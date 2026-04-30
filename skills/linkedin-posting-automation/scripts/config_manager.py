#!/usr/bin/env python3
"""
Configuration Manager for LinkedIn Posting Automation

Manages configuration for the LinkedIn posting system including API settings,
approval workflows, and posting parameters.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, asdict, field
from enum import Enum

from linkedin_api_integration import PostStatus
from approval_workflow import ApprovalLevel, UserRole
from content_management import ContentCategory

import structlog

logger = structlog.get_logger()


class PostingStrategy(Enum):
    """Strategies for posting"""
    INSTANT = "instant"
    SCHEDULED = "scheduled"
    BATCH = "batch"


class ContentModerationLevel(Enum):
    """Levels of content moderation"""
    STRICT = "strict"
    MODERATE = "moderate"
    RELAXED = "relaxed"


@dataclass
class LinkedInAPIConfig:
    """Configuration for LinkedIn API access"""
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    redirect_uri: str = "https://yourdomain.com/linkedin/callback"
    scopes: list = field(default_factory=lambda: ["w_member_social", "w_organization_social", "rw_organization_admin"])
    api_version: str = "202404"
    page_ids: list = field(default_factory=list)


@dataclass
class ApprovalConfig:
    """Configuration for approval workflows"""
    enabled: bool = True
    required_approvals: int = 1
    approval_levels: list = field(default_factory=list)
    max_review_days: int = 7
    auto_reject_expired: bool = True
    notification_on_pending: bool = True


@dataclass
class PostingConfig:
    """Configuration for posting behavior"""
    auto_publish: bool = False
    scheduled_buffer_days: int = 7
    max_posts_per_day: int = 1
    optimal_posting_times: list = field(default_factory=lambda: ["08:00", "12:00", "16:00"])
    timezone: str = "UTC"
    posting_strategy: PostingStrategy = PostingStrategy.SCHEDULED
    retry_failed_posts: bool = True
    retry_attempts: int = 3


@dataclass
class ContentConfig:
    """Configuration for content management"""
    max_characters: int = 3000
    max_hashtags: int = 5
    media_support: bool = True
    supported_media_types: list = field(default_factory=lambda: ["image", "video", "document"])
    max_media_attachment: int = 1
    enable_templates: bool = True
    default_template_category: ContentCategory = ContentCategory.NEWS


@dataclass
class ModerationConfig:
    """Configuration for content moderation"""
    enabled: bool = True
    ai_content_check: bool = True
    brand_keyword_check: bool = True
    profanity_filter: bool = True
    compliance_keywords: list = field(default_factory=lambda: ["confidential", "proprietary", "secret"])
    moderation_level: ContentModerationLevel = ContentModerationLevel.MODERATE
    auto_flag_suspicious_content: bool = True


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
    notify_on_approval_needed: bool = True


@dataclass
class LinkedInPostingConfig:
    """Complete LinkedIn posting system configuration"""
    linkedin: LinkedInAPIConfig = field(default_factory=LinkedInAPIConfig)
    approval: ApprovalConfig = field(default_factory=ApprovalConfig)
    posting: PostingConfig = field(default_factory=PostingConfig)
    content: ContentConfig = field(default_factory=ContentConfig)
    moderation: ModerationConfig = field(default_factory=ModerationConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    system_settings: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.system_settings:
            self.system_settings = {
                "debug_mode": False,
                "log_level": "INFO",
                "max_content_history_days": 90,
                "backup_enabled": True,
                "audit_trail_enabled": True
            }


class ConfigManager:
    """Manages LinkedIn posting system configuration"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "./linkedin_config.json"
        self.config = self.load_config()
        self.logger = logger.bind(component="ConfigManager")

    def load_config(self) -> LinkedInPostingConfig:
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
            return LinkedInPostingConfig()

    def save_config(self, config: LinkedInPostingConfig = None, path: str = None) -> bool:
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

    def _dict_to_config(self, data: Dict[str, Any]) -> LinkedInPostingConfig:
        """Convert dictionary to LinkedInPostingConfig object"""
        linkedin_data = data.get('linkedin', {})
        approval_data = data.get('approval', {})
        posting_data = data.get('posting', {})
        content_data = data.get('content', {}).copy()  # Copy to modify
        moderation_data = data.get('moderation', {})
        notifications_data = data.get('notifications', {})
        system_settings_data = data.get('system_settings', {})

        # Handle enums
        posting_strategy_str = posting_data.get('posting_strategy', 'scheduled')
        if isinstance(posting_strategy_str, str):
            posting_strategy = PostingStrategy[posting_strategy_str.upper()]
        else:
            posting_strategy = posting_strategy_str

        moderation_level_str = moderation_data.get('moderation_level', 'moderate')
        if isinstance(moderation_level_str, str):
            moderation_level = ContentModerationLevel[moderation_level_str.upper()]
        else:
            moderation_level = moderation_level_str

        # Handle content category enum
        default_category_str = content_data.pop('default_template_category', 'news')
        if isinstance(default_category_str, str):
            default_category = ContentCategory[default_category_str.upper()]
        else:
            default_category = default_category_str

        # Create individual config objects
        linkedin_config = LinkedInAPIConfig(**linkedin_data)
        approval_config = ApprovalConfig(**approval_data)

        # Handle enum for posting config
        posting_config = PostingConfig(
            **{k: v for k, v in posting_data.items() if k != 'posting_strategy'},
            posting_strategy=posting_strategy
        )

        # Create content config with proper enum
        content_config = ContentConfig(
            **{k: v for k, v in content_data.items()},
            default_template_category=default_category
        )

        # Handle enum for moderation config
        moderation_config = ModerationConfig(
            **{k: v for k, v in moderation_data.items() if k != 'moderation_level'},
            moderation_level=moderation_level
        )

        notifications_config = NotificationConfig(**notifications_data)

        return LinkedInPostingConfig(
            linkedin=linkedin_config,
            approval=approval_config,
            posting=posting_config,
            content=content_config,
            moderation=moderation_config,
            notifications=notifications_config,
            system_settings=system_settings_data
        )

    def _config_to_dict(self, config: LinkedInPostingConfig) -> Dict[str, Any]:
        """Convert LinkedInPostingConfig object to dictionary"""
        # Convert content config with enum handling
        content_dict = asdict(config.content)
        content_dict['default_template_category'] = config.content.default_template_category.value

        return {
            'linkedin': asdict(config.linkedin),
            'approval': asdict(config.approval),
            'posting': {
                **asdict(config.posting),
                'posting_strategy': config.posting.posting_strategy.value
            },
            'content': content_dict,
            'moderation': {
                **asdict(config.moderation),
                'moderation_level': config.moderation.moderation_level.value
            },
            'notifications': asdict(config.notifications),
            'system_settings': config.system_settings
        }

    def validate_config(self) -> list:
        """Validate configuration and return list of errors"""
        errors = []

        # Validate LinkedIn API configuration
        if not self.config.linkedin.oauth_client_id:
            errors.append("oauth_client_id is required")

        if not self.config.linkedin.oauth_client_secret:
            errors.append("oauth_client_secret is required")

        if not self.config.linkedin.redirect_uri:
            errors.append("redirect_uri is required")

        # Validate approval configuration
        if self.config.approval.required_approvals < 0:
            errors.append("required_approvals must be non-negative")

        if self.config.approval.max_review_days <= 0:
            errors.append("max_review_days must be positive")

        # Validate posting configuration
        if self.config.posting.max_posts_per_day <= 0:
            errors.append("max_posts_per_day must be positive")

        if self.config.posting.scheduled_buffer_days < 0:
            errors.append("scheduled_buffer_days must be non-negative")

        # Validate content configuration
        if self.config.content.max_characters <= 0:
            errors.append("max_characters must be positive")

        if self.config.content.max_hashtags < 0:
            errors.append("max_hashtags must be non-negative")

        if self.config.content.max_media_attachment < 0:
            errors.append("max_media_attachment must be non-negative")

        # Validate moderation configuration
        if not isinstance(self.config.moderation.enabled, bool):
            errors.append("moderation.enabled must be a boolean")

        return errors

    def update_config(self, **kwargs):
        """Update configuration with provided values"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                # Check nested attributes
                for attr_name in ['linkedin', 'approval', 'posting', 'content', 'moderation', 'notifications']:
                    attr = getattr(self.config, attr_name)
                    if hasattr(attr, key):
                        setattr(attr, key, value)
                        break
                else:
                    raise AttributeError(f"No attribute '{key}' found in config")

    def get_effective_config(self) -> Dict[str, Any]:
        """Get effective configuration as dictionary"""
        return self._config_to_dict(self.config)

    def get_linkedin_config(self) -> LinkedInAPIConfig:
        """Get LinkedIn API configuration"""
        return self.config.linkedin

    def get_approval_config(self) -> ApprovalConfig:
        """Get approval configuration"""
        return self.config.approval

    def get_posting_config(self) -> PostingConfig:
        """Get posting configuration"""
        return self.config.posting

    def get_content_config(self) -> ContentConfig:
        """Get content configuration"""
        return self.config.content

    def get_moderation_config(self) -> ModerationConfig:
        """Get moderation configuration"""
        return self.config.moderation

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
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.config_path}.backup.{timestamp}"

        return self.save_config(self.config, backup_path)


def create_default_config(path: str = "./linkedin_config.json") -> bool:
    """Create a default configuration file"""
    config_manager = ConfigManager()
    default_config = LinkedInPostingConfig()

    # Create directory if it doesn't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    success = config_manager.save_config(default_config, path)
    if success:
        logger.info("Default configuration created", config_path=path)
        print(f"Created default configuration at {path}")
        print("Configuration includes:")
        print("  - OAuth settings with default scopes")
        print("  - Approval workflow enabled")
        print("  - Scheduled posting strategy")
        print("  - Content moderation enabled")
        print("  - Default content limits")
    else:
        print(f"Failed to create configuration at {path}")

    return success


def create_production_config(path: str = "./production_linkedin_config.json") -> bool:
    """Create a production-ready configuration file"""
    config = LinkedInPostingConfig(
        linkedin=LinkedInAPIConfig(
            oauth_client_id=os.getenv("LINKEDIN_CLIENT_ID", ""),
            oauth_client_secret=os.getenv("LINKEDIN_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("LINKEDIN_REDIRECT_URI", "https://yourdomain.com/linkedin/callback"),
            scopes=["w_member_social", "w_organization_social", "rw_organization_admin"],
            api_version="202404",
            page_ids=os.getenv("LINKEDIN_PAGE_IDS", "").split(",") if os.getenv("LINKEDIN_PAGE_IDS") else []
        ),
        approval=ApprovalConfig(
            enabled=True,
            required_approvals=2,
            approval_levels=[
                {"name": "editorial", "role": "content_editor", "required": True},
                {"name": "compliance", "role": "compliance_officer", "required": True}
            ],
            max_review_days=5,
            auto_reject_expired=True,
            notification_on_pending=True
        ),
        posting=PostingConfig(
            auto_publish=False,
            scheduled_buffer_days=14,
            max_posts_per_day=2,
            optimal_posting_times=["08:00", "12:00", "16:00", "19:00"],
            timezone="US/Eastern",
            posting_strategy=PostingStrategy.SCHEDULED,
            retry_failed_posts=True,
            retry_attempts=5
        ),
        content=ContentConfig(
            max_characters=2500,
            max_hashtags=3,
            media_support=True,
            supported_media_types=["image", "video"],
            max_media_attachment=1,
            enable_templates=True,
            default_template_category=ContentCategory.INSIGHTS
        ),
        moderation=ModerationConfig(
            enabled=True,
            ai_content_check=True,
            brand_keyword_check=True,
            profanity_filter=True,
            compliance_keywords=["confidential", "proprietary", "secret", "internal"],
            moderation_level=ContentModerationLevel.STRICT,
            auto_flag_suspicious_content=True
        ),
        notifications=NotificationConfig(
            email_enabled=True,
            slack_enabled=True,
            webhook_enabled=True,
            notification_recipients=["admin@company.com", "marketing@company.com"],
            notify_on_failure=True,
            notify_on_success=False,
            notify_on_approval_needed=True
        ),
        system_settings={
            "debug_mode": False,
            "log_level": "INFO",
            "max_content_history_days": 180,
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
            print("  - Enhanced approval workflow (2 levels)")
            print("  - Stricter content moderation")
            print("  - More posting times available")
            print("  - 6-month content history retention")
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


def show_config(config_path: str = "./linkedin_config.json") -> bool:
    """Display current configuration"""
    try:
        config_manager = ConfigManager(config_path)
        config_dict = config_manager.get_effective_config()

        print("Current LinkedIn Posting Configuration:")
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
            'linkedin': old_data.get('linkedin', {}),
            'approval': old_data.get('approval', {}),
            'posting': old_data.get('posting', {}),
            'content': old_data.get('content', {}),
            'moderation': old_data.get('moderation', {}),
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
        logger.error("Error migrating configuration", old_path=old_path, new_path=new_path, error=str(e))
        print(f"Error migrating configuration: {e}")
        return False


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get a configured instance of ConfigManager"""
    return ConfigManager(config_path)


def main():
    """Main entry point for configuration management"""
    import argparse

    parser = argparse.ArgumentParser(description="LinkedIn Posting Automation Configuration Manager")
    parser.add_argument("action", choices=["create-default", "create-production", "validate", "show", "update", "migrate"],
                       help="Action to perform")
    parser.add_argument("--config", default="./linkedin_config.json",
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
            elif value in [strategy.value for strategy in PostingStrategy]:
                value = PostingStrategy[value.upper()]
            elif value in [level.value for level in ContentModerationLevel]:
                value = ContentModerationLevel[value.upper()]

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