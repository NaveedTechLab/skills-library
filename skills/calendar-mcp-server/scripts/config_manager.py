#!/usr/bin/env python3
"""
Configuration Manager for Calendar MCP Server.

Provides a dataclass-based configuration for Google Calendar API settings,
HITL approval thresholds, and default calendar parameters. Configuration
can be loaded from environment variables, a JSON file, or constructed
directly in code.
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("calendar-config")


@dataclass
class CalendarConfig:
    """
    Complete configuration for the Calendar MCP Server.

    Attributes:
        credentials_path: Path to Google OAuth2 credentials JSON file.
        token_path: Path to store/load the OAuth2 token.
        default_calendar_id: Calendar ID to use when none is specified.
        approval_dir: Root directory for HITL approval files.
        approval_timeout_seconds: How long an approval request stays valid.
        organization_domains: List of internal email domains. Attendees
            outside these domains are considered external and trigger HITL.
        auto_approve_personal: If True, events on the primary calendar
            with no attendees are created without HITL approval.
        max_results_default: Default maximum number of events returned
            by list queries.
        timezone: Default timezone for event creation (IANA timezone name).
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        server_host: Host for the MCP server when running in HTTP mode.
        server_port: Port for the MCP server when running in HTTP mode.
    """

    # Google API settings
    credentials_path: str = "credentials.json"
    token_path: str = "calendar_token.json"

    # Calendar defaults
    default_calendar_id: str = "primary"
    timezone: str = "UTC"
    max_results_default: int = 25

    # HITL / approval settings
    approval_dir: str = "./Pending_Approval"
    approval_timeout_seconds: int = 3600
    organization_domains: List[str] = field(default_factory=list)
    auto_approve_personal: bool = True

    # Server settings
    server_host: str = "localhost"
    server_port: int = 8090
    log_level: str = "INFO"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to a dictionary."""
        return asdict(self)

    def save(self, path: str) -> None:
        """Save configuration to a JSON file."""
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(
            json.dumps(self.to_dict(), indent=2), encoding="utf-8"
        )
        logger.info("Configuration saved to %s", filepath)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalendarConfig":
        """Create a CalendarConfig from a dictionary, ignoring unknown keys."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    @classmethod
    def from_file(cls, path: str) -> "CalendarConfig":
        """Load configuration from a JSON file."""
        filepath = Path(path)
        if not filepath.exists():
            logger.warning(
                "Config file %s not found, using defaults.", filepath
            )
            return cls()
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_env(cls) -> "CalendarConfig":
        """
        Create a CalendarConfig from environment variables.

        Recognized environment variables (all optional):
            GOOGLE_CALENDAR_CREDENTIALS
            GOOGLE_CALENDAR_TOKEN
            CALENDAR_DEFAULT_ID
            CALENDAR_TIMEZONE
            CALENDAR_MAX_RESULTS
            CALENDAR_APPROVAL_DIR
            CALENDAR_APPROVAL_TIMEOUT
            CALENDAR_ORG_DOMAINS  (comma-separated)
            CALENDAR_AUTO_APPROVE_PERSONAL  (true/false)
            CALENDAR_SERVER_HOST
            CALENDAR_SERVER_PORT
            CALENDAR_LOG_LEVEL
        """
        def _bool(val: str) -> bool:
            return val.strip().lower() in ("true", "1", "yes")

        kwargs: Dict[str, Any] = {}

        env_map = {
            "GOOGLE_CALENDAR_CREDENTIALS": ("credentials_path", str),
            "GOOGLE_CALENDAR_TOKEN": ("token_path", str),
            "CALENDAR_DEFAULT_ID": ("default_calendar_id", str),
            "CALENDAR_TIMEZONE": ("timezone", str),
            "CALENDAR_MAX_RESULTS": ("max_results_default", int),
            "CALENDAR_APPROVAL_DIR": ("approval_dir", str),
            "CALENDAR_APPROVAL_TIMEOUT": ("approval_timeout_seconds", int),
            "CALENDAR_AUTO_APPROVE_PERSONAL": ("auto_approve_personal", _bool),
            "CALENDAR_SERVER_HOST": ("server_host", str),
            "CALENDAR_SERVER_PORT": ("server_port", int),
            "CALENDAR_LOG_LEVEL": ("log_level", str),
        }

        for env_var, (field_name, converter) in env_map.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    kwargs[field_name] = converter(value)
                except (ValueError, TypeError) as exc:
                    logger.warning(
                        "Invalid value for %s=%s: %s", env_var, value, exc
                    )

        # Special handling for comma-separated domains
        domains_str = os.getenv("CALENDAR_ORG_DOMAINS")
        if domains_str:
            kwargs["organization_domains"] = [
                d.strip().lower() for d in domains_str.split(",") if d.strip()
            ]

        return cls(**kwargs)

    def validate(self) -> List[str]:
        """
        Validate the configuration and return a list of error messages.
        An empty list means the configuration is valid.
        """
        errors: List[str] = []

        if not self.credentials_path:
            errors.append("credentials_path must not be empty")

        if not self.token_path:
            errors.append("token_path must not be empty")

        if self.approval_timeout_seconds <= 0:
            errors.append("approval_timeout_seconds must be positive")

        if self.max_results_default <= 0:
            errors.append("max_results_default must be positive")

        if self.server_port < 1 or self.server_port > 65535:
            errors.append("server_port must be between 1 and 65535")

        if self.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            errors.append(
                f"log_level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL; got {self.log_level}"
            )

        return errors


def get_config(
    config_path: Optional[str] = None,
    use_env: bool = True,
) -> CalendarConfig:
    """
    Convenience function to load configuration with the following priority:

    1. Explicit JSON file (if ``config_path`` is provided and exists).
    2. Environment variables (if ``use_env`` is True).
    3. Defaults.

    Values from higher-priority sources override lower-priority ones.
    """
    config = CalendarConfig()

    # Layer 1: file-based config
    if config_path:
        file_path = Path(config_path)
        if file_path.exists():
            config = CalendarConfig.from_file(config_path)
            logger.info("Loaded config from %s", config_path)

    # Layer 2: environment variable overrides
    if use_env:
        env_config = CalendarConfig.from_env()
        env_dict = env_config.to_dict()
        base_dict = config.to_dict()
        default_dict = CalendarConfig().to_dict()

        # Only override fields that differ from defaults (i.e., were set via env)
        merged = dict(base_dict)
        for key, env_val in env_dict.items():
            if env_val != default_dict.get(key):
                merged[key] = env_val

        config = CalendarConfig.from_dict(merged)

    return config


def create_default_config(path: str = "./calendar_config.json") -> CalendarConfig:
    """Create and save a default configuration file."""
    config = CalendarConfig()
    config.save(path)
    logger.info("Default calendar config created at %s", path)
    return config
