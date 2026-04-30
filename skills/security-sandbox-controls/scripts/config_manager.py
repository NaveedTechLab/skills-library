#!/usr/bin/env python3
"""
Configuration Manager for Security Sandbox Controls

Manages configuration for safety controls including DRY_RUN mode, rate limits,
credential isolation, and permission boundaries.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, asdict, field
from enum import Enum

from safety_controls import SafetyMode, RateLimitRule, SafetyConfig


@dataclass
class SecuritySandboxConfig:
    """Complete security sandbox configuration"""
    mode: SafetyMode = SafetyMode.DEVELOPMENT
    dry_run_enabled: bool = False
    rate_limits: Dict[str, RateLimitRule] = field(default_factory=dict)
    credentials_isolated: bool = True
    permission_enforcement: bool = True
    dangerous_operations_allowed: bool = False
    log_level: str = "INFO"
    audit_logging: bool = True
    environment: str = "development"

    def __post_init__(self):
        # Set default rate limits if not provided
        if not self.rate_limits:
            self.rate_limits = {
                "file_operations": RateLimitRule(max_operations=100, window_seconds=60),
                "network_requests": RateLimitRule(max_operations=50, window_seconds=60),
                "system_commands": RateLimitRule(max_operations=20, window_seconds=60),
                "credential_access": RateLimitRule(max_operations=10, window_seconds=60),
            }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        result = asdict(self)
        # Convert enums to strings
        result['mode'] = self.mode.value
        # Convert RateLimitRule objects to dictionaries
        rate_limits_dict = {}
        for key, rule in self.rate_limits.items():
            rate_limits_dict[key] = {
                'max_operations': rule.max_operations,
                'window_seconds': rule.window_seconds,
                'burst_allowance': rule.burst_allowance,
                'per_user': rule.per_user,
                'per_resource': rule.per_resource
            }
        result['rate_limits'] = rate_limits_dict
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create configuration from dictionary"""
        # Convert string mode back to enum
        mode_str = data.get('mode', 'DEVELOPMENT')
        mode = SafetyMode(mode_str) if isinstance(mode_str, str) else mode_str

        # Convert rate limit dictionaries back to RateLimitRule objects
        rate_limits_data = data.get('rate_limits', {})
        rate_limits = {}
        for key, rule_data in rate_limits_data.items():
            rate_limits[key] = RateLimitRule(
                max_operations=rule_data['max_operations'],
                window_seconds=rule_data['window_seconds'],
                burst_allowance=rule_data.get('burst_allowance', 0),
                per_user=rule_data.get('per_user', False),
                per_resource=rule_data.get('per_resource', False)
            )

        return cls(
            mode=mode,
            dry_run_enabled=data.get('dry_run_enabled', False),
            rate_limits=rate_limits,
            credentials_isolated=data.get('credentials_isolated', True),
            permission_enforcement=data.get('permission_enforcement', True),
            dangerous_operations_allowed=data.get('dangerous_operations_allowed', False),
            log_level=data.get('log_level', 'INFO'),
            audit_logging=data.get('audit_logging', True),
            environment=data.get('environment', 'development')
        )


class ConfigManager:
    """Manages security sandbox configuration"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "./security_sandbox_config.json"
        self.config = self.load_config()

    def load_config(self) -> SecuritySandboxConfig:
        """Load configuration from file or use defaults"""
        if self.config_path and os.path.exists(self.config_path):
            path = Path(self.config_path)
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            return SecuritySandboxConfig.from_dict(data)
        else:
            return SecuritySandboxConfig()

    def save_config(self, config: SecuritySandboxConfig = None, path: str = None) -> bool:
        """Save configuration to file"""
        save_path = Path(path if path else self.config_path)
        config_to_save = config or self.config

        try:
            config_dict = config_to_save.to_dict()
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_dict, f, default_flow_style=False)
                else:
                    json.dump(config_dict, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def validate_config(self) -> list:
        """Validate configuration and return list of errors"""
        errors = []

        # Validate mode
        if not isinstance(self.config.mode, SafetyMode):
            try:
                SafetyMode(self.config.mode)
            except ValueError:
                errors.append(f"Invalid mode: {self.config.mode}")

        # Validate rate limits
        for key, rule in self.config.rate_limits.items():
            if rule.max_operations <= 0:
                errors.append(f"Rate limit max_operations must be positive for {key}")
            if rule.window_seconds <= 0:
                errors.append(f"Rate limit window_seconds must be positive for {key}")

        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.config.log_level not in valid_log_levels:
            errors.append(f"log_level must be one of {valid_log_levels}")

        # Validate environment
        valid_environments = ['development', 'staging', 'production']
        if self.config.environment not in valid_environments:
            errors.append(f"environment must be one of {valid_environments}")

        return errors

    def update_config(self, **kwargs):
        """Update configuration with provided values"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                # Handle enum conversion for mode
                if key == 'mode' and isinstance(value, str):
                    value = SafetyMode(value)
                setattr(self.config, key, value)
            else:
                raise AttributeError(f"No attribute '{key}' found in config")

    def get_effective_config(self) -> Dict[str, Any]:
        """Get effective configuration as dictionary"""
        return self.config.to_dict()

    def get_environment_config(self, environment: str) -> SecuritySandboxConfig:
        """Get configuration appropriate for the specified environment"""
        base_config = self.load_config()

        # Apply environment-specific overrides
        if environment == 'production':
            base_config.mode = SafetyMode.PRODUCTION
            base_config.permission_enforcement = True
            base_config.dangerous_operations_allowed = False
            base_config.audit_logging = True
            # Stricter rate limits for production
            base_config.rate_limits = {
                "file_operations": RateLimitRule(max_operations=50, window_seconds=60),
                "network_requests": RateLimitRule(max_operations=25, window_seconds=60),
                "system_commands": RateLimitRule(max_operations=10, window_seconds=60),
                "credential_access": RateLimitRule(max_operations=5, window_seconds=60),
            }
        elif environment == 'staging':
            base_config.mode = SafetyMode.STAGING
            base_config.permission_enforcement = True
            base_config.dangerous_operations_allowed = False
        elif environment == 'development':
            base_config.mode = SafetyMode.DEVELOPMENT
            base_config.dry_run_enabled = True  # Enable dry-run by default in dev

        base_config.environment = environment
        return base_config


def create_default_config(path: str = "./security_sandbox_config.json"):
    """Create a default configuration file"""
    config_manager = ConfigManager()
    default_config = SecuritySandboxConfig()

    # Create directory if it doesn't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    success = config_manager.save_config(default_config, path)
    if success:
        print(f"Created default configuration at {path}")
        print("Configuration includes:")
        print("  - Development mode with dry-run capability")
        print("  - Moderate rate limiting")
        print("  - Credential isolation enabled")
        print("  - Permission enforcement enabled")
        print("  - Audit logging enabled")
    else:
        print(f"Failed to create configuration at {path}")


def create_production_config(path: str = "./production_security_sandbox_config.json"):
    """Create a production-ready configuration file"""
    config = SecuritySandboxConfig(
        mode=SafetyMode.PRODUCTION,
        dry_run_enabled=False,
        credentials_isolated=True,
        permission_enforcement=True,
        dangerous_operations_allowed=False,
        audit_logging=True,
        environment="production",
        rate_limits={
            "file_operations": RateLimitRule(max_operations=50, window_seconds=60),
            "network_requests": RateLimitRule(max_operations=25, window_seconds=60),
            "system_commands": RateLimitRule(max_operations=10, window_seconds=60),
            "credential_access": RateLimitRule(max_operations=5, window_seconds=60),
        }
    )

    # Create directory if it doesn't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2)
        print(f"Created production configuration at {path}")
        print("Production configuration includes:")
        print("  - Production mode with strict controls")
        print("  - No dry-run mode")
        print("  - All safety controls enabled")
        print("  - Restrictive rate limits")
    except Exception as e:
        print(f"Failed to create production configuration at {path}: {e}")


def validate_config_file(config_path: str) -> bool:
    """Validate a configuration file"""
    try:
        config_manager = ConfigManager(config_path)
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


def show_config(config_path: str = "./security_sandbox_config.json"):
    """Display current configuration"""
    try:
        config_manager = ConfigManager(config_path)
        config_dict = config_manager.get_effective_config()

        print("Current Security Sandbox Configuration:")
        print(json.dumps(config_dict, indent=2))
    except Exception as e:
        print(f"Error displaying configuration: {e}")


def main():
    """Main entry point for configuration management"""
    import argparse

    parser = argparse.ArgumentParser(description="Security Sandbox Controls Configuration Manager")
    parser.add_argument("action", choices=["create-default", "create-production", "validate", "show", "update"],
                       help="Action to perform")
    parser.add_argument("--config", default="./security_sandbox_config.json",
                       help="Path to configuration file")
    parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"),
                       help="Set a configuration value (key value)")

    args = parser.parse_args()

    if args.action == "create-default":
        create_default_config(args.config)
    elif args.action == "create-production":
        create_production_config(args.config)
    elif args.action == "validate":
        validate_config_file(args.config)
    elif args.action == "show":
        show_config(args.config)
    elif args.action == "update":
        if not args.set:
            print("Error: --set KEY VALUE required for update action")
            return

        try:
            config_manager = ConfigManager(args.config)
            key, value = args.set

            # Try to convert value to appropriate type
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)
            elif value in [mode.value for mode in SafetyMode]:
                value = SafetyMode(value)

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