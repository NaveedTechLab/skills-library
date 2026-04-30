"""
Vault Synchronization

Handles synchronization of the Obsidian vault between Cloud and Local agents.
Supports git-based sync (recommended) and Syncthing, with conflict resolution
and security filtering.

Platinum Phase 2 - Personal AI Employee Project
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
import fnmatch
import json
import logging
import os
import subprocess
import time

logger = logging.getLogger("a2a-vault-sync")


# ---------------------------------------------------------------------------
# Security filter
# ---------------------------------------------------------------------------

# File patterns that must NEVER be synced between agents
NEVER_SYNC_PATTERNS: list[str] = [
    ".env",
    ".env.*",
    "*.env",
    ".env.local",
    ".env.production",
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.jks",
    # Token / credential stores
    "token.json",
    "tokens.json",
    "credentials.json",
    "client_secret*.json",
    "service_account*.json",
    "*_credentials.*",
    "*_token.*",
    # WhatsApp session data
    "session-*",
    "auth_info*",
    ".wwebjs_auth/**",
    "whatsapp_session/**",
    # Banking credentials
    "banking_*",
    "bank_creds*",
    "*_banking.*",
    # SSH keys
    "id_rsa*",
    "id_ed25519*",
    "id_ecdsa*",
    # OS / editor artifacts
    ".DS_Store",
    "Thumbs.db",
    "*.swp",
    "*.swo",
    # Node / Python artifacts that shouldn't sync
    "node_modules/**",
    "__pycache__/**",
    "*.pyc",
    ".venv/**",
    "venv/**",
]


class SecurityFilter:
    """Filters files to prevent sensitive data from being synced."""

    def __init__(self, extra_patterns: Optional[list[str]] = None) -> None:
        self.patterns = list(NEVER_SYNC_PATTERNS)
        if extra_patterns:
            self.patterns.extend(extra_patterns)

    def is_safe_to_sync(self, filepath: str) -> bool:
        """Return True if the file is safe to sync."""
        name = os.path.basename(filepath)
        rel_path = filepath  # may be relative or absolute

        for pattern in self.patterns:
            if fnmatch.fnmatch(name, pattern):
                return False
            if fnmatch.fnmatch(rel_path, pattern):
                return False
            # Check if any path component matches
            parts = Path(rel_path).parts
            for part in parts:
                if fnmatch.fnmatch(part, pattern):
                    return False

        return True

    def filter_paths(self, paths: list[str]) -> tuple[list[str], list[str]]:
        """Split paths into (safe, blocked) lists."""
        safe: list[str] = []
        blocked: list[str] = []
        for p in paths:
            if self.is_safe_to_sync(p):
                safe.append(p)
            else:
                blocked.append(p)
        return safe, blocked

    def scan_directory(self, directory: Path) -> list[str]:
        """Return list of blocked files found in a directory."""
        blocked: list[str] = []
        for root, _dirs, files in os.walk(directory):
            for filename in files:
                full = os.path.join(root, filename)
                rel = os.path.relpath(full, directory)
                if not self.is_safe_to_sync(rel):
                    blocked.append(rel)
        return blocked


# ---------------------------------------------------------------------------
# Conflict resolution
# ---------------------------------------------------------------------------

class ConflictStrategy(Enum):
    LOCAL_WINS = "local_wins"
    CLOUD_WINS = "cloud_wins"
    NEWEST_WINS = "newest_wins"
    MANUAL = "manual"


@dataclass
class ConflictRecord:
    filepath: str
    local_mtime: Optional[datetime] = None
    cloud_mtime: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Files with special conflict resolution rules
CONFLICT_RULES: dict[str, ConflictStrategy] = {
    "Dashboard.md": ConflictStrategy.LOCAL_WINS,  # Single-writer: Local only
    "Plan.md": ConflictStrategy.NEWEST_WINS,
}


class ConflictResolver:
    """Resolves sync conflicts between Cloud and Local vaults."""

    def __init__(
        self,
        default_strategy: ConflictStrategy = ConflictStrategy.NEWEST_WINS,
        custom_rules: Optional[dict[str, ConflictStrategy]] = None,
    ) -> None:
        self.default_strategy = default_strategy
        self.rules: dict[str, ConflictStrategy] = dict(CONFLICT_RULES)
        if custom_rules:
            self.rules.update(custom_rules)
        self._history: list[ConflictRecord] = []

    def resolve(self, filepath: str, local_mtime: datetime, cloud_mtime: datetime) -> str:
        """Return 'local' or 'cloud' indicating which version wins."""
        filename = os.path.basename(filepath)
        strategy = self.rules.get(filename, self.default_strategy)

        if strategy == ConflictStrategy.LOCAL_WINS:
            winner = "local"
        elif strategy == ConflictStrategy.CLOUD_WINS:
            winner = "cloud"
        elif strategy == ConflictStrategy.NEWEST_WINS:
            winner = "local" if local_mtime >= cloud_mtime else "cloud"
        else:
            # Manual resolution - default to local for safety
            winner = "local"
            logger.warning("Manual conflict resolution needed for %s, defaulting to local", filepath)

        record = ConflictRecord(
            filepath=filepath,
            local_mtime=local_mtime,
            cloud_mtime=cloud_mtime,
            resolved_by=strategy.value,
            resolution=winner,
        )
        self._history.append(record)
        logger.info("Conflict resolved for %s: %s wins (strategy: %s)", filepath, winner, strategy.value)

        return winner

    @property
    def history(self) -> list[dict]:
        return [
            {
                "filepath": r.filepath,
                "local_mtime": r.local_mtime.isoformat() if r.local_mtime else None,
                "cloud_mtime": r.cloud_mtime.isoformat() if r.cloud_mtime else None,
                "resolved_by": r.resolved_by,
                "resolution": r.resolution,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in self._history
        ]


# ---------------------------------------------------------------------------
# Sync status
# ---------------------------------------------------------------------------

@dataclass
class SyncStatus:
    last_sync: Optional[datetime] = None
    files_synced: int = 0
    files_blocked: int = 0
    conflicts_resolved: int = 0
    errors: list[str] = field(default_factory=list)
    is_syncing: bool = False
    sync_method: str = "none"

    def to_dict(self) -> dict:
        return {
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "files_synced": self.files_synced,
            "files_blocked": self.files_blocked,
            "conflicts_resolved": self.conflicts_resolved,
            "errors": self.errors,
            "is_syncing": self.is_syncing,
            "sync_method": self.sync_method,
        }


# ---------------------------------------------------------------------------
# Git-based sync
# ---------------------------------------------------------------------------

class GitVaultSync:
    """Git-based vault synchronization (recommended).

    Uses a shared git repository for the vault. Both agents commit changes
    and pull/merge to stay in sync.
    """

    def __init__(
        self,
        vault_path: Path,
        remote_name: str = "origin",
        branch: str = "main",
        security_filter: Optional[SecurityFilter] = None,
        conflict_resolver: Optional[ConflictResolver] = None,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.remote_name = remote_name
        self.branch = branch
        self.security_filter = security_filter or SecurityFilter()
        self.conflict_resolver = conflict_resolver or ConflictResolver()
        self.status = SyncStatus(sync_method="git")
        self._gitignore_path = self.vault_path / ".gitignore"

    def ensure_gitignore(self) -> None:
        """Ensure .gitignore contains all security filter patterns."""
        existing: set[str] = set()
        if self._gitignore_path.exists():
            existing = set(self._gitignore_path.read_text(encoding="utf-8").splitlines())

        lines_to_add: list[str] = []
        for pattern in NEVER_SYNC_PATTERNS:
            if pattern not in existing:
                lines_to_add.append(pattern)

        if lines_to_add:
            with open(self._gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n# A2A Security Filter - auto-generated\n")
                for line in lines_to_add:
                    f.write(f"{line}\n")
            logger.info("Updated .gitignore with %d security patterns", len(lines_to_add))

    def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        cmd = ["git", "-C", str(self.vault_path)] + list(args)
        logger.debug("Running: %s", " ".join(cmd))
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
            timeout=60,
        )

    def is_git_repo(self) -> bool:
        result = self._run_git("rev-parse", "--is-inside-work-tree", check=False)
        return result.returncode == 0

    def init_repo(self) -> bool:
        """Initialize the vault as a git repository if not already."""
        if self.is_git_repo():
            logger.info("Vault is already a git repository")
            return True
        try:
            self._run_git("init")
            self.ensure_gitignore()
            self._run_git("add", ".gitignore")
            self._run_git("commit", "-m", "Initialize vault with security gitignore")
            logger.info("Git repository initialized at %s", self.vault_path)
            return True
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to init git repo: %s", exc.stderr)
            return False

    def sync(self) -> SyncStatus:
        """Perform a full sync cycle: commit local, pull, push."""
        self.status.is_syncing = True
        self.status.errors = []
        self.status.files_synced = 0
        self.status.files_blocked = 0
        self.status.conflicts_resolved = 0

        try:
            self.ensure_gitignore()

            # Check for blocked files
            blocked = self.security_filter.scan_directory(self.vault_path)
            self.status.files_blocked = len(blocked)
            if blocked:
                logger.warning("Blocked %d sensitive files from sync", len(blocked))

            # Stage and commit local changes
            self._run_git("add", "-A")

            # Check if there are changes to commit
            diff_result = self._run_git("diff", "--cached", "--stat", check=False)
            if diff_result.stdout.strip():
                timestamp = datetime.now(timezone.utc).isoformat()
                self._run_git("commit", "-m", f"A2A vault sync: {timestamp}")
                logger.info("Committed local changes")

            # Pull remote changes
            pull_result = self._run_git("pull", self.remote_name, self.branch, "--no-edit", check=False)

            if pull_result.returncode != 0:
                if "CONFLICT" in pull_result.stdout or "CONFLICT" in pull_result.stderr:
                    conflicts = self._resolve_conflicts()
                    self.status.conflicts_resolved = conflicts
                else:
                    error_msg = pull_result.stderr.strip() or pull_result.stdout.strip()
                    if "Could not resolve host" in error_msg or "No such remote" in error_msg:
                        logger.warning("Remote not available, skipping pull: %s", error_msg)
                    else:
                        self.status.errors.append(f"Pull failed: {error_msg}")
                        logger.error("Git pull failed: %s", error_msg)

            # Push local changes
            push_result = self._run_git("push", self.remote_name, self.branch, check=False)
            if push_result.returncode != 0:
                error_msg = push_result.stderr.strip()
                if "No such remote" not in error_msg:
                    logger.warning("Git push failed: %s", error_msg)

            # Count synced files
            log_result = self._run_git("diff", "--stat", "HEAD~1", "HEAD", check=False)
            if log_result.returncode == 0:
                lines = log_result.stdout.strip().splitlines()
                self.status.files_synced = max(0, len(lines) - 1)  # last line is summary

            self.status.last_sync = datetime.now(timezone.utc)

        except subprocess.TimeoutExpired:
            self.status.errors.append("Git operation timed out")
            logger.error("Git sync timed out")
        except Exception as exc:
            self.status.errors.append(str(exc))
            logger.error("Sync error: %s", exc)
        finally:
            self.status.is_syncing = False

        return self.status

    def _resolve_conflicts(self) -> int:
        """Resolve merge conflicts using configured strategies."""
        resolved = 0
        result = self._run_git("diff", "--name-only", "--diff-filter=U", check=False)
        if result.returncode != 0:
            return 0

        conflicted_files = result.stdout.strip().splitlines()
        for filepath in conflicted_files:
            filename = os.path.basename(filepath)
            # For Dashboard.md, always take local (ours)
            winner = self.conflict_resolver.resolve(
                filepath,
                local_mtime=datetime.now(timezone.utc),
                cloud_mtime=datetime.now(timezone.utc),
            )
            if winner == "local":
                self._run_git("checkout", "--ours", filepath, check=False)
            else:
                self._run_git("checkout", "--theirs", filepath, check=False)

            self._run_git("add", filepath, check=False)
            resolved += 1

        if resolved > 0:
            self._run_git("commit", "-m", f"Resolved {resolved} conflict(s) via A2A sync", check=False)

        return resolved

    def get_status(self) -> dict:
        return self.status.to_dict()


# ---------------------------------------------------------------------------
# Syncthing-based sync
# ---------------------------------------------------------------------------

class SyncthingVaultSync:
    """Syncthing-based vault synchronization.

    Relies on Syncthing running externally for file synchronization.
    This class provides monitoring and conflict resolution on top.
    """

    def __init__(
        self,
        vault_path: Path,
        syncthing_api_url: str = "http://localhost:8384",
        api_key: Optional[str] = None,
        security_filter: Optional[SecurityFilter] = None,
        conflict_resolver: Optional[ConflictResolver] = None,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.api_url = syncthing_api_url
        self.api_key = api_key
        self.security_filter = security_filter or SecurityFilter()
        self.conflict_resolver = conflict_resolver or ConflictResolver()
        self.status = SyncStatus(sync_method="syncthing")

    def ensure_ignore_file(self) -> None:
        """Write .stignore for Syncthing with security patterns."""
        stignore_path = self.vault_path / ".stignore"
        lines = ["// A2A Security Filter - auto-generated"]
        for pattern in NEVER_SYNC_PATTERNS:
            lines.append(pattern)

        stignore_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info("Updated .stignore with security patterns")

    def check_status(self) -> dict:
        """Check Syncthing status via its REST API."""
        try:
            import urllib.request
            import urllib.error

            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            req = urllib.request.Request(
                f"{self.api_url}/rest/system/status",
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return {
                    "running": True,
                    "my_id": data.get("myID", ""),
                    "uptime": data.get("uptime", 0),
                }
        except Exception as exc:
            logger.warning("Syncthing API check failed: %s", exc)
            return {"running": False, "error": str(exc)}

    def resolve_conflicts(self) -> int:
        """Find and resolve Syncthing conflict files (.sync-conflict-*)."""
        resolved = 0
        for root, _dirs, files in os.walk(self.vault_path):
            for filename in files:
                if ".sync-conflict-" not in filename:
                    continue

                conflict_path = Path(root) / filename
                # Parse original filename from conflict name
                # Format: file.sync-conflict-YYYYMMDD-HHMMSS-XXXXXXX.ext
                parts = filename.split(".sync-conflict-")
                if len(parts) >= 2:
                    # Reconstruct original filename
                    original_name = parts[0]
                    remaining = parts[1]
                    # Find extension after the conflict timestamp
                    ext_start = remaining.find(".")
                    if ext_start >= 0:
                        original_name += remaining[ext_start:]

                    original_path = Path(root) / original_name
                    rel_path = os.path.relpath(str(original_path), str(self.vault_path))

                    if original_path.exists():
                        local_mtime = datetime.fromtimestamp(
                            original_path.stat().st_mtime, tz=timezone.utc
                        )
                        conflict_mtime = datetime.fromtimestamp(
                            conflict_path.stat().st_mtime, tz=timezone.utc
                        )

                        winner = self.conflict_resolver.resolve(
                            rel_path, local_mtime, conflict_mtime
                        )

                        if winner == "cloud":
                            # Cloud version (conflict file) wins
                            conflict_path.replace(original_path)
                        else:
                            # Local version wins, remove conflict
                            conflict_path.unlink()

                        resolved += 1
                    else:
                        # Original doesn't exist, rename conflict to original
                        conflict_path.rename(original_path)
                        resolved += 1

        if resolved:
            logger.info("Resolved %d Syncthing conflicts", resolved)
        return resolved

    def get_status(self) -> dict:
        syncthing_status = self.check_status()
        result = self.status.to_dict()
        result["syncthing"] = syncthing_status
        return result


# ---------------------------------------------------------------------------
# Sync monitor
# ---------------------------------------------------------------------------

class SyncMonitor:
    """Monitors vault sync status and alerts on issues."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = Path(vault_path)
        self._sync_log: list[dict] = []

    def log_sync_event(self, event_type: str, details: dict) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details,
        }
        self._sync_log.append(entry)

        # Write to vault
        log_dir = self.vault_path / "Updates" / "sync-log"
        log_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = log_dir / f"sync-{date_str}.json"

        existing: list[dict] = []
        if log_file.exists():
            try:
                existing = json.loads(log_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        existing.append(entry)
        log_file.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")

    def get_recent_events(self, limit: int = 20) -> list[dict]:
        return self._sync_log[-limit:]

    def check_health(self, max_sync_age_minutes: int = 30) -> dict:
        """Check if sync is healthy based on recent events."""
        if not self._sync_log:
            return {
                "healthy": False,
                "reason": "No sync events recorded",
                "last_event": None,
            }

        last = self._sync_log[-1]
        last_ts = datetime.fromisoformat(last["timestamp"])
        age_minutes = (datetime.now(timezone.utc) - last_ts).total_seconds() / 60

        if age_minutes > max_sync_age_minutes:
            return {
                "healthy": False,
                "reason": f"Last sync was {int(age_minutes)} minutes ago (threshold: {max_sync_age_minutes})",
                "last_event": last,
            }

        # Check for recent errors
        recent_errors = [
            e for e in self._sync_log[-5:]
            if e["event_type"] == "error"
        ]

        if len(recent_errors) >= 3:
            return {
                "healthy": False,
                "reason": f"{len(recent_errors)} errors in last 5 sync events",
                "last_event": last,
            }

        return {
            "healthy": True,
            "reason": "Sync operating normally",
            "last_event": last,
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_vault_sync(
    vault_path: Path,
    method: str = "git",
    **kwargs,
) -> GitVaultSync | SyncthingVaultSync:
    """Create a vault sync instance based on the chosen method."""
    security_filter = SecurityFilter(extra_patterns=kwargs.get("extra_filter_patterns"))
    conflict_resolver = ConflictResolver(
        default_strategy=ConflictStrategy(kwargs.get("conflict_strategy", "newest_wins")),
    )

    if method == "syncthing":
        return SyncthingVaultSync(
            vault_path=vault_path,
            syncthing_api_url=kwargs.get("syncthing_api_url", "http://localhost:8384"),
            api_key=kwargs.get("syncthing_api_key"),
            security_filter=security_filter,
            conflict_resolver=conflict_resolver,
        )
    else:
        return GitVaultSync(
            vault_path=vault_path,
            remote_name=kwargs.get("remote_name", "origin"),
            branch=kwargs.get("branch", "main"),
            security_filter=security_filter,
            conflict_resolver=conflict_resolver,
        )
