#!/usr/bin/env python3
"""
Deployment script for Fly.io applications
Handles configuration, deployment, and post-deployment tasks
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import toml

def check_fly_installed():
    """Check if flyctl is installed"""
    try:
        result = subprocess.run(['fly', 'version'],
                              capture_output=True, text=True, check=True)
        print(f"✅ Flyctl is installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Flyctl is not installed. Please install it first:")
        print("  curl -L https://fly.io/install.sh | sh")
        return False

def create_fly_toml(app_name, region="ams", cpu_kind="shared", cpus=1, memory_mb=1024):
    """Create a basic fly.toml configuration"""

    fly_config = {
        'app': app_name,
        'primary_region': region,
        'build': {
            'builder': 'paketobuildpacks/builder:base',
            'buildpacks': ['gcr.io/paketo-buildpacks/python']
        },
        'http_service': {
            'internal_port': 8000,
            'force_https': True,
            'auto_stop_machines': True,
            'auto_start_machines': True,
            'min_machines_running': 0,
            'processes': ['app']
        },
        'vm': {
            'cpu_kind': cpu_kind,
            'cpus': cpus,
            'memory_mb': memory_mb
        },
        'env': {
            'PORT': '8000'
        }
    }

    # Add static files mount if static directory exists
    if Path('static').exists():
        fly_config['statics'] = [{
            'guest_path': '/app/static',
            'url_prefix': '/static/'
        }]

    # Write to fly.toml
    with open('fly.toml', 'w') as f:
        toml.dump(fly_config, f)

    print(f"✅ Created fly.toml for app: {app_name}")
    return True

def deploy_application():
    """Deploy the application to Fly.io"""
    try:
        print("🚀 Starting deployment to Fly.io...")

        # Check if logged in
        result = subprocess.run(['fly', 'auth', 'whoami'],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Not logged in to Fly.io. Please run: fly auth login")
            return False

        # Deploy the application
        result = subprocess.run(['fly', 'deploy'],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Application deployed successfully!")
            print(result.stdout)

            # Get the application URL
            status_result = subprocess.run(['fly', 'status'],
                                         capture_output=True, text=True)
            if status_result.returncode == 0:
                for line in status_result.stdout.split('\n'):
                    if 'Hostname' in line or 'URL' in line:
                        print(f"🌐 Application URL: {line.strip()}")

            return True
        else:
            print("❌ Deployment failed:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ Deployment error: {e}")
        return False

def set_secrets(secrets_dict):
    """Set environment variables as secrets in Fly.io"""
    try:
        if not secrets_dict:
            return True

        secrets_list = []
        for key, value in secrets_dict.items():
            secrets_list.append(f"{key}={value}")

        if secrets_list:
            cmd = ['fly', 'secrets', 'set'] + secrets_list
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Secrets set successfully")
                return True
            else:
                print(f"❌ Failed to set secrets: {result.stderr}")
                return False

    except Exception as e:
        print(f"❌ Error setting secrets: {e}")
        return False

def create_postgres_cluster(name, region="ams"):
    """Create a PostgreSQL cluster for the application"""
    try:
        print(f"🔧 Creating PostgreSQL cluster: {name}")

        cmd = ['fly', 'postgres', 'create', '--name', name, '--region', region]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ PostgreSQL cluster created successfully")
            return True
        else:
            print(f"❌ Failed to create PostgreSQL cluster: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error creating PostgreSQL cluster: {e}")
        return False

def attach_postgres_to_app(postgres_app, app_name):
    """Attach PostgreSQL cluster to application"""
    try:
        print(f"🔗 Attaching {postgres_app} to {app_name}")

        cmd = ['fly', 'postgres', 'attach', '--postgres-app', postgres_app, '--app', app_name]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ PostgreSQL attached successfully")
            print("DATABASE_URL is now available as an environment variable")
            return True
        else:
            print(f"❌ Failed to attach PostgreSQL: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error attaching PostgreSQL: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python deploy_to_fly.py <app-name> [options]")
        print("Options:")
        print("  --create-postgres <name>  Create and attach PostgreSQL cluster")
        print("  --set-secret KEY=value    Set environment secrets")
        print("  --region REGION          Set deployment region (default: ams)")
        return

    app_name = sys.argv[1]
    create_postgres = None
    secrets = {}
    region = "ams"

    # Parse additional arguments
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--create-postgres" and i + 1 < len(sys.argv):
            create_postgres = sys.argv[i + 1]
            i += 2
        elif arg.startswith("--set-secret") and i + 1 < len(sys.argv):
            secret_pair = sys.argv[i + 1]
            if '=' in secret_pair:
                key, value = secret_pair.split('=', 1)
                secrets[key] = value
            i += 2
        elif arg == "--region" and i + 1 < len(sys.argv):
            region = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    print(f"🚀 Deploying {app_name} to Fly.io...")

    # Check prerequisites
    if not check_fly_installed():
        return

    # Create fly.toml configuration
    if not create_fly_toml(app_name, region=region):
        return

    # Create PostgreSQL if requested
    if create_postgres:
        if not create_postgres_cluster(create_postgres, region=region):
            print("❌ Continuing without database...")
        else:
            # Attach database to app after deployment
            print("⏳ Deploying first without database, then attaching...")

    # Set secrets if provided
    if secrets:
        print("🔐 Setting secrets...")
        if not set_secrets(secrets):
            print("❌ Continuing without setting secrets...")

    # Deploy the application
    if deploy_application():
        print(f"\n🎉 {app_name} successfully deployed to Fly.io!")

        # Attach database if requested
        if create_postgres:
            print("\n🔗 Attaching PostgreSQL database...")
            if attach_postgres_to_app(create_postgres, app_name):
                print("✅ Database attached successfully!")
                print("🔄 Redeploying to apply database configuration...")
                subprocess.run(['fly', 'deploy'], capture_output=True, text=True)
    else:
        print("\n💥 Deployment failed!")

if __name__ == "__main__":
    main()