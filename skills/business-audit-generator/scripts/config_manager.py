#!/usr/bin/env python3
"""
Configuration Manager for Business Audit Generator

Manages configuration for the business audit system including analysis settings,
reporting preferences, and data source configurations.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, asdict, field
from datetime import datetime

import structlog

from business_audit_core import ReportPeriod

logger = structlog.get_logger()


@dataclass
class AnalysisConfig:
    """Configuration for data analysis"""
    include_task_completion: bool = True
    include_financial_metrics: bool = True
    include_goal_progress: bool = True
    include_sales_data: bool = True
    include_operational_metrics: bool = True
    task_completion_threshold: float = 0.8
    financial_variance_threshold: float = 0.1
    goal_progress_threshold: float = 0.75
    anomaly_detection_enabled: bool = True
    correlation_analysis_enabled: bool = True
    trend_analysis_enabled: bool = True
    data_quality_check_enabled: bool = True


@dataclass
class ReportingConfig:
    """Configuration for report generation"""
    report_title: str = "Monday Morning CEO Briefing"
    report_frequency: ReportPeriod = ReportPeriod.WEEKLY
    report_day: str = "monday"
    report_time: str = "08:00"
    output_formats: list = field(default_factory=lambda: ["pdf", "html", "email"])
    distribution_list: list = field(default_factory=lambda: ["ceo@company.com"])
    include_charts: bool = True
    include_recommendations: bool = True
    include_risk_assessment: bool = True
    include_trend_analysis: bool = True
    include_correlation_analysis: bool = True


@dataclass
class MetricThresholdsConfig:
    """Configuration for metric thresholds and risk levels"""
    task_completion_threshold: float = 0.8
    financial_variance_threshold: float = 0.1
    goal_progress_threshold: float = 0.75
    risk_identification_criteria: Dict[str, float] = field(default_factory=dict)
    performance_level_definitions: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.risk_identification_criteria:
            self.risk_identification_criteria = {
                "low": 0.2,
                "medium": 0.5,
                "high": 0.8
            }

        if not self.performance_level_definitions:
            self.performance_level_definitions = {
                "excellent": {"min": 0.9, "max": 1.0},
                "good": {"min": 0.8, "max": 0.89},
                "fair": {"min": 0.7, "max": 0.79},
                "poor": {"min": 0.5, "max": 0.69},
                "critical": {"min": 0.0, "max": 0.49}
            }


@dataclass
class DataSourceConfig:
    """Configuration for data sources"""
    task_system_url: Optional[str] = None
    finance_system_url: Optional[str] = None
    crm_system_url: Optional[str] = None
    goals_system_url: Optional[str] = None
    sales_system_url: Optional[str] = None
    operational_system_url: Optional[str] = None
    task_system_auth: Optional[Dict[str, str]] = field(default_factory=dict)
    finance_system_auth: Optional[Dict[str, str]] = field(default_factory=dict)
    crm_system_auth: Optional[Dict[str, str]] = field(default_factory=dict)
    goals_system_auth: Optional[Dict[str, str]] = field(default_factory=dict)
    data_refresh_interval_minutes: int = 60
    max_data_age_hours: int = 24


@dataclass
class NotificationConfig:
    """Configuration for notifications"""
    email_enabled: bool = True
    slack_enabled: bool = False
    webhook_enabled: bool = False
    email_template_path: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    webhook_urls: list = field(default_factory=list)
    notification_recipients: list = field(default_factory=list)
    notify_on_failure: bool = True
    notify_on_success: bool = False
    notify_on_anomalies: bool = True


@dataclass
class BusinessAuditConfig:
    """Complete business audit system configuration"""
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    metrics: MetricThresholdsConfig = field(default_factory=MetricThresholdsConfig)
    data_sources: DataSourceConfig = field(default_factory=DataSourceConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    system_settings: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.system_settings:
            self.system_settings = {
                "debug_mode": False,
                "log_level": "INFO",
                "max_report_history_days": 90,
                "backup_enabled": True,
                "audit_trail_enabled": True
            }


class ConfigManager:
    """Manages business audit system configuration"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "./business_audit_config.json"
        self.config = self.load_config()
        self.logger = logger.bind(component="ConfigManager")

    def load_config(self) -> BusinessAuditConfig:
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
            return BusinessAuditConfig()

    def save_config(self, config: BusinessAuditConfig = None, path: str = None) -> bool:
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

            self.logger.info("Configuration saved", config_path=str(save_path))
            return True
        except Exception as e:
            self.logger.error("Error saving config", error=str(e))
            return False

    def _dict_to_config(self, data: Dict[str, Any]) -> BusinessAuditConfig:
        """Convert dictionary to BusinessAuditConfig object"""
        analysis_data = data.get('analysis', {})
        reporting_data = data.get('reporting', {})
        metrics_data = data.get('metrics', {})
        data_sources_data = data.get('data_sources', {})
        notifications_data = data.get('notifications', {})
        system_settings_data = data.get('system_settings', {})

        # Handle enum conversion for report frequency
        report_freq_str = reporting_data.get('report_frequency', 'weekly')
        if isinstance(report_freq_str, str):
            try:
                report_frequency = ReportPeriod(report_freq_str.lower())
            except ValueError:
                report_frequency = ReportPeriod.WEEKLY
        else:
            report_frequency = report_freq_str

        # Create individual config objects
        analysis_config = AnalysisConfig(**{k: v for k, v in analysis_data.items()})
        reporting_config = ReportingConfig(
            **{k: v for k, v in reporting_data.items() if k != 'report_frequency'},
            report_frequency=report_frequency
        )
        metrics_config = MetricThresholdsConfig(**{k: v for k, v in metrics_data.items()})
        data_sources_config = DataSourceConfig(**{k: v for k, v in data_sources_data.items()})
        notifications_config = NotificationConfig(**{k: v for k, v in notifications_data.items()})

        return BusinessAuditConfig(
            analysis=analysis_config,
            reporting=reporting_config,
            metrics=metrics_config,
            data_sources=data_sources_config,
            notifications=notifications_config,
            system_settings=system_settings_data
        )

    def _config_to_dict(self, config: BusinessAuditConfig) -> Dict[str, Any]:
        """Convert BusinessAuditConfig object to dictionary"""
        reporting_dict = asdict(config.reporting)
        # Convert enum to string for serialization
        reporting_dict['report_frequency'] = config.reporting.report_frequency.value

        return {
            'analysis': asdict(config.analysis),
            'reporting': reporting_dict,
            'metrics': asdict(config.metrics),
            'data_sources': asdict(config.data_sources),
            'notifications': asdict(config.notifications),
            'system_settings': config.system_settings
        }

    def validate_config(self) -> list:
        """Validate configuration and return list of errors"""
        errors = []

        # Validate analysis configuration
        if self.config.analysis.task_completion_threshold < 0 or self.config.analysis.task_completion_threshold > 1:
            errors.append("task_completion_threshold must be between 0 and 1")

        if self.config.analysis.financial_variance_threshold < 0:
            errors.append("financial_variance_threshold must be non-negative")

        if self.config.analysis.goal_progress_threshold < 0 or self.config.analysis.goal_progress_threshold > 1:
            errors.append("goal_progress_threshold must be between 0 and 1")

        # Validate reporting configuration
        valid_periods = [period.value for period in ReportPeriod]
        if self.config.reporting.report_frequency.value not in valid_periods:
            errors.append(f"report_frequency must be one of {valid_periods}")

        valid_formats = ["pdf", "html", "email", "json", "csv"]
        invalid_formats = [fmt for fmt in self.config.reporting.output_formats if fmt not in valid_formats]
        if invalid_formats:
            errors.append(f"Invalid output formats: {invalid_formats}")

        # Validate metric thresholds
        if self.config.metrics.task_completion_threshold < 0 or self.config.metrics.task_completion_threshold > 1:
            errors.append("metrics.task_completion_threshold must be between 0 and 1")

        if self.config.metrics.goal_progress_threshold < 0 or self.config.metrics.goal_progress_threshold > 1:
            errors.append("metrics.goal_progress_threshold must be between 0 and 1")

        # Validate data source configuration
        if self.config.data_sources.data_refresh_interval_minutes <= 0:
            errors.append("data_refresh_interval_minutes must be positive")

        if self.config.data_sources.max_data_age_hours <= 0:
            errors.append("max_data_age_hours must be positive")

        return errors

    def update_config(self, **kwargs):
        """Update configuration with provided values"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                # Check nested attributes
                for attr_name in ['analysis', 'reporting', 'metrics', 'data_sources', 'notifications']:
                    attr = getattr(self.config, attr_name)
                    if hasattr(attr, key):
                        setattr(attr, key, value)
                        break
                else:
                    raise AttributeError(f"No attribute '{key}' found in config")

    def get_effective_config(self) -> Dict[str, Any]:
        """Get effective configuration as dictionary"""
        return self._config_to_dict(self.config)

    def get_analysis_config(self) -> AnalysisConfig:
        """Get analysis-specific configuration"""
        return self.config.analysis

    def get_reporting_config(self) -> ReportingConfig:
        """Get reporting-specific configuration"""
        return self.config.reporting

    def get_metric_thresholds_config(self) -> MetricThresholdsConfig:
        """Get metric thresholds configuration"""
        return self.config.metrics

    def get_data_source_config(self) -> DataSourceConfig:
        """Get data source configuration"""
        return self.config.data_sources

    def get_notification_config(self) -> NotificationConfig:
        """Get notification configuration"""
        return self.config.notifications

    def reload_config(self):
        """Reload configuration from file"""
        self.config = self.load_config()
        self.logger.info("Configuration reloaded", config_path=self.config_path)

    def create_backup(self, backup_path: Optional[str] = None) -> bool:
        """Create a backup of the current configuration"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.config_path}.backup.{timestamp}"

        return self.save_config(self.config, backup_path)


def create_default_config(path: str = "./business_audit_config.json") -> bool:
    """Create a default configuration file"""
    config_manager = ConfigManager()
    default_config = BusinessAuditConfig()

    # Create directory if it doesn't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    success = config_manager.save_config(default_config, path)
    if success:
        logger.info("Default configuration created", config_path=path)
        print(f"Created default configuration at {path}")
        print("Configuration includes:")
        print("  - Weekly reporting schedule")
        print("  - All analysis modules enabled")
        print("  - HTML and email output formats")
        print("  - Standard metric thresholds")
    else:
        print(f"Failed to create configuration at {path}")

    return success


def create_production_config(path: str = "./production_business_audit_config.json") -> bool:
    """Create a production-ready configuration file"""
    config = BusinessAuditConfig(
        analysis=AnalysisConfig(
            include_task_completion=True,
            include_financial_metrics=True,
            include_goal_progress=True,
            include_sales_data=True,
            include_operational_metrics=True,
            task_completion_threshold=0.85,
            financial_variance_threshold=0.05,
            goal_progress_threshold=0.8,
            anomaly_detection_enabled=True,
            correlation_analysis_enabled=True,
            trend_analysis_enabled=True,
            data_quality_check_enabled=True
        ),
        reporting=ReportingConfig(
            report_title="Monday Morning CEO Briefing",
            report_frequency=ReportPeriod.WEEKLY,
            report_day="monday",
            report_time="08:00",
            output_formats=["pdf", "html", "email"],
            distribution_list=["ceo@company.com", "executive-team@company.com"],
            include_charts=True,
            include_recommendations=True,
            include_risk_assessment=True,
            include_trend_analysis=True,
            include_correlation_analysis=True
        ),
        metrics=MetricThresholdsConfig(
            task_completion_threshold=0.85,
            financial_variance_threshold=0.05,
            goal_progress_threshold=0.8,
            risk_identification_criteria={
                "low": 0.15,
                "medium": 0.4,
                "high": 0.75
            }
        ),
        data_sources=DataSourceConfig(
            data_refresh_interval_minutes=30,
            max_data_age_hours=12
        ),
        notifications=NotificationConfig(
            email_enabled=True,
            slack_enabled=True,
            notify_on_failure=True,
            notify_on_success=False,
            notify_on_anomalies=True
        ),
        system_settings={
            "debug_mode": False,
            "log_level": "INFO",
            "max_report_history_days": 180,
            "backup_enabled": True,
            "audit_trail_enabled": True
        }
    )

    # Create directory if it doesn't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    try:
        config_manager = ConfigManager()
        success = config_manager.save_config(config, path)
        if success:
            logger.info("Production configuration created", config_path=path)
            print(f"Created production configuration at {path}")
            print("Production configuration includes:")
            print("  - Stricter thresholds for metrics")
            print("  - More frequent data refresh (30 min)")
            print("  - Enhanced notification settings")
            print("  - 6-month report history retention")
        else:
            print(f"Failed to create production configuration at {path}")
        return success
    except Exception as e:
        logger.error("Failed to create production configuration", config_path=path, error=str(e))
        print(f"Failed to create production configuration at {path}: {e}")
        return False


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
        logger.error("Error validating configuration", config_path=config_path, error=str(e))
        print(f"Error validating configuration: {e}")
        return False


def show_config(config_path: str = "./business_audit_config.json") -> bool:
    """Display current configuration"""
    try:
        config_manager = ConfigManager(config_path)
        config_dict = config_manager.get_effective_config()

        print("Current Business Audit Configuration:")
        print(json.dumps(config_dict, indent=2))
        return True
    except Exception as e:
        logger.error("Error displaying configuration", config_path=config_path, error=str(e))
        print(f"Error displaying configuration: {e}")
        return False


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
        # This is a simplified transformation - in a real scenario, this would handle more complex migrations
        new_data = {
            'analysis': old_data.get('analysis', {}),
            'reporting': old_data.get('reporting', {}),
            'metrics': old_data.get('metrics', {}),
            'data_sources': old_data.get('data_sources', {}),
            'notifications': old_data.get('notifications', {}),
            'system_settings': old_data.get('system_settings', {})
        }

        # Save the transformed config
        new_path = Path(new_config_path)
        with open(new_path, 'w', encoding='utf-8') as f:
            if new_path.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(new_data, f, default_flow_style=False)
            else:
                json.dump(new_data, f, indent=2)

        logger.info("Configuration migrated", old_path=str(old_path), new_path=str(new_path))
        print(f"Configuration migrated from {old_config_path} to {new_config_path}")
        return True

    except Exception as e:
        logger.error("Error migrating configuration", old_path=old_config_path, new_path=new_config_path, error=str(e))
        print(f"Error migrating configuration: {e}")
        return False


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get a configured instance of ConfigManager"""
    return ConfigManager(config_path)


def main():
    """Main entry point for configuration management"""
    import argparse

    parser = argparse.ArgumentParser(description="Business Audit Generator Configuration Manager")
    parser.add_argument("action", choices=["create-default", "create-production", "validate", "show", "update", "migrate"],
                       help="Action to perform")
    parser.add_argument("--config", default="./business_audit_config.json",
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
            elif value in [period.value for period in ReportPeriod]:
                value = ReportPeriod(value)

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