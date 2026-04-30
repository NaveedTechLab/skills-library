"""
Configuration manager for Browser Payment MCP Server.

Centralizes all configuration with sensible defaults, environment variable
overrides, and validation. No secrets are stored -- credentials are managed
by Playwright's persistent browser context.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


def _env_bool(key: str, default: bool = False) -> bool:
    """Read a boolean from an environment variable."""
    raw = os.getenv(key, str(default)).strip().lower()
    return raw in ("true", "1", "yes")


def _env_int(key: str, default: int) -> int:
    """Read an integer from an environment variable."""
    raw = os.getenv(key, "")
    if raw.strip().isdigit():
        return int(raw.strip())
    return default


def _env_list(key: str, default: str = "") -> List[str]:
    """Read a comma-separated list from an environment variable."""
    raw = os.getenv(key, default).strip()
    if not raw or raw == "*":
        return []
    return [d.strip() for d in raw.split(",") if d.strip()]


@dataclass
class PaymentConfig:
    """All configurable settings for the Browser Payment MCP server."""

    # -- Execution mode --
    dry_run: bool = field(default_factory=lambda: _env_bool("PAYMENT_DRY_RUN", False))
    headless: bool = field(default_factory=lambda: _env_bool("PAYMENT_HEADLESS", True))

    # -- Directories --
    vault_dir: str = field(
        default_factory=lambda: os.getenv("PAYMENT_VAULT_DIR", "demo_vault")
    )
    screenshot_dir: str = field(
        default_factory=lambda: os.getenv(
            "PAYMENT_SCREENSHOT_DIR", "demo_vault/Logs/payments/screenshots"
        )
    )
    audit_log_dir: str = field(
        default_factory=lambda: os.getenv(
            "PAYMENT_AUDIT_LOG_DIR", "demo_vault/Logs/payments"
        )
    )

    # -- Rate limiting --
    max_payments_per_hour: int = field(
        default_factory=lambda: _env_int("PAYMENT_MAX_PER_HOUR", 3)
    )

    # -- Approval --
    approval_expiry_hours: int = field(
        default_factory=lambda: _env_int("PAYMENT_APPROVAL_EXPIRY_H", 24)
    )

    # -- Domain restrictions --
    allowed_domains: List[str] = field(
        default_factory=lambda: _env_list("PAYMENT_ALLOWED_DOMAINS", "*")
    )

    # -- Retention --
    audit_retention_days: int = field(
        default_factory=lambda: _env_int("PAYMENT_AUDIT_RETENTION_DAYS", 90)
    )

    # -- Browser profile --
    browser_profile_dir: str = field(
        default_factory=lambda: os.getenv(
            "PAYMENT_BROWSER_PROFILE", "demo_vault/.browser_profile"
        )
    )

    # -- Derived paths --

    @property
    def pending_approval_dir(self) -> Path:
        return Path(self.vault_dir) / "Pending_Approval"

    @property
    def approved_dir(self) -> Path:
        return Path(self.vault_dir) / "Approved"

    @property
    def screenshot_path(self) -> Path:
        return Path(self.screenshot_dir)

    @property
    def audit_log_path(self) -> Path:
        return Path(self.audit_log_dir)

    @property
    def browser_profile_path(self) -> Path:
        return Path(self.browser_profile_dir)

    # -- Validation --

    def validate(self) -> List[str]:
        """Return a list of configuration warnings (empty means all good)."""
        warnings: List[str] = []

        if self.max_payments_per_hour < 1:
            warnings.append(
                f"max_payments_per_hour is {self.max_payments_per_hour}; "
                "must be >= 1. Defaulting to 1."
            )
            object.__setattr__(self, "max_payments_per_hour", 1)

        if self.approval_expiry_hours < 1:
            warnings.append(
                f"approval_expiry_hours is {self.approval_expiry_hours}; "
                "must be >= 1. Defaulting to 1."
            )
            object.__setattr__(self, "approval_expiry_hours", 1)

        if self.audit_retention_days < 1:
            warnings.append(
                f"audit_retention_days is {self.audit_retention_days}; "
                "must be >= 1. Defaulting to 30."
            )
            object.__setattr__(self, "audit_retention_days", 30)

        return warnings

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        for directory in [
            self.pending_approval_dir,
            self.approved_dir,
            self.screenshot_path,
            self.audit_log_path,
            self.browser_profile_path,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def is_domain_allowed(self, url: str) -> bool:
        """Check whether a URL's domain is in the allowed list.

        An empty allowed_domains list means all domains are allowed.
        """
        if not self.allowed_domains:
            return True

        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
        except Exception:
            return False

        for allowed in self.allowed_domains:
            if hostname == allowed or hostname.endswith(f".{allowed}"):
                return True
        return False

    def to_dict(self) -> dict:
        """Serialise config to a dict (safe for logging -- no secrets)."""
        return {
            "dry_run": self.dry_run,
            "headless": self.headless,
            "vault_dir": self.vault_dir,
            "screenshot_dir": self.screenshot_dir,
            "audit_log_dir": self.audit_log_dir,
            "max_payments_per_hour": self.max_payments_per_hour,
            "approval_expiry_hours": self.approval_expiry_hours,
            "allowed_domains": self.allowed_domains if self.allowed_domains else ["*"],
            "audit_retention_days": self.audit_retention_days,
            "browser_profile_dir": self.browser_profile_dir,
        }


# Singleton instance -- import and use directly.
config = PaymentConfig()
