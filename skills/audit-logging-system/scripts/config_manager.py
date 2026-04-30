#!/usr/bin/env python3
"""
Configuration Manager for Audit Logging System

Manages configuration for the audit logging system including retention policies,
storage settings, and security options.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, asdict


@dataclass
class AuditStorageConfig:
    """Storage configuration for audit logs"""
    storage_path: str = "./audit_logs"
    max_size_mb: int = 100
    compress_logs: bool = True
    keep_archives: int = 10
    rotation_interval_hours: int = 24


@dataclass
class AuditSecurityConfig:
    """Security configuration for audit logs"""
    enable_encryption: bool = False
    encryption_key: Optional[str] = None
    enable_signing: bool = True
    integrity_protection: bool = True
    access_control_enabled: bool = True
    privileged_access_logging: bool = True


@dataclass
class AuditRetentionConfig:
    """Retention configuration for audit logs"""
    retention_days: int = 90
    security_event_retention_days: int = 3650  # 10 years for security events
    compliance_retention_days: int = 2555  # 7 years for compliance
    auto_cleanup: bool = True
    cleanup_interval_hours: int = 24


@dataclass
class AuditFilterConfig:
    """Event filtering configuration"""
    include_event_types: list = None
    exclude_event_types: list = None
    min_log_level: str = "INFO"
    sensitive_data_masking: bool = True
    pii_masking_patterns: list = None


@dataclass
class AuditConfig:
    """Complete audit logging configuration"""
    enabled: bool = True
    log_format: str = "structured_json"
    storage: AuditStorageConfig = None
    security: AuditSecurityConfig = None
    retention: AuditRetentionConfig = None
    filters: AuditFilterConfig = None

    def __post_init__(self):
        if self.storage is None:
            self.storage = AuditStorageConfig()
        if self.security is None:
            self.security = AuditSecurityConfig()
        if self.retention is None:
            self.retention = AuditRetentionConfig()
        if self.filters is None:
            self.filters = AuditFilterConfig()
        if self.filters.include_event_types is None:
            self.filters.include_event_types = [
                "agent_action", "file_access", "data_access",
                "config_change", "security_event", "system_event"
            ]
        if self.filters.exclude_event_types is None:
            self.filters.exclude_event_types = ["heartbeat", "health_check"]
        if self.filters.pii_masking_patterns is None:
            self.filters.pii_masking_patterns = [
                r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
                r'\b[A-Z]{2}\d{6}\b',      # Passport pattern
                r'\b\d{16}\b',              # Credit card pattern
                r'\b[\w\.-]+@[\w\.-]+\.\w{2,4}\b'  # Email pattern
            ]


class AuditConfigManager:
    """Manages audit logging configuration"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "./audit_config.json"
        self.config = self.load_config()

    def load_config(self) -> AuditConfig:
        """Load configuration from file or use defaults"""
        if self.config_path and os.path.exists(self.config_path):
            path = Path(self.config_path)
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            return self._dict_to_config(data)
        else:
            return AuditConfig()

    def save_config(self, config: AuditConfig = None, path: str = None) -> bool:
        """Save configuration to file"""
        save_path = Path(path if path else self.config_path)
        config_to_save = config or self.config

        try:
            config_dict = self._config_to_dict(config_to_save)
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_dict, f, default_flow_style=False)
                else:
                    json.dump(config_dict, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def _dict_to_config(self, data: Dict[str, Any]) -> AuditConfig:
        """Convert dictionary to AuditConfig object"""
        storage_data = data.get('storage', {})
        security_data = data.get('security', {})
        retention_data = data.get('retention', {})
        filters_data = data.get('filters', {})

        return AuditConfig(
            enabled=data.get('enabled', True),
            log_format=data.get('log_format', 'structured_json'),
            storage=AuditStorageConfig(**storage_data) if storage_data else AuditStorageConfig(),
            security=AuditSecurityConfig(**security_data) if security_data else AuditSecurityConfig(),
            retention=AuditRetentionConfig(**retention_data) if retention_data else AuditRetentionConfig(),
            filters=AuditFilterConfig(**filters_data) if filters_data else AuditFilterConfig()
        )

    def _config_to_dict(self, config: AuditConfig) -> Dict[str, Any]:
        """Convert AuditConfig object to dictionary"""
        return {
            'enabled': config.enabled,
            'log_format': config.log_format,
            'storage': asdict(config.storage),
            'security': asdict(config.security),
            'retention': asdict(config.retention),
            'filters': asdict(config.filters)
        }

    def validate_config(self) -> list:
        """Validate configuration and return list of errors"""
        errors = []

        # Validate storage path
        storage_path = Path(self.config.storage.storage_path)
        try:
            storage_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            errors.append(f"Cannot create storage path: {storage_path}")

        # Validate retention settings
        if self.config.retention.retention_days < 1:
            errors.append("retention_days must be positive")
        if self.config.retention.security_event_retention_days < 1:
            errors.append("security_event_retention_days must be positive")

        # Validate log format
        if self.config.log_format not in ['structured_json', 'json', 'text']:
            errors.append("log_format must be 'structured_json', 'json', or 'text'")

        # Validate log level
        if self.config.filters.min_log_level not in ['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']:
            errors.append("min_log_level must be one of DEBUG, INFO, WARN, ERROR, CRITICAL")

        return errors

    def update_config(self, **kwargs):
        """Update configuration with provided values"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                # Check nested attributes
                for attr_name in ['storage', 'security', 'retention', 'filters']:
                    attr = getattr(self.config, attr_name)
                    if hasattr(attr, key):
                        setattr(attr, key, value)
                        break
                else:
                    raise AttributeError(f"No attribute '{key}' found in config")

    def get_effective_config(self) -> Dict[str, Any]:
        """Get effective configuration as dictionary"""
        return self._config_to_dict(self.config)


def create_default_config(path: str = "./audit_config.json"):
    """Create a default configuration file"""
    config_manager = AuditConfigManager()
    default_config = AuditConfig()

    # Create directory if it doesn't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    success = config_manager.save_config(default_config, path)
    if success:
        print(f"Created default configuration at {path}")
        print("Configuration includes:")
        print("  - 90-day retention (extendable for compliance/security)")
        print("  - Structured JSON logging")
        print("  - Encryption and signing enabled")
        print("  - PII masking patterns")
        print("  - Storage path: ./audit_logs")
    else:
        print(f"Failed to create configuration at {path}")


def validate_config_file(config_path: str) -> bool:
    """Validate a configuration file"""
    try:
        config_manager = AuditConfigManager(config_path)
        errors = config_manager.validate_config()

        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("Configuration is valid!")
            return True
    except Exception as e:
        print(f"Error validating configuration: {e}")
        return False


def show_config(config_path: str = "./audit_config.json"):
    """Display current configuration"""
    try:
        config_manager = AuditConfigManager(config_path)
        config_dict = config_manager.get_effective_config()

        print("Current Audit Configuration:")
        print(json.dumps(config_dict, indent=2))
    except Exception as e:
        print(f"Error displaying configuration: {e}")


def main():
    """Main entry point for configuration management"""
    import argparse

    parser = argparse.ArgumentParser(description="Audit Logging System Configuration Manager")
    parser.add_argument("action", choices=["create-default", "validate", "show", "update"],
                       help="Action to perform")
    parser.add_argument("--config", default="./audit_config.json",
                       help="Path to configuration file")
    parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"),
                       help="Set a configuration value (key value)")

    args = parser.parse_args()

    if args.action == "create-default":
        create_default_config(args.config)
    elif args.action == "validate":
        validate_config_file(args.config)
    elif args.action == "show":
        show_config(args.config)
    elif args.action == "update":
        if not args.set:
            print("Error: --set KEY VALUE required for update action")
            return

        try:
            config_manager = AuditConfigManager(args.config)
            key, value = args.set

            # Try to convert value to appropriate type
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)

            config_manager.update_config(**{key: value})

            # Save the updated configuration
            if config_manager.save_config():
                print(f"Updated {key} = {value}")
            else:
                print("Failed to save configuration")

        except AttributeError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Error updating configuration: {e}")


if __name__ == "__main__":
    main()