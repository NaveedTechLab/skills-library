#!/usr/bin/env python3
"""
Configuration Helper for Email MCP Server

Helper script for setting up and managing email MCP server configuration.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

def create_default_config(config_path: str = "email_config.json"):
    """Create a default configuration file"""
    default_config = {
        "credentials_path": "credentials.json",
        "token_path": "token.pickle",
        "server": {
            "host": "localhost",
            "port": 8080
        },
        "hitl": {
            "enabled": True,
            "approval_timeout": 3600,
            "approval_required": {
                "external_recipients": True,
                "attachment_size_mb": 10,
                "sensitive_keywords": ["confidential", "private", "urgent", "sensitive", "classified"]
            }
        },
        "email_settings": {
            "default_signature": "--\nSent via Claude Email MCP Server",
            "max_attachment_size_mb": 25,
            "rate_limit": {
                "requests_per_minute": 10,
                "burst_size": 5
            }
        }
    }

    config_file = Path(config_path)
    if config_file.exists():
        print(f"Configuration file {config_path} already exists!")
        response = input("Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2)

    print(f"Created default configuration at {config_path}")
    print("Remember to update the credentials_path with your Google credentials file!")


def validate_config(config_path: str = "email_config.json") -> bool:
    """Validate the configuration file"""
    if not os.path.exists(config_path):
        print(f"Configuration file {config_path} does not exist!")
        return False

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in configuration file: {e}")
        return False
    except Exception as e:
        print(f"Error reading configuration file: {e}")
        return False

    # Validate required fields
    required_fields = ['credentials_path', 'token_path', 'server']
    missing_fields = []
    for field in required_fields:
        if field not in config:
            missing_fields.append(field)

    if missing_fields:
        print(f"Missing required fields: {missing_fields}")
        return False

    # Validate server configuration
    server_config = config.get('server', {})
    if not isinstance(server_config, dict):
        print("server configuration must be an object")
        return False

    if 'host' not in server_config or 'port' not in server_config:
        print("server configuration must include 'host' and 'port'")
        return False

    # Validate credentials file exists
    credentials_path = config.get('credentials_path', 'credentials.json')
    if not os.path.exists(credentials_path):
        print(f"Credentials file {credentials_path} does not exist!")
        print("You need to set up Google API credentials first.")
        return False

    print("Configuration is valid!")
    return True


def setup_google_credentials():
    """Guide user through Google credentials setup"""
    print("Setting up Google API credentials for Gmail...")
    print("\nSteps to create Google credentials:")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create a new project or select an existing one")
    print("3. Enable the Gmail API")
    print("4. Go to 'Credentials' in the sidebar")
    print("5. Click 'Create Credentials' -> 'OAuth 2.0 Client IDs'")
    print("6. Select 'Desktop Application' as the application type")
    print("7. Download the credentials JSON file")
    print("8. Rename it to 'credentials.json' and place it in this directory")
    print("\nFor more details, visit: https://developers.google.com/gmail/api/quickstart/python")


def show_config(config_path: str = "email_config.json"):
    """Display current configuration (with sensitive data masked)"""
    if not os.path.exists(config_path):
        print(f"Configuration file {config_path} does not exist!")
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in configuration file: {e}")
        return

    # Mask sensitive fields
    safe_config = config.copy()
    if 'credentials_path' in safe_config:
        safe_config['credentials_path'] = safe_config['credentials_path']

    print("Current configuration:")
    print(json.dumps(safe_config, indent=2))


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Email MCP Server Configuration Helper")
    parser.add_argument("action", choices=["create-config", "validate", "setup-credentials", "show-config"],
                       help="Action to perform")
    parser.add_argument("--config", default="email_config.json",
                       help="Path to configuration file")

    args = parser.parse_args()

    if args.action == "create-config":
        create_default_config(args.config)
    elif args.action == "validate":
        validate_config(args.config)
    elif args.action == "setup-credentials":
        setup_google_credentials()
    elif args.action == "show-config":
        show_config(args.config)


if __name__ == "__main__":
    main()