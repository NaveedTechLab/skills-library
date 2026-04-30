#!/usr/bin/env python3
"""
Alert Manager for Watchdog Process Manager

Handles notifications and alerts for process failures, health violations, and system events.
"""

import asyncio
import json
import logging
import smtplib
import socket
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import requests
import yaml

logger = logging.getLogger(__name__)


class AlertChannel:
    """Base class for alert channels"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config

    async def send_alert(self, alert_type: str, message: str, **kwargs) -> bool:
        """Send an alert message. Must be implemented by subclasses."""
        raise NotImplementedError


class EmailAlertChannel(AlertChannel):
    """Email alert channel"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.smtp_server = config['smtp_server']
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config['username']
        self.password = config['password']
        self.from_email = config['from_email']
        self.to_emails = config['to_emails']  # List of recipient emails

    async def send_alert(self, alert_type: str, message: str, **kwargs) -> bool:
        """Send an email alert"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['Subject'] = f"Process Alert: {alert_type}"
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)

            # Create message body
            body = f"""
Process Alert

Type: {alert_type}
Message: {message}
Timestamp: {datetime.now().isoformat()}
Details: {json.dumps(kwargs, indent=2, default=str)}

This is an automated message from the Watchdog Process Manager.
            """.strip()
            msg.attach(MIMEText(body, 'plain'))

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Email alert sent via {self.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert via {self.name}: {e}")
            return False


class SlackAlertChannel(AlertChannel):
    """Slack alert channel"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.webhook_url = config['webhook_url']
        self.channel = config.get('channel', '#alerts')
        self.username = config.get('username', 'WatchdogBot')

    async def send_alert(self, alert_type: str, message: str, **kwargs) -> bool:
        """Send a Slack alert"""
        try:
            # Format Slack message
            slack_message = {
                "channel": self.channel,
                "username": self.username,
                "text": f"🚨 *Process Alert*: {alert_type}",
                "attachments": [
                    {
                        "color": "danger" if "failure" in alert_type.lower() or "error" in alert_type.lower() else "warning",
                        "fields": [
                            {
                                "title": "Message",
                                "value": message,
                                "short": False
                            },
                            {
                                "title": "Timestamp",
                                "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True
                            }
                        ]
                    }
                ]
            }

            # Add additional details if provided
            if kwargs:
                details_attachment = {
                    "color": "warning",
                    "title": "Additional Details",
                    "text": json.dumps(kwargs, indent=2, default=str),
                    "mrkdwn_in": ["text"]
                }
                slack_message["attachments"].append(details_attachment)

            # Send to Slack webhook
            response = requests.post(
                self.webhook_url,
                json=slack_message,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                logger.info(f"Slack alert sent via {self.name}")
                return True
            else:
                logger.error(f"Failed to send Slack alert: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Slack alert via {self.name}: {e}")
            return False


class WebhookAlertChannel(AlertChannel):
    """Generic webhook alert channel"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.url = config['url']
        self.method = config.get('method', 'POST').upper()
        self.headers = config.get('headers', {})
        self.auth = config.get('auth')  # Tuple of (username, password) for basic auth

    async def send_alert(self, alert_type: str, message: str, **kwargs) -> bool:
        """Send an alert via webhook"""
        try:
            payload = {
                'type': alert_type,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'details': kwargs
            }

            response = requests.request(
                method=self.method,
                url=self.url,
                json=payload,
                headers=self.headers,
                auth=self.auth
            )

            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook alert sent via {self.name}")
                return True
            else:
                logger.error(f"Failed to send webhook alert: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send webhook alert via {self.name}: {e}")
            return False


class LogAlertChannel(AlertChannel):
    """Log-based alert channel"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.log_level = config.get('log_level', 'WARNING').upper()
        self.logger_name = config.get('logger_name', 'alert_logger')

    async def send_alert(self, alert_type: str, message: str, **kwargs) -> bool:
        """Send an alert to logs"""
        try:
            # Get or create logger
            alert_logger = logging.getLogger(self.logger_name)

            # Map log level
            log_method = getattr(alert_logger, self.log_level.lower(), alert_logger.warning)

            # Log the alert
            log_message = f"ALERT [{alert_type}]: {message}"
            if kwargs:
                log_message += f" | Details: {json.dumps(kwargs, default=str)}"

            log_method(log_message)

            logger.info(f"Log alert recorded via {self.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send log alert via {self.name}: {e}")
            return False


class AlertManager:
    """Manages alerting and notifications"""

    def __init__(self, config_path: Optional[str] = None):
        self.channels: Dict[str, AlertChannel] = {}
        self.rules: List[Dict[str, Any]] = []
        self.config = self._load_config(config_path)

        # Initialize configured channels
        for channel_config in self.config.get('channels', []):
            self.add_channel_from_config(channel_config)

        # Load alert rules
        self.rules = self.config.get('rules', [])

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load alert manager configuration"""
        default_config = {
            "channels": [],
            "rules": [
                {
                    "name": "critical_failures",
                    "conditions": {
                        "alert_types": ["process_failure", "restart_limit_exceeded"],
                        "severity": "critical"
                    },
                    "actions": ["email", "slack"]
                },
                {
                    "name": "resource_violations",
                    "conditions": {
                        "alert_types": ["resource_violation"],
                        "severity": "warning"
                    },
                    "actions": ["log", "webhook"]
                }
            ],
            "default_channels": ["log"]
        }

        if config_path and Path(config_path).exists():
            path = Path(config_path)
            with open(path, 'r') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    file_config = yaml.safe_load(f)
                else:
                    file_config = json.load(f)
            default_config.update(file_config)

        return default_config

    def add_channel(self, channel: AlertChannel):
        """Add an alert channel"""
        self.channels[channel.name] = channel
        logger.info(f"Added alert channel: {channel.name}")

    def add_channel_from_config(self, config: Dict[str, Any]):
        """Add an alert channel from configuration"""
        channel_type = config['type']
        name = config['name']

        if channel_type == 'email':
            channel = EmailAlertChannel(name, config)
        elif channel_type == 'slack':
            channel = SlackAlertChannel(name, config)
        elif channel_type == 'webhook':
            channel = WebhookAlertChannel(name, config)
        elif channel_type == 'log':
            channel = LogAlertChannel(name, config)
        else:
            raise ValueError(f"Unknown channel type: {channel_type}")

        self.add_channel(channel)

    def send_alert(self, alert_type: str, message: str, severity: str = "warning", **kwargs) -> List[bool]:
        """Send an alert to all matching channels"""
        # Determine which channels to use based on rules
        channels_to_notify = self._get_channels_for_alert(alert_type, severity)

        # Send alert to each channel
        results = []
        for channel_name in channels_to_notify:
            if channel_name in self.channels:
                result = asyncio.run(self.channels[channel_name].send_alert(alert_type, message, **kwargs))
                results.append(result)
            else:
                logger.warning(f"Channel {channel_name} not found")
                results.append(False)

        return results

    def _get_channels_for_alert(self, alert_type: str, severity: str) -> List[str]:
        """Get channels that should be notified for this alert"""
        # Check rules to determine channels
        for rule in self.rules:
            conditions = rule.get('conditions', {})
            rule_types = conditions.get('alert_types', [])
            rule_severity = conditions.get('severity')

            if alert_type in rule_types and (not rule_severity or rule_severity == severity):
                return rule.get('actions', self.config.get('default_channels', ['log']))

        # If no rule matches, use default channels
        return self.config.get('default_channels', ['log'])

    def alert_process_failure(self, process_name: str, exit_code: Optional[int] = None):
        """Send alert when process fails"""
        message = f"Process {process_name} failed"
        if exit_code is not None:
            message += f" with exit code {exit_code}"

        logger.error(message)
        return self.send_alert("process_failure", message, severity="critical", process_name=process_name, exit_code=exit_code)

    def alert_restart_limit_exceeded(self, process_name: str):
        """Send alert when restart limit is exceeded"""
        message = f"Restart limit exceeded for process {process_name}"
        logger.error(message)
        return self.send_alert("restart_limit_exceeded", message, severity="critical", process_name=process_name)

    def alert_resource_violation(self, process_name: str, resource: str, value: Any, limit: Any):
        """Send alert when resource limit is violated"""
        message = f"Resource violation for {process_name}: {resource}={value}, limit={limit}"
        logger.warning(message)
        return self.send_alert("resource_violation", message, severity="warning", process_name=process_name, resource=resource, value=value, limit=limit)

    def alert_system_health_violation(self, metric: str, value: Any, limit: Any):
        """Send alert when system health metric violates threshold"""
        message = f"System health violation: {metric}={value}, limit={limit}"
        logger.warning(message)
        return self.send_alert("system_health_violation", message, severity="warning", metric=metric, value=value, limit=limit)

    def alert_custom(self, alert_type: str, message: str, severity: str = "info", **kwargs):
        """Send a custom alert"""
        logger.log(getattr(logging, severity.upper(), logging.INFO), message)
        return self.send_alert(alert_type, message, severity, **kwargs)


def main():
    """Main entry point for alert manager"""
    import argparse

    parser = argparse.ArgumentParser(description="Alert Manager for Watchdog Process Manager")
    parser.add_argument("action", choices=["send-test", "configure", "status"],
                       help="Action to perform")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--type", help="Alert type for test")
    parser.add_argument("--message", help="Alert message for test")
    parser.add_argument("--severity", default="warning", help="Alert severity")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    alert_manager = AlertManager(args.config)

    if args.action == "send-test":
        if not args.type or not args.message:
            print("Error: --type and --message required for send-test action")
            return

        results = alert_manager.alert_custom(args.type, args.message, args.severity)
        print(f"Alert sent. Results: {results}")

    elif args.action == "configure":
        print("Current configuration:")
        print(json.dumps(alert_manager.config, indent=2))

    elif args.action == "status":
        print(f"Active alert channels: {list(alert_manager.channels.keys())}")
        print(f"Loaded rules: {len(alert_manager.rules)}")


if __name__ == "__main__":
    main()