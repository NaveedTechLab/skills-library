#!/usr/bin/env python3
"""
Configuration Manager for Orchestrator Engine

Handles loading, validating, and managing orchestrator configurations.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

# Default configuration structure
DEFAULT_CONFIG = {
    "routing_rules": [
        {
            "pattern": "**/*.py",
            "watcher": "python-analyzer",
            "priority": 10
        },
        {
            "pattern": "**/*.js",
            "watcher": "javascript-analyzer",
            "priority": 10
        },
        {
            "pattern": "**/*.md",
            "watcher": "markdown-processor",
            "priority": 10
        },
        {
            "pattern": "**/CLAUDE.md",
            "watcher": "specification-processor",
            "priority": 20
        }
    ],
    "concurrency_limits": {
        "max_processes": 5,
        "max_concurrent_files": 10
    },
    "output_settings": {
        "default_output_dir": "./processed",
        "preserve_original": True,
        "log_level": "INFO"
    },
    "watcher_endpoints": {
        "python-analyzer": "http://localhost:8001",
        "javascript-analyzer": "http://localhost:8002",
        "markdown-processor": "http://localhost:8003",
        "specification-processor": "http://localhost:8004"
    }
}


class ConfigManager:
    """Manages orchestrator configuration"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        if self.config_path and os.path.exists(self.config_path):
            path = Path(self.config_path)
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        else:
            return DEFAULT_CONFIG.copy()

    def save_config(self, config: Dict[str, Any], path: str = None) -> bool:
        """Save configuration to file"""
        save_path = Path(path if path else self.config_path or './orchestrator_config.json')

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config, f, default_flow_style=False)
                else:
                    json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        # Validate routing rules
        routing_rules = self.config.get('routing_rules', [])
        for i, rule in enumerate(routing_rules):
            if not isinstance(rule, dict):
                errors.append(f"Routing rule {i} is not a dictionary")
                continue

            if 'pattern' not in rule or 'watcher' not in rule:
                errors.append(f"Routing rule {i} missing required fields (pattern, watcher)")

            if not isinstance(rule.get('priority', 1), int):
                errors.append(f"Routing rule {i} has invalid priority (must be integer)")

        # Validate concurrency limits
        concurrency = self.config.get('concurrency_limits', {})
        max_proc = concurrency.get('max_processes', 5)
        max_files = concurrency.get('max_concurrent_files', 10)

        if not isinstance(max_proc, int) or max_proc <= 0:
            errors.append("max_processes must be a positive integer")

        if not isinstance(max_files, int) or max_files <= 0:
            errors.append("max_concurrent_files must be a positive integer")

        return errors

    def get_routing_rules(self) -> List[Dict[str, Any]]:
        """Get routing rules from config"""
        return self.config.get('routing_rules', [])

    def get_concurrency_limit(self) -> int:
        """Get maximum number of concurrent processes"""
        return self.config.get('concurrency_limits', {}).get('max_processes', 5)

    def get_watcher_endpoint(self, watcher_name: str) -> Optional[str]:
        """Get endpoint URL for a specific watcher"""
        endpoints = self.config.get('watcher_endpoints', {})
        return endpoints.get(watcher_name)

    def update_watcher_endpoint(self, watcher_name: str, endpoint: str):
        """Update endpoint for a specific watcher"""
        if 'watcher_endpoints' not in self.config:
            self.config['watcher_endpoints'] = {}
        self.config['watcher_endpoints'][watcher_name] = endpoint


def create_default_config(path: str = './orchestrator_config.json'):
    """Create a default configuration file"""
    config_manager = ConfigManager()
    config_manager.save_config(DEFAULT_CONFIG, path)
    print(f"Created default configuration at {path}")


def main():
    """Command line interface for configuration management"""
    import argparse

    parser = argparse.ArgumentParser(description="Orchestrator Configuration Manager")
    parser.add_argument("action", choices=["validate", "create-default", "show"],
                       help="Action to perform")
    parser.add_argument("--config", help="Path to configuration file")

    args = parser.parse_args()

    if args.action == "create-default":
        create_default_config(args.config)
    elif args.action == "validate":
        config_manager = ConfigManager(args.config)
        errors = config_manager.validate_config()
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            exit(1)
        else:
            print("Configuration is valid!")
    elif args.action == "show":
        config_manager = ConfigManager(args.config)
        print(json.dumps(config_manager.config, indent=2))


if __name__ == "__main__":
    main()