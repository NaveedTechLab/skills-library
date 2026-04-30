#!/usr/bin/env python3
"""
Feature Guard Generator
Generates feature guard decorators and access control classes for premium features
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

TEMPLATE_DIR = Path(__file__).parent / "templates"

def create_feature_guard_class(feature_name: str, required_tier: str) -> str:
    """Generate a feature guard class"""
    return f'''from enum import Enum
from typing import Dict, Any, Optional
import functools
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Tier(Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class Feature(Enum):
    {feature_name.upper()} = "{feature_name.lower()}"

class FeatureGuard:
    """
    Feature guard for {feature_name} feature
    Controls access based on user tier and usage quotas
    """

    def __init__(self, db_connection):
        self.db = db_connection
        self.required_tier = Tier.{required_tier.upper()}

        # Define quota limits per tier
        self.quota_limits = {{
            Tier.FREE: 0,  # No access for free tier
            Tier.BASIC: 5,  # 5 uses per day for basic
            Tier.PREMIUM: 50,  # 50 uses per day for premium
            Tier.ENTERPRISE: 1000  # 1000 uses per day for enterprise
        }}

    def check_access(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user has access to {feature_name} feature
        """
        user_tier = self._get_user_tier(user_id)

        # Check if user has required tier
        if self._tier_has_access(user_tier):
            # Check quota if applicable
            if self.quota_limits[user_tier] > 0:
                usage_count = self._get_daily_usage(user_id)
                quota_limit = self.quota_limits[user_tier]

                if usage_count >= quota_limit:
                    return {{
                        "has_access": False,
                        "reason": "QUOTA_EXCEEDED",
                        "message": f"Daily quota exceeded. Limit: {{quota_limit}}, Used: {{usage_count}}",
                        "quota_remaining": 0
                    }}

            return {{
                "has_access": True,
                "user_tier": user_tier.value,
                "quota_remaining": self.quota_limits[user_tier] - self._get_daily_usage(user_id) if self.quota_limits[user_tier] > 0 else float('inf')
            }}
        else:
            return {{
                "has_access": False,
                "reason": "INSUFFICIENT_TIER",
                "message": f"{feature_name} requires {{self.required_tier.value}} tier or higher",
                "required_tier": self.required_tier.value,
                "user_tier": user_tier.value
            }}

    def _get_user_tier(self, user_id: str) -> Tier:
        """
        Get user's subscription tier from database
        """
        result = self.db.execute('''
    SELECT tier FROM subscriptions
    WHERE user_id = ? AND status = 'active' AND expires_at > ?
''', (user_id, datetime.utcnow())).fetchone()

        if result:
            return Tier(result[0])
        else:
            return Tier.FREE  # Default to free tier

    def _tier_has_access(self, user_tier: Tier) -> bool:
        """
        Check if tier has access to this feature
        """
        tier_values = {{
            Tier.FREE: 0,
            Tier.BASIC: 1,
            Tier.PREMIUM: 2,
            Tier.ENTERPRISE: 3
        }}

        return tier_values[user_tier] >= tier_values[self.required_tier]

    def _get_daily_usage(self, user_id: str) -> int:
        """
        Get today's usage count for this feature
        """
        today = datetime.utcnow().date()
        result = self.db.execute('''
    SELECT COALESCE(SUM(usage_count), 0) FROM feature_usage
    WHERE user_id = ? AND feature = ? AND date_recorded = ?
''', (user_id, Feature.{feature_name.upper()}.value, today)).fetchone()

        return result[0] if result else 0

    def track_usage(self, user_id: str, count: int = 1):
        """
        Track feature usage for quota management
        """
        today = datetime.utcnow().date()
        self.db.execute('''
    INSERT INTO feature_usage (user_id, feature, usage_count, date_recorded)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(user_id, feature, date_recorded)
    DO UPDATE SET usage_count = usage_count + ?
''', (user_id, Feature.{feature_name.upper()}.value, count, today, count))


def require_{feature_name}_access(func):
    """
    Decorator to enforce {feature_name} feature access control
    """
    @functools.wraps(func)
    def wrapper(self, user_id: str, *args, **kwargs):
        # Get feature guard from the service instance
        feature_guard = getattr(self, 'feature_guard', None)
        if not feature_guard:
            raise AttributeError("Service must have 'feature_guard' attribute")

        access_result = feature_guard.check_access(user_id)

        if not access_result["has_access"]:
            raise PermissionError(access_result.get("message", f"Access denied for {feature_name}"))

        # Track usage if access is granted
        if access_result.get("quota_remaining") is not None:
            feature_guard.track_usage(user_id)

        return func(self, user_id, *args, **kwargs)

    return wrapper
'''


def create_service_template(feature_name: str, service_name: str) -> str:
    """Generate a service class template"""
    return f'''from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class {service_name}:
    """
    Service class for {feature_name} feature
    Implements the core functionality with feature access control
    """

    def __init__(self, feature_guard, database_connection):
        self.feature_guard = feature_guard
        self.db = database_connection

    def require_{feature_name}_access(self, user_id: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Wrapper method to enforce access control
        """
        # This method would be decorated with @require_{feature_name}_access in real implementation
        access_result = self.feature_guard.check_access(user_id)

        if not access_result["has_access"]:
            raise PermissionError(access_result.get("message", f"Access denied for {feature_name}"))

        # Track usage if access is granted
        if access_result.get("quota_remaining") is not None:
            self.feature_guard.track_usage(user_id)

        # Call the actual implementation
        return self._{feature_name}_implementation(user_id, *args, **kwargs)

    def _{feature_name}_implementation(self, user_id: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Actual implementation of {feature_name} feature
        """
        # TODO: Implement the core functionality here
        logger.info(f"Executing {feature_name} for user {{user_id}}")

        # Example implementation
        result = {{
            "success": True,
            "feature": "{feature_name}",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {{}}  # Add feature-specific data here
        }}

        return result

    def get_feature_info(self) -> Dict[str, Any]:
        """
        Get information about this feature
        """
        return {{
            "name": "{feature_name}",
            "description": "Implementation of {feature_name} feature with access control",
            "tier_requirement": self.feature_guard.required_tier.value
        }}
'''


def create_migration_script(feature_name: str) -> str:
    """Generate database migration script"""
    return f'''-- Migration for {feature_name} feature
-- Add feature to feature_usage table if it doesn't exist

-- Ensure feature_usage table exists
CREATE TABLE IF NOT EXISTS feature_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    feature TEXT NOT NULL,
    usage_count INTEGER DEFAULT 1,
    date_recorded DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, feature, date_recorded)
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_feature_usage_user_feature_date
ON feature_usage(user_id, feature, date_recorded);

-- Add feature to allowed features list if needed
-- This would be in a features configuration table
INSERT OR IGNORE INTO features (name, description)
VALUES ('{feature_name}', '{feature_name} feature for premium users');

-- Example: Set default quota for existing premium users
-- UPDATE subscriptions SET {feature_name}_quota = 50
-- WHERE tier IN ('premium', 'enterprise');
'''


def main():
    parser = argparse.ArgumentParser(description='Generate feature guard and service templates')
    parser.add_argument('--feature-name', required=True, help='Name of the feature (e.g., adaptive-learning)')
    parser.add_argument('--service-name', required=True, help='Name of the service class (e.g., AdaptiveLearningService)')
    parser.add_argument('--tier', choices=['FREE', 'BASIC', 'PREMIUM', 'ENTERPRISE'],
                       default='PREMIUM', help='Required tier for feature access')
    parser.add_argument('--output-dir', default='./generated', help='Output directory for generated files')

    args = parser.parse_args()

    # Normalize feature name (convert hyphens to underscores)
    normalized_feature_name = args.feature_name.replace('-', '_').replace(' ', '_')

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating feature guard for: {normalized_feature_name}")
    print(f"Required tier: {args.tier}")
    print(f"Output directory: {output_dir}")

    # Generate feature guard class
    guard_code = create_feature_guard_class(normalized_feature_name, args.tier)
    guard_file = output_dir / f"{normalized_feature_name}_guard.py"
    with open(guard_file, 'w') as f:
        f.write(guard_code)
    print(f"✓ Created feature guard: {guard_file}")

    # Generate service class
    service_code = create_service_template(normalized_feature_name, args.service_name)
    service_file = output_dir / f"{normalized_feature_name}_service.py"
    with open(service_file, 'w') as f:
        f.write(service_code)
    print(f"✓ Created service class: {service_file}")

    # Generate migration script
    migration_code = create_migration_script(normalized_feature_name)
    migration_file = output_dir / f"migration_{normalized_feature_name}.sql"
    with open(migration_file, 'w') as f:
        f.write(migration_code)
    print(f"✓ Created migration script: {migration_file}")

    # Create a combined example
    example_code = f'''"""
Example usage of {normalized_feature_name} feature guard and service
"""

from {normalized_feature_name}_guard import {args.service_name}, require_{normalized_feature_name}_access
import sqlite3
from datetime import datetime

# Initialize database (for example)
db = sqlite3.connect(':memory:')  # In real app, use persistent DB
cursor = db.cursor()

# Create necessary tables
cursor.executescript("""
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id TEXT PRIMARY KEY,
    tier TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    expires_at TIMESTAMP DEFAULT (datetime('now', '+30 days'))
);

CREATE TABLE IF NOT EXISTS feature_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    feature TEXT NOT NULL,
    usage_count INTEGER DEFAULT 1,
    date_recorded DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, feature, date_recorded)
);
""")

# Create a premium user for testing
cursor.execute("INSERT OR REPLACE INTO subscriptions (user_id, tier) VALUES (?, ?)",
              ("user123", "premium"))

db.commit()

# Initialize feature guard and service
feature_guard = {args.service_name[:-7]}Guard(db)  # Remove 'Service' from class name
service = {args.service_name}(feature_guard, db)

print("=== {normalized_feature_name} Feature Example ===")
print(f"Feature info: {{service.get_feature_info()}}")

try:
    # This should work for premium user
    result = service.require_{normalized_feature_name}_access("user123")
    print(f"✓ Feature executed successfully: {{result}}")
except PermissionError as e:
    print(f"✗ Access denied: {{e}}")

# Clean up
db.close()
'''

    example_file = output_dir / f"example_{normalized_feature_name}.py"
    with open(example_file, 'w') as f:
        f.write(example_code)
    print(f"✓ Created example usage: {example_file}")

    print(f"\n🎉 Generation complete! Files created in {output_dir}/")
    print(f"Files created:")
    print(f"  - {guard_file.name}")
    print(f"  - {service_file.name}")
    print(f"  - {migration_file.name}")
    print(f"  - {example_file.name}")
    print(f"\nTo use these files:")
    print(f"  1. Review and customize the generated code")
    print(f"  2. Run the migration script on your database")
    print(f"  3. Integrate the service and guard into your application")


if __name__ == "__main__":
    main()