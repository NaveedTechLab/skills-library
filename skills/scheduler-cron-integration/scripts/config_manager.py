#!/usr/bin/env python3
"""
Configuration Manager for Scheduler Cron Integration

Manages configuration for the scheduling system including scheduler settings,
cron parsing options, and job execution parameters.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, asdict, field
from enum import Enum

from scheduler_core import JobPriority


class SchedulerLogLevel(Enum):
    """Log levels for the scheduler"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class SchedulerConfig:
    """Configuration for the scheduler core"""
    enabled: bool = True
    max_concurrent_jobs: int = 10
    job_storage_path: str = "./scheduled_jobs.db"
    log_retention_days: int = 30
    check_interval_seconds: int = 30
    log_level: str = "INFO"
    timezone: str = "UTC"
    max_execution_time_minutes: int = 60
    enable_persistence: bool = True
    backup_on_startup: bool = False


@dataclass
class CronConfig:
    """Configuration for cron expression parsing"""
    support_seconds: bool = True
    timezone: str = "UTC"
    max_execution_time_minutes: int = 60
    validate_expressions: bool = True
    allow_aliases: bool = True
    extended_format: bool = True


@dataclass
class JobDefaultsConfig:
    """Default settings for jobs"""
    default_timeout_minutes: int = 10
    max_retries: int = 3
    retry_delay_seconds: int = 30
    default_priority: JobPriority = JobPriority.NORMAL
    enable_notifications: bool = True
    notify_on_failure: bool = True
    notify_on_success: bool = False
    max_history_records: int = 100


@dataclass
class SecurityConfig:
    """Security-related configuration"""
    enforce_permissions: bool = False
    allowed_users: list = field(default_factory=list)
    restricted_commands: list = field(default_factory=list)
    audit_logging: bool = True
    require_authentication: bool = True


@dataclass
class SchedulerSystemConfig:
    """Complete scheduler system configuration"""
    scheduler: SchedulerConfig = None
    cron: CronConfig = None
    jobs: JobDefaultsConfig = None
    security: SecurityConfig = None

    def __post_init__(self):
        if self.scheduler is None:
            self.scheduler = SchedulerConfig()
        if self.cron is None:
            self.cron = CronConfig()
        if self.jobs is None:
            self.jobs = JobDefaultsConfig()
        if self.security is None:
            self.security = SecurityConfig()

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        result = {}
        result['scheduler'] = asdict(self.scheduler)
        result['cron'] = asdict(self.cron)
        result['jobs'] = asdict(self.jobs)
        result['security'] = asdict(self.security)

        # Convert enum values to strings
        result['jobs']['default_priority'] = self.jobs.default_priority.name

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create configuration from dictionary"""
        scheduler_data = data.get('scheduler', {})
        cron_data = data.get('cron', {})
        jobs_data = data.get('jobs', {})
        security_data = data.get('security', {})

        # Handle enum conversion for priority
        priority_str = jobs_data.get('default_priority', 'NORMAL')
        if isinstance(priority_str, str):
            priority = JobPriority[priority_str.upper()]
        else:
            priority = priority_str

        scheduler_config = SchedulerConfig(**scheduler_data)
        cron_config = CronConfig(**cron_data)
        job_defaults_config = JobDefaultsConfig(
            **{k: v for k, v in jobs_data.items() if k != 'default_priority'},
            default_priority=priority
        )
        security_config = SecurityConfig(**security_data)

        return cls(
            scheduler=scheduler_config,
            cron=cron_config,
            jobs=job_defaults_config,
            security=security_config
        )


class ConfigManager:
    """Manages scheduler system configuration"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "./scheduler_config.json"
        self.config = self.load_config()

    def load_config(self) -> SchedulerSystemConfig:
        """Load configuration from file or use defaults"""
        if self.config_path and os.path.exists(self.config_path):
            path = Path(self.config_path)
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            return SchedulerSystemConfig.from_dict(data)
        else:
            return SchedulerSystemConfig()

    def save_config(self, config: SchedulerSystemConfig = None, path: str = None) -> bool:
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

        # Validate scheduler config
        if self.config.scheduler.max_concurrent_jobs <= 0:
            errors.append("max_concurrent_jobs must be positive")
        if self.config.scheduler.check_interval_seconds <= 0:
            errors.append("check_interval_seconds must be positive")
        if self.config.scheduler.log_retention_days <= 0:
            errors.append("log_retention_days must be positive")

        # Validate cron config
        if self.config.cron.max_execution_time_minutes <= 0:
            errors.append("max_execution_time_minutes must be positive")

        # Validate job defaults
        if self.config.jobs.default_timeout_minutes <= 0:
            errors.append("default_timeout_minutes must be positive")
        if self.config.jobs.max_retries < 0:
            errors.append("max_retries must be non-negative")
        if self.config.jobs.retry_delay_seconds < 0:
            errors.append("retry_delay_seconds must be non-negative")
        if self.config.jobs.max_history_records <= 0:
            errors.append("max_history_records must be positive")

        # Validate log level
        valid_log_levels = [level.value for level in SchedulerLogLevel]
        if self.config.scheduler.log_level not in valid_log_levels:
            errors.append(f"log_level must be one of {valid_log_levels}")

        return errors

    def update_config(self, **kwargs):
        """Update configuration with provided values"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                # Check nested attributes
                for attr_name in ['scheduler', 'cron', 'jobs', 'security']:
                    attr = getattr(self.config, attr_name)
                    if hasattr(attr, key):
                        setattr(attr, key, value)
                        break
                else:
                    raise AttributeError(f"No attribute '{key}' found in config")

    def get_effective_config(self) -> Dict[str, Any]:
        """Get effective configuration as dictionary"""
        return self.config.to_dict()

    def get_scheduler_config(self) -> SchedulerConfig:
        """Get scheduler-specific configuration"""
        return self.config.scheduler

    def get_cron_config(self) -> CronConfig:
        """Get cron-specific configuration"""
        return self.config.cron

    def get_job_defaults_config(self) -> JobDefaultsConfig:
        """Get job defaults configuration"""
        return self.config.jobs

    def get_security_config(self) -> SecurityConfig:
        """Get security configuration"""
        return self.config.security


def create_default_config(path: str = "./scheduler_config.json"):
    """Create a default configuration file"""
    config_manager = ConfigManager()
    default_config = SchedulerSystemConfig()

    # Create directory if it doesn't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    success = config_manager.save_config(default_config, path)
    if success:
        print(f"Created default configuration at {path}")
        print("Configuration includes:")
        print("  - 10 max concurrent jobs")
        print("  - 30-second check interval")
        print("  - 30-day log retention")
        print("  - 10-minute default job timeout")
        print("  - 3 max retries with 30-second delay")
        print("  - UTC timezone by default")
    else:
        print(f"Failed to create configuration at {path}")


def create_production_config(path: str = "./production_scheduler_config.json"):
    """Create a production-ready configuration file"""
    config = SchedulerSystemConfig(
        scheduler=SchedulerConfig(
            enabled=True,
            max_concurrent_jobs=20,
            job_storage_path="/var/lib/scheduler/jobs.db",
            log_retention_days=90,
            check_interval_seconds=15,
            log_level="INFO",
            timezone="UTC",
            max_execution_time_minutes=120,
            enable_persistence=True,
            backup_on_startup=True
        ),
        cron=CronConfig(
            support_seconds=True,
            timezone="UTC",
            max_execution_time_minutes=120,
            validate_expressions=True,
            allow_aliases=True,
            extended_format=True
        ),
        jobs=JobDefaultsConfig(
            default_timeout_minutes=30,
            max_retries=5,
            retry_delay_seconds=60,
            default_priority=JobPriority.NORMAL,
            enable_notifications=True,
            notify_on_failure=True,
            notify_on_success=False,
            max_history_records=500
        ),
        security=SecurityConfig(
            enforce_permissions=True,
            allowed_users=["admin", "scheduler"],
            restricted_commands=["rm", "shutdown", "reboot"],
            audit_logging=True,
            require_authentication=True
        )
    )

    # Create directory if it doesn't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    try:
        config_manager = ConfigManager()
        success = config_manager.save_config(config, path)
        if success:
            print(f"Created production configuration at {path}")
            print("Production configuration includes:")
            print("  - Higher concurrency (20 jobs)")
            print("  - Longer retention (90 days)")
            print("  - More retries (5) with longer delays (60s)")
            print("  - Enhanced security settings")
        else:
            print(f"Failed to create production configuration at {path}")
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


def show_config(config_path: str = "./scheduler_config.json"):
    """Display current configuration"""
    try:
        config_manager = ConfigManager(config_path)
        config_dict = config_manager.get_effective_config()

        print("Current Scheduler Configuration:")
        print(json.dumps(config_dict, indent=2))
    except Exception as e:
        print(f"Error displaying configuration: {e}")


def migrate_config(old_config_path: str, new_config_path: str) -> bool:
    """Migrate an old configuration format to the new format"""
    try:
        # Load old config as raw JSON/YAML
        old_path = Path(old_config_path)
        with open(old_path, 'r', encoding='utf-8') as f:
            if old_path.suffix.lower() in ['.yaml', '.yml']:
                old_data = yaml.safe_load(f)
            else:
                old_data = json.load(f)

        # Transform old format to new format
        # Old format had flat structure, new has nested sections
        if 'scheduler' not in old_data:
            # It's an old flat format, transform it
            new_data = {
                'scheduler': {
                    'enabled': old_data.get('enabled', True),
                    'max_concurrent_jobs': old_data.get('max_concurrent_jobs', 10),
                    'job_storage_path': old_data.get('job_storage_path', './scheduled_jobs.db'),
                    'log_retention_days': old_data.get('log_retention_days', 30),
                    'check_interval_seconds': old_data.get('check_interval_seconds', 30),
                    'log_level': old_data.get('log_level', 'INFO'),
                    'timezone': old_data.get('timezone', 'UTC'),
                    'max_execution_time_minutes': old_data.get('max_execution_time_minutes', 60),
                    'enable_persistence': old_data.get('enable_persistence', True),
                    'backup_on_startup': old_data.get('backup_on_startup', False)
                },
                'cron': {
                    'support_seconds': old_data.get('support_seconds', True),
                    'timezone': old_data.get('timezone', 'UTC'),
                    'max_execution_time_minutes': old_data.get('max_execution_time_minutes', 60),
                    'validate_expressions': old_data.get('validate_expressions', True),
                    'allow_aliases': old_data.get('allow_aliases', True),
                    'extended_format': old_data.get('extended_format', True)
                },
                'jobs': {
                    'default_timeout_minutes': old_data.get('default_timeout_minutes', 10),
                    'max_retries': old_data.get('max_retries', 3),
                    'retry_delay_seconds': old_data.get('retry_delay_seconds', 30),
                    'default_priority': old_data.get('default_priority', 'NORMAL'),
                    'enable_notifications': old_data.get('enable_notifications', True),
                    'notify_on_failure': old_data.get('notify_on_failure', True),
                    'notify_on_success': old_data.get('notify_on_success', False),
                    'max_history_records': old_data.get('max_history_records', 100)
                },
                'security': {
                    'enforce_permissions': old_data.get('enforce_permissions', False),
                    'allowed_users': old_data.get('allowed_users', []),
                    'restricted_commands': old_data.get('restricted_commands', []),
                    'audit_logging': old_data.get('audit_logging', True),
                    'require_authentication': old_data.get('require_authentication', True)
                }
            }
        else:
            # Already in new format
            new_data = old_data

        # Save the transformed config
        new_path = Path(new_config_path)
        with open(new_path, 'w', encoding='utf-8') as f:
            if new_path.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(new_data, f, default_flow_style=False)
            else:
                json.dump(new_data, f, indent=2)

        print(f"Configuration migrated from {old_config_path} to {new_config_path}")
        return True

    except Exception as e:
        print(f"Error migrating configuration: {e}")
        return False


def main():
    """Main entry point for configuration management"""
    import argparse

    parser = argparse.ArgumentParser(description="Scheduler Cron Integration Configuration Manager")
    parser.add_argument("action", choices=["create-default", "create-production", "validate", "show", "update", "migrate"],
                       help="Action to perform")
    parser.add_argument("--config", default="./scheduler_config.json",
                       help="Path to configuration file")
    parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"),
                       help="Set a configuration value (key value)")
    parser.add_argument("--old-config", help="Path to old configuration file (for migration)")

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
            elif value in [level.value for level in SchedulerLogLevel]:
                value = SchedulerLogLevel(value)
            elif value in [priority.name for priority in JobPriority]:
                value = JobPriority[value]

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
    elif args.action == "migrate":
        if not args.old_config:
            print("Error: --old-config PATH required for migration")
            return
        migrate_config(args.old_config, args.config)


if __name__ == "__main__":
    main()