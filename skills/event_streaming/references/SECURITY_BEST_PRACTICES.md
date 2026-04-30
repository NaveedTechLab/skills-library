# Security Best Practices for Kafka Event Streaming

## Overview

This document outlines security best practices for securing the Kafka-based event streaming system. It covers authentication, authorization, encryption, and other security considerations for protecting data in transit and at rest.

## Authentication

### SASL Authentication

#### SASL/PLAIN Configuration
```python
from kafka import KafkaProducer, KafkaConsumer
import json

class SASLPlainConfig:
    """
    Configuration for SASL/PLAIN authentication.
    """

    def __init__(self, username: str, password: str, bootstrap_servers: str):
        self.username = username
        self.password = password
        self.bootstrap_servers = bootstrap_servers

    def create_producer(self) -> KafkaProducer:
        """
        Create a producer with SASL/PLAIN authentication.
        """
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            security_protocol='SASL_PLAINTEXT',  # or SASL_SSL for encrypted
            sasl_mechanism='PLAIN',
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=2147483647
        )

    def create_consumer(self, group_id: str) -> KafkaConsumer:
        """
        Create a consumer with SASL/PLAIN authentication.
        """
        return KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            security_protocol='SASL_PLAINTEXT',  # or SASL_SSL for encrypted
            sasl_mechanism='PLAIN',
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=False
        )
```

#### SASL/SCRAM Configuration
```python
class SASLScramConfig:
    """
    Configuration for SASL/SCRAM authentication (more secure than PLAIN).
    """

    def __init__(self, username: str, password: str, bootstrap_servers: str,
                 scram_mechanism: str = 'SCRAM-SHA-256'):
        self.username = username
        self.password = password
        self.bootstrap_servers = bootstrap_servers
        self.scram_mechanism = scram_mechanism

    def create_producer(self) -> KafkaProducer:
        """
        Create a producer with SASL/SCRAM authentication.
        """
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            security_protocol='SASL_PLAINTEXT',  # or SASL_SSL for encrypted
            sasl_mechanism=self.scram_mechanism,
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=2147483647
        )

    def create_consumer(self, group_id: str) -> KafkaConsumer:
        """
        Create a consumer with SASL/SCRAM authentication.
        """
        return KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            security_protocol='SASL_PLAINTEXT',  # or SASL_SSL for encrypted
            sasl_mechanism=self.scram_mechanism,
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=False
        )
```

#### Kerberos (GSSAPI) Configuration
```python
class KerberosConfig:
    """
    Configuration for Kerberos/GSSAPI authentication.
    """

    def __init__(self, bootstrap_servers: str, principal: str, keytab_path: str):
        self.bootstrap_servers = bootstrap_servers
        self.principal = principal
        self.keytab_path = keytab_path

    def create_producer(self) -> KafkaProducer:
        """
        Create a producer with Kerberos authentication.
        """
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            security_protocol='SASL_PLAINTEXT',  # or SASL_SSL for encrypted
            sasl_mechanism='GSSAPI',
            sasl_kerberos_service_name='kafka',
            sasl_kerberos_principal=self.principal,
            # Note: Additional Kerberos configuration needed
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=2147483647
        )
```

## Encryption

### SSL/TLS Configuration

#### SSL Client Configuration
```python
import ssl
import os

class SSLConfig:
    """
    Configuration for SSL/TLS encryption.
    """

    def __init__(self, bootstrap_servers: str,
                 cafile: str = None,
                 certfile: str = None,
                 keyfile: str = None,
                 password: str = None):
        self.bootstrap_servers = bootstrap_servers
        self.cafile = cafile
        self.certfile = certfile
        self.keyfile = keyfile
        self.password = password

    def create_ssl_context(self) -> ssl.SSLContext:
        """
        Create SSL context with proper certificate validation.
        """
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

        if self.cafile:
            context.load_verify_locations(cafile=self.cafile)
        else:
            # Load default CA certificates
            context.load_default_certs(ssl.Purpose.SERVER_AUTH)

        if self.certfile and self.keyfile:
            context.load_cert_chain(
                certfile=self.certfile,
                keyfile=self.keyfile,
                password=self.password
            )

        # Set minimum TLS version for security
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        return context

    def create_producer(self) -> KafkaProducer:
        """
        Create a producer with SSL/TLS encryption.
        """
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            security_protocol='SSL',
            ssl_cafile=self.cafile,
            ssl_certfile=self.certfile,
            ssl_keyfile=self.keyfile,
            ssl_password=self.password,
            ssl_check_hostname=True,
            ssl_context=self.create_ssl_context(),
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=2147483647
        )

    def create_consumer(self, group_id: str) -> KafkaConsumer:
        """
        Create a consumer with SSL/TLS encryption.
        """
        return KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            security_protocol='SSL',
            ssl_cafile=self.cafile,
            ssl_certfile=self.certfile,
            ssl_keyfile=self.keyfile,
            ssl_password=self.password,
            ssl_check_hostname=True,
            ssl_context=self.create_ssl_context(),
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=False
        )
```

#### Combined SASL_SSL Configuration
```python
class SecureConfig:
    """
    Configuration combining SSL/TLS with SASL authentication.
    """

    def __init__(self, bootstrap_servers: str, username: str, password: str,
                 cafile: str = None, certfile: str = None, keyfile: str = None):
        self.bootstrap_servers = bootstrap_servers
        self.username = username
        self.password = password
        self.cafile = cafile
        self.certfile = certfile
        self.keyfile = keyfile

    def create_secure_producer(self) -> KafkaProducer:
        """
        Create a producer with SSL/TLS + SASL authentication.
        """
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            security_protocol='SASL_SSL',
            sasl_mechanism='SCRAM-SHA-256',  # or 'PLAIN' for simple auth
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
            ssl_cafile=self.cafile,
            ssl_certfile=self.certfile,
            ssl_keyfile=self.keyfile,
            ssl_check_hostname=True,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=2147483647
        )

    def create_secure_consumer(self, group_id: str) -> KafkaConsumer:
        """
        Create a consumer with SSL/TLS + SASL authentication.
        """
        return KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            security_protocol='SASL_SSL',
            sasl_mechanism='SCRAM-SHA-256',
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
            ssl_cafile=self.cafile,
            ssl_certfile=self.certfile,
            ssl_keyfile=self.keyfile,
            ssl_check_hostname=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=False
        )
```

## Authorization (ACLs)

### ACL Management

#### Kafka Admin Client for ACLs
```python
from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType
from kafka.coordinator.protocol import MemberAssignment
from kafka.protocol.admin import (
    DescribeAclsRequest_v0, CreateAclsRequest_v0,
    DeleteAclsRequest_v0, AclOperation, AclPermissionType,
    ResourcePatternType, ResourceType
)
from kafka.structs import Acl, ResourcePattern

class ACLManager:
    """
    Manager for Kafka Access Control Lists (ACLs).
    """

    def __init__(self, bootstrap_servers: str, security_config=None):
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            **(security_config or {})
        )

    def create_topic_acl(self, topic_name: str, principal: str,
                        host: str = '*', operations: list = None) -> bool:
        """
        Create ACLs for a topic.

        Args:
            topic_name: Name of the topic
            principal: Principal (e.g., "User:alice")
            host: Host pattern (default '*')
            operations: List of operations (READ, WRITE, DESCRIBE, etc.)

        Returns:
            True if successful
        """
        if operations is None:
            operations = ['READ', 'WRITE']

        # Map operation names to Kafka ACL operations
        operation_map = {
            'ALL': AclOperation.ALL,
            'READ': AclOperation.READ,
            'WRITE': AclOperation.WRITE,
            'CREATE': AclOperation.CREATE,
            'DELETE': AclOperation.DELETE,
            'ALTER': AclOperation.ALTER,
            'DESCRIBE': AclOperation.DESCRIBE,
            'CLUSTER_ACTION': AclOperation.CLUSTER_ACTION,
            'DESCRIBE_CONFIGS': AclOperation.DESCRIBE_CONFIGS,
            'ALTER_CONFIGS': AclOperation.ALTER_CONFIGS,
            'IDEMPOTENT_WRITE': AclOperation.IDEMPOTENT_WRITE
        }

        try:
            acls = []
            for op_name in operations:
                acl = Acl(
                    principal=principal,
                    host=host,
                    operation=operation_map[op_name.upper()],
                    permission_type=AclPermissionType.ALLOW
                )

                resource_pattern = ResourcePattern(
                    resource_type=ResourceType.TOPIC,
                    name=topic_name,
                    pattern_type=ResourcePatternType.LITERAL
                )

                acls.append((acl, resource_pattern))

            # Create ACLs
            self.admin_client.create_acls(acls)
            print(f"Created ACLs for topic {topic_name} for principal {principal}")
            return True

        except Exception as e:
            print(f"Error creating ACLs for topic {topic_name}: {e}")
            return False

    def create_consumer_group_acl(self, group_name: str, principal: str,
                                host: str = '*', operations: list = None) -> bool:
        """
        Create ACLs for a consumer group.
        """
        if operations is None:
            operations = ['READ']

        operation_map = {
            'ALL': AclOperation.ALL,
            'READ': AclOperation.READ,
            'DESCRIBE': AclOperation.DESCRIBE,
        }

        try:
            acls = []
            for op_name in operations:
                acl = Acl(
                    principal=principal,
                    host=host,
                    operation=operation_map[op_name.upper()],
                    permission_type=AclPermissionType.ALLOW
                )

                resource_pattern = ResourcePattern(
                    resource_type=ResourceType.GROUP,
                    name=group_name,
                    pattern_type=ResourcePatternType.LITERAL
                )

                acls.append((acl, resource_pattern))

            self.admin_client.create_acls(acls)
            print(f"Created ACLs for consumer group {group_name} for principal {principal}")
            return True

        except Exception as e:
            print(f"Error creating ACLs for consumer group {group_name}: {e}")
            return False

    def list_acls(self, resource_type: str = 'TOPIC', resource_name: str = '*'):
        """
        List ACLs for a specific resource.
        """
        try:
            # This would use the admin client to describe ACLs
            # Implementation depends on the specific Kafka client library
            print(f"Listing ACLs for {resource_type}: {resource_name}")
            # Actual implementation would call describe_acls
            return []
        except Exception as e:
            print(f"Error listing ACLs: {e}")
            return []
```

## Secure Message Content

### Message Encryption

#### Client-Side Message Encryption
```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import json

class MessageEncryptor:
    """
    Encrypts message content before sending to Kafka.
    """

    def __init__(self, encryption_key: bytes = None):
        if encryption_key is None:
            # In production, get from secure key management system
            self.key = Fernet.generate_key()
        else:
            self.key = encryption_key

        self.cipher_suite = Fernet(self.key)

    def encrypt_message(self, message: dict) -> dict:
        """
        Encrypt message content while keeping metadata accessible.
        """
        # Keep non-sensitive metadata in plain text
        encrypted_payload = {
            'encrypted_content': self.cipher_suite.encrypt(
                json.dumps(message).encode('utf-8')
            ).decode('utf-8'),
            'encryption_version': '1.0',
            'timestamp': message.get('timestamp', None)  # Keep timestamp accessible for ordering
        }

        return encrypted_payload

    def decrypt_message(self, encrypted_payload: dict) -> dict:
        """
        Decrypt message content.
        """
        if encrypted_payload.get('encryption_version') != '1.0':
            raise ValueError("Unsupported encryption version")

        decrypted_bytes = self.cipher_suite.decrypt(
            encrypted_payload['encrypted_content'].encode('utf-8')
        )
        return json.loads(decrypted_bytes.decode('utf-8'))

    def encrypt_field(self, field_value: str) -> str:
        """
        Encrypt a specific field value.
        """
        encrypted = self.cipher_suite.encrypt(field_value.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt_field(self, encrypted_field: str) -> str:
        """
        Decrypt a specific field value.
        """
        encrypted_bytes = base64.b64decode(encrypted_field.encode('utf-8'))
        decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')
```

#### Secure Producer with Encryption
```python
class SecureEncryptedProducer:
    """
    Producer that encrypts message content before sending.
    """

    def __init__(self, bootstrap_servers: str, encryptor: MessageEncryptor,
                 security_config: dict = None):
        self.encryptor = encryptor

        # Create underlying producer with security
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            **(security_config or {}),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=2147483647
        )

    def send_secure_message(self, topic: str, message: dict, key: str = None) -> bool:
        """
        Send an encrypted message to Kafka.
        """
        try:
            # Encrypt the message content
            encrypted_message = self.encryptor.encrypt_message(message)

            # Send encrypted message
            future = self.producer.send(topic, value=encrypted_message, key=key)
            record_metadata = future.get(timeout=30)

            print(f"Encrypted message sent to {topic}[{record_metadata.partition}] "
                  f"at offset {record_metadata.offset}")
            return True

        except Exception as e:
            print(f"Error sending encrypted message: {e}")
            return False

    def close(self):
        """
        Close the producer.
        """
        self.producer.close()
```

## Network Security

### Firewall and Network Configuration

#### Secure Network Configuration
```python
import socket
from typing import List, Tuple

class NetworkSecurityManager:
    """
    Manages network security aspects of Kafka connections.
    """

    def __init__(self, allowed_hosts: List[str] = None, allowed_ports: List[int] = None):
        self.allowed_hosts = allowed_hosts or []
        self.allowed_ports = allowed_ports or [9092, 9093]  # Default Kafka ports

    def validate_connection_endpoint(self, host: str, port: int) -> bool:
        """
        Validate that a connection endpoint is allowed.
        """
        # Check if host is in allowed list (or if we allow all hosts)
        if self.allowed_hosts and host not in self.allowed_hosts:
            print(f"Connection to {host}:{port} is not allowed")
            return False

        # Check if port is in allowed list
        if port not in self.allowed_ports:
            print(f"Connection to {host}:{port} uses disallowed port")
            return False

        return True

    def create_secure_socket(self, host: str, port: int, timeout: int = 10) -> socket.socket:
        """
        Create a secure socket connection with validation.
        """
        if not self.validate_connection_endpoint(host, port):
            raise ValueError(f"Connection to {host}:{port} is not allowed")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        # Disable IPv4 address sharing to prevent certain attacks
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)

        return sock

    def get_trusted_bootstrap_servers(self, original_servers: List[str]) -> List[str]:
        """
        Filter bootstrap servers to only include trusted endpoints.
        """
        trusted_servers = []

        for server in original_servers:
            host, port = server.split(':')
            port = int(port)

            if self.validate_connection_endpoint(host, port):
                trusted_servers.append(server)

        return trusted_servers
```

## Security Monitoring

### Security Event Monitoring
```python
import logging
from datetime import datetime
from typing import Dict, Any

class SecurityEventLogger:
    """
    Logs security-relevant events for monitoring and auditing.
    """

    def __init__(self, logger_name: str = 'kafka_security'):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        # Create handler for security events
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_auth_event(self, event_type: str, principal: str, success: bool,
                      details: Dict[str, Any] = None):
        """
        Log authentication events.
        """
        event_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'principal': principal,
            'success': success,
            'details': details or {}
        }

        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, f"AUTH_EVENT: {event_data}")

    def log_acl_violation(self, principal: str, resource: str, operation: str,
                         details: Dict[str, Any] = None):
        """
        Log ACL violations.
        """
        event_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'ACL_VIOLATION',
            'principal': principal,
            'resource': resource,
            'operation': operation,
            'details': details or {}
        }

        self.logger.warning(f"SECURITY_VIOLATION: {event_data}")

    def log_unusual_activity(self, activity_type: str, details: Dict[str, Any]):
        """
        Log unusual security-related activity.
        """
        event_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'UNUSUAL_ACTIVITY',
            'activity_type': activity_type,
            'details': details
        }

        self.logger.info(f"UNUSUAL_ACTIVITY: {event_data}")
```

## Secret Management

### Secure Credential Handling
```python
import os
import boto3
from typing import Optional

class CredentialManager:
    """
    Manages secure credential retrieval from various sources.
    """

    def get_kafka_credentials(self) -> Dict[str, str]:
        """
        Retrieve Kafka credentials from secure storage.
        Supports multiple backends: environment variables, AWS Secrets Manager, etc.
        """
        # 1. Check environment variables first
        username = os.getenv('KAFKA_USERNAME')
        password = os.getenv('KAFKA_PASSWORD')

        if username and password:
            return {'username': username, 'password': password}

        # 2. Check AWS Secrets Manager
        secret_name = os.getenv('KAFKA_CREDENTIALS_SECRET_NAME')
        if secret_name:
            return self._get_from_aws_secrets(secret_name)

        # 3. Check HashiCorp Vault (if configured)
        vault_path = os.getenv('KAFKA_CREDENTIALS_VAULT_PATH')
        if vault_path:
            return self._get_from_vault(vault_path)

        raise ValueError("No secure credentials found for Kafka")

    def _get_from_aws_secrets(self, secret_name: str) -> Dict[str, str]:
        """
        Retrieve credentials from AWS Secrets Manager.
        """
        try:
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            )

            response = client.get_secret_value(SecretId=secret_name)
            secret = response['SecretString']

            import json
            credentials = json.loads(secret)
            return {
                'username': credentials['username'],
                'password': credentials['password']
            }

        except Exception as e:
            raise ValueError(f"Could not retrieve credentials from AWS Secrets Manager: {e}")

    def _get_from_vault(self, vault_path: str) -> Dict[str, str]:
        """
        Retrieve credentials from HashiCorp Vault.
        """
        # This would require the hvac library
        # import hvac
        # client = hvac.Client(url=os.getenv('VAULT_ADDR'))
        # client.token = os.getenv('VAULT_TOKEN')
        # secret_response = client.secrets.kv.v2.read_secret_version(path=vault_path)
        # return secret_response['data']['data']

        # Placeholder implementation
        raise NotImplementedError("Vault integration not implemented")

class SecureConnectionFactory:
    """
    Creates Kafka connections with securely retrieved credentials.
    """

    def __init__(self, credential_manager: CredentialManager):
        self.credential_manager = credential_manager

    def create_secure_producer(self, bootstrap_servers: str) -> KafkaProducer:
        """
        Create a secure producer with retrieved credentials.
        """
        credentials = self.credential_manager.get_kafka_credentials()

        return KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            security_protocol='SASL_SSL',
            sasl_mechanism='SCRAM-SHA-256',
            sasl_plain_username=credentials['username'],
            sasl_plain_password=credentials['password'],
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=2147483647
        )

    def create_secure_consumer(self, bootstrap_servers: str, group_id: str) -> KafkaConsumer:
        """
        Create a secure consumer with retrieved credentials.
        """
        credentials = self.credential_manager.get_kafka_credentials()

        return KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            security_protocol='SASL_SSL',
            sasl_mechanism='SCRAM-SHA-256',
            sasl_plain_username=credentials['username'],
            sasl_plain_password=credentials['password'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=False
        )
```

## Security Best Practices Summary

### Implementation Checklist
```python
class SecurityBestPracticesChecker:
    """
    Validates that security best practices are implemented.
    """

    def __init__(self):
        self.checks = []

    def validate_ssl_configuration(self, producer_or_consumer) -> bool:
        """
        Validate that SSL is properly configured.
        """
        config = getattr(producer_or_consumer, '_client', producer_or_consumer)._config
        has_ssl = config.get('security_protocol', '').upper().startswith('SSL')
        has_ca_verification = config.get('ssl_check_hostname', False)

        check_result = has_ssl and has_ca_verification
        self.checks.append(('SSL Configuration', check_result))

        return check_result

    def validate_sasl_configuration(self, producer_or_consumer) -> bool:
        """
        Validate that SASL authentication is configured.
        """
        config = getattr(producer_or_consumer, '_client', producer_or_consumer)._config
        has_sasl = config.get('security_protocol', '').upper().startswith('SASL')
        has_mechanism = bool(config.get('sasl_mechanism'))

        check_result = has_sasl and has_mechanism
        self.checks.append(('SASL Configuration', check_result))

        return check_result

    def validate_encryption_at_rest(self) -> bool:
        """
        Validate that encryption at rest is configured at the infrastructure level.
        """
        # This would check cloud provider configurations
        # For now, returning True as a placeholder
        check_result = True  # Should be determined by infrastructure configuration
        self.checks.append(('Encryption at Rest', check_result))

        return check_result

    def validate_network_security(self, bootstrap_servers: list) -> bool:
        """
        Validate network security configuration.
        """
        # Check that only secure endpoints are used
        secure_endpoints = all(
            server.startswith(('localhost', '127.0.0.1')) or
            ':9093' in server  # SSL port
            for server in bootstrap_servers
        )

        check_result = secure_endpoints
        self.checks.append(('Network Security', check_result))

        return check_result

    def run_security_audit(self, producer_or_consumer, bootstrap_servers: list) -> Dict[str, bool]:
        """
        Run a comprehensive security audit.
        """
        self.checks = []  # Reset checks

        results = {
            'ssl_configured': self.validate_ssl_configuration(producer_or_consumer),
            'sasl_configured': self.validate_sasl_configuration(producer_or_consumer),
            'encryption_at_rest': self.validate_encryption_at_rest(),
            'network_security': self.validate_network_security(bootstrap_servers)
        }

        # Calculate overall security score
        passed_checks = sum(results.values())
        total_checks = len(results)
        security_score = passed_checks / total_checks if total_checks > 0 else 0

        results['overall_security_score'] = security_score
        results['security_grade'] = self._get_security_grade(security_score)

        return results

    def _get_security_grade(self, score: float) -> str:
        """
        Convert security score to letter grade.
        """
        if score >= 0.9:
            return 'A'
        elif score >= 0.8:
            return 'B'
        elif score >= 0.7:
            return 'C'
        elif score >= 0.6:
            return 'D'
        else:
            return 'F'
```

This comprehensive security guide provides all the patterns and best practices needed to secure the Kafka-based event streaming system.