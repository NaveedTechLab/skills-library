#!/usr/bin/env python3
"""
Slack MCP Server - Configuration Manager

Manages configuration for the Slack MCP server including bot tokens,
HITL settings, rate limits, and audit log paths. Configuration is loaded
from environment variables with sensible defaults.
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SlackConfig:
    """Configuration for the Slack MCP Server.

    All sensitive values (tokens, secrets) are loaded from environment
    variables. Never hardcode secrets in configuration files.
    """

    # --- Authentication ---
    bot_token: str = ""
    app_token: str = ""
    signing_secret: str = ""

    # --- Defaults ---
    default_channel: str = "general"

    # --- HITL Settings ---
    hitl_enabled: bool = True
    hitl_external_channels: bool = True
    hitl_new_dm_users: bool = True
    hitl_file_uploads: bool = True
    hitl_bulk_threshold: int = 3
    hitl_bulk_window_seconds: int = 60

    # --- Rate Limiting ---
    rate_limit_per_minute: int = 50
    rate_limit_per_second: int = 1

    # --- Audit & Approval ---
    audit_log_path: str = "logs/slack_audit.log"
    approval_dir: str = "Pending_Approval"
    approval_timeout_seconds: int = 3600

    # --- Server ---
    server_host: str = "localhost"
    server_port: int = 8090

    # --- Internal Channel Identifiers ---
    internal_channel_prefixes: list = field(default_factory=lambda: ["C"])
    external_shared_channel_prefixes: list = field(default_factory=lambda: ["E"])

    # --- Known DM Users (user IDs previously contacted) ---
    known_dm_users_file: str = "data/known_dm_users.json"

    def validate(self) -> list:
        """Validate the configuration and return a list of issues.

        Returns:
            List of validation error strings. Empty list means valid.
        """
        issues = []

        if not self.bot_token:
            issues.append(
                "bot_token is required. Set SLACK_BOT_TOKEN environment variable."
            )
        elif not self.bot_token.startswith("xoxb-"):
            issues.append(
                "bot_token should start with 'xoxb-'. "
                "Ensure you are using a Bot User OAuth Token."
            )

        if self.app_token and not self.app_token.startswith("xapp-"):
            issues.append(
                "app_token should start with 'xapp-' if provided. "
                "Ensure you are using an App-Level Token."
            )

        if self.hitl_bulk_threshold < 1:
            issues.append("hitl_bulk_threshold must be at least 1.")

        if self.hitl_bulk_window_seconds < 1:
            issues.append("hitl_bulk_window_seconds must be at least 1.")

        if self.rate_limit_per_minute < 1:
            issues.append("rate_limit_per_minute must be at least 1.")

        if self.rate_limit_per_second < 1:
            issues.append("rate_limit_per_second must be at least 1.")

        if self.approval_timeout_seconds < 60:
            issues.append("approval_timeout_seconds should be at least 60.")

        return issues

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to dictionary, masking sensitive fields."""
        data = asdict(self)
        # Mask sensitive values
        for key in ("bot_token", "app_token", "signing_secret"):
            if data.get(key):
                value = data[key]
                data[key] = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
        return data

    def to_json(self, indent: int = 2) -> str:
        """Serialize config to JSON string with masked secrets."""
        return json.dumps(self.to_dict(), indent=indent)


def load_config(
    config_file: Optional[str] = None,
    env_prefix: str = "SLACK_",
) -> SlackConfig:
    """Load configuration from environment variables and optional config file.

    Priority (highest to lowest):
    1. Environment variables
    2. Config file values
    3. Dataclass defaults

    Args:
        config_file: Optional path to a JSON configuration file.
        env_prefix: Prefix for environment variable names.

    Returns:
        Populated SlackConfig instance.
    """
    # Start with defaults
    config = SlackConfig()

    # Layer 1: Load from config file if provided
    if config_file and Path(config_file).exists():
        try:
            with open(config_file, "r") as f:
                file_data = json.load(f)

            # Map JSON keys to dataclass fields
            field_mapping = {
                "bot_token": "bot_token",
                "app_token": "app_token",
                "signing_secret": "signing_secret",
                "default_channel": "default_channel",
                "hitl_enabled": "hitl_enabled",
                "hitl_external_channels": "hitl_external_channels",
                "hitl_new_dm_users": "hitl_new_dm_users",
                "hitl_file_uploads": "hitl_file_uploads",
                "hitl_bulk_threshold": "hitl_bulk_threshold",
                "hitl_bulk_window_seconds": "hitl_bulk_window_seconds",
                "rate_limit_per_minute": "rate_limit_per_minute",
                "rate_limit_per_second": "rate_limit_per_second",
                "audit_log_path": "audit_log_path",
                "approval_dir": "approval_dir",
                "approval_timeout_seconds": "approval_timeout_seconds",
                "server_host": "server_host",
                "server_port": "server_port",
            }

            for json_key, attr_name in field_mapping.items():
                if json_key in file_data:
                    setattr(config, attr_name, file_data[json_key])

            logger.info("Loaded configuration from %s", config_file)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load config file %s: %s", config_file, exc)

    # Layer 2: Override with environment variables (highest priority)
    env_mapping = {
        f"{env_prefix}BOT_TOKEN": "bot_token",
        f"{env_prefix}APP_TOKEN": "app_token",
        f"{env_prefix}SIGNING_SECRET": "signing_secret",
        f"{env_prefix}DEFAULT_CHANNEL": "default_channel",
        f"{env_prefix}HITL_ENABLED": "hitl_enabled",
        f"{env_prefix}HITL_EXTERNAL_CHANNELS": "hitl_external_channels",
        f"{env_prefix}HITL_NEW_DM_USERS": "hitl_new_dm_users",
        f"{env_prefix}HITL_FILE_UPLOADS": "hitl_file_uploads",
        f"{env_prefix}HITL_BULK_THRESHOLD": "hitl_bulk_threshold",
        f"{env_prefix}HITL_BULK_WINDOW_SECONDS": "hitl_bulk_window_seconds",
        f"{env_prefix}RATE_LIMIT_PER_MINUTE": "rate_limit_per_minute",
        f"{env_prefix}RATE_LIMIT_PER_SECOND": "rate_limit_per_second",
        f"{env_prefix}AUDIT_LOG_PATH": "audit_log_path",
        f"{env_prefix}APPROVAL_DIR": "approval_dir",
        f"{env_prefix}APPROVAL_TIMEOUT_SECONDS": "approval_timeout_seconds",
        f"{env_prefix}SERVER_HOST": "server_host",
        f"{env_prefix}SERVER_PORT": "server_port",
    }

    bool_fields = {
        "hitl_enabled",
        "hitl_external_channels",
        "hitl_new_dm_users",
        "hitl_file_uploads",
    }
    int_fields = {
        "hitl_bulk_threshold",
        "hitl_bulk_window_seconds",
        "rate_limit_per_minute",
        "rate_limit_per_second",
        "approval_timeout_seconds",
        "server_port",
    }

    for env_var, attr_name in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            if attr_name in bool_fields:
                setattr(config, attr_name, value.lower() in ("true", "1", "yes"))
            elif attr_name in int_fields:
                try:
                    setattr(config, attr_name, int(value))
                except ValueError:
                    logger.warning(
                        "Invalid integer for %s=%s, using default", env_var, value
                    )
            else:
                setattr(config, attr_name, value)

    # Validate and warn
    issues = config.validate()
    for issue in issues:
        logger.warning("Config validation: %s", issue)

    return config


def ensure_directories(config: SlackConfig) -> None:
    """Create required directories if they do not exist.

    Args:
        config: The SlackConfig instance with directory paths.
    """
    dirs_to_create = [
        Path(config.audit_log_path).parent,
        Path(config.approval_dir),
        Path(config.known_dm_users_file).parent,
    ]

    for directory in dirs_to_create:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            logger.info("Created directory: %s", directory)
