#!/usr/bin/env python3
"""
Deployment script for Railway applications
Handles configuration, deployment, and environment setup
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_railway_installed():
    """Check if Railway CLI is installed"""
    try:
        result = subprocess.run(['railway', 'version'],
                              capture_output=True, text=True, check=True)
        print(f"✅ Railway CLI is installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Railway CLI is not installed. Please install it first:")
        print("  npm install -g @railway/cli")
        return False

def check_logged_in():
    """Check if user is logged in to Railway"""
    try:
        result = subprocess.run(['railway', 'whoami'],
                              capture_output=True, text=True, check=False)

        if result.returncode == 0:
            print(f"✅ Logged in to Railway as: {result.stdout.strip()}")
            return True
        else:
            print("❌ Not logged in to Railway. Please run: railway login")
            return False
    except Exception:
        print("❌ Not logged in to Railway. Please run: railway login")
        return False

def initialize_project(project_name=None):
    """Initialize a new Railway project"""
    try:
        if project_name:
            # Create project with specific name
            cmd = ['railway', 'init', project_name]
        else:
            # Interactive initialization
            cmd = ['railway', 'init']

        print("🔧 Initializing Railway project...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Project initialized successfully")
            return True
        else:
            print(f"❌ Initialization failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error initializing project: {e}")
        return False

def link_project(project_id):
    """Link to an existing Railway project"""
    try:
        cmd = ['railway', 'link', project_id]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ Linked to project: {project_id}")
            return True
        else:
            print(f"❌ Failed to link project: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error linking project: {e}")
        return False

def set_environment_variables(variables_dict):
    """Set environment variables in Railway"""
    try:
        if not variables_dict:
            return True

        print("🔐 Setting environment variables...")

        for key, value in variables_dict.items():
            cmd = ['railway', 'variables', 'set', f"{key}={value}"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ Failed to set {key}: {result.stderr}")
                return False

        print("✅ Environment variables set successfully")
        return True

    except Exception as e:
        print(f"❌ Error setting environment variables: {e}")
        return False

def deploy_application():
    """Deploy the application to Railway"""
    try:
        print("🚀 Starting deployment to Railway...")

        # Deploy the application
        cmd = ['railway', 'up']
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Application deployed successfully!")
            print(result.stdout)

            # Try to get the deployment URL
            status_result = subprocess.run(['railway', 'status'],
                                        capture_output=True, text=True)
            if status_result.returncode == 0:
                print("📋 Deployment status:")
                print(status_result.stdout)

            return True
        else:
            print("❌ Deployment failed:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ Deployment error: {e}")
        return False

def create_service_config(service_name="web", framework="python", port=8000):
    """Create a basic service configuration"""

    # Determine build command based on framework
    build_commands = {
        'python': 'pip install -r requirements.txt',
        'django': 'pip install -r requirements.txt && python manage.py collectstatic --noinput',
        'fastapi': 'pip install -r requirements.txt'
    }

    start_commands = {
        'python': f'python app.py',
        'django': f'python manage.py runserver 0.0.0.0:{port}',
        'fastapi': f'uvicorn app.main:app --host 0.0.0.0 --port {port}'
    }

    build_cmd = build_commands.get(framework, 'pip install -r requirements.txt')
    start_cmd = start_commands.get(framework, f'python -m http.server {port}')

    # Create railway.toml configuration
    config_content = f"""# Railway Configuration
[build]
builder = "nixpacks"

[build.args]
PYTHON_VERSION = "3.11"

[deploy]
numReplicas = 1
region = "us-west-1"
ephemeralDisk = 512
restartPolicyType = "Always"
restartPolicyMaxRetries = 3

[http]
proxyHeaders = true
minTLSServerVersion = "1.0"
minTLSClientVersion = "1.0"

[build.env]
BUILD_CMD = "{build_cmd}"

[deploy.env]
START_CMD = "{start_cmd}"
PORT = "{port}"
"""

    with open('railway.toml', 'w') as f:
        f.write(config_content)

    print(f"✅ Created railway.toml configuration for {service_name}")
    print(f"   Framework: {framework}")
    print(f"   Port: {port}")
    return True

def setup_database_connection(db_type="postgresql"):
    """Setup database connection environment variables"""

    db_configs = {
        'postgresql': {
            'env_vars': {
                'DATABASE_URL': '${{DATABASE_URL}}'  # Will be provided by Railway
            }
        },
        'neon': {
            'env_vars': {
                'NEON_DATABASE_URL': '${{NEON_DATABASE_URL}}',
                'DATABASE_URL': '${{NEON_DATABASE_URL}}'
            }
        },
        'supabase': {
            'env_vars': {
                'SUPABASE_URL': '${{SUPABASE_URL}}',
                'SUPABASE_ANON_KEY': '${{SUPABASE_ANON_KEY}}'
            }
        }
    }

    if db_type in db_configs:
        print(f"🔧 Setting up {db_type} database configuration...")
        return db_configs[db_type]['env_vars']
    else:
        print(f"⚠️  Unknown database type: {db_type}")
        return {}

def main():
    if len(sys.argv) < 2:
        print("Usage: python deploy_to_railway.py <action> [options]")
        print("")
        print("Actions:")
        print("  init <project-name>          Initialize new Railway project")
        print("  deploy                      Deploy current project")
        print("  link <project-id>           Link to existing project")
        print("  setup <framework>           Setup configuration for framework")
        print("")
        print("Options:")
        print("  --db-type TYPE              Database type (postgresql, neon, supabase)")
        print("  --port PORT                 Application port (default: 8000)")
        print("  --set-env KEY=value         Set environment variable")
        print("  --framework FRAMEWORK       Framework type (python, django, fastapi)")
        return

    action = sys.argv[1]

    # Parse additional arguments
    db_type = None
    port = 8000
    framework = "python"
    env_vars = {}
    project_arg = None

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--db-type" and i + 1 < len(sys.argv):
            db_type = sys.argv[i + 1]
            i += 2
        elif arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
            i += 2
        elif arg == "--framework" and i + 1 < len(sys.argv):
            framework = sys.argv[i + 1]
            i += 2
        elif arg.startswith("--set-env") and i + 1 < len(sys.argv):
            env_pair = sys.argv[i + 1]
            if '=' in env_pair:
                key, value = env_pair.split('=', 1)
                env_vars[key] = value
            i += 2
        elif arg.startswith("--") == False and action in ["init", "link"]:
            project_arg = sys.argv[i]
            i += 1
        else:
            i += 1

    print(f"🚀 Performing Railway action: {action}")

    # Check prerequisites
    if not check_railway_installed():
        return

    if not check_logged_in():
        return

    if action == "init":
        success = initialize_project(project_arg)
        if success and db_type:
            db_env_vars = setup_database_connection(db_type)
            if db_env_vars:
                # Add database vars to env_vars
                env_vars.update(db_env_vars)

        if success and env_vars:
            set_environment_variables(env_vars)

    elif action == "link":
        if not project_arg:
            print("❌ Project ID required for link action")
            return
        success = link_project(project_arg)
        if success and db_type:
            db_env_vars = setup_database_connection(db_type)
            if db_env_vars:
                env_vars.update(db_env_vars)
        if success and env_vars:
            set_environment_variables(env_vars)

    elif action == "deploy":
        # Create service configuration
        create_service_config(framework=framework, port=port)

        # Set environment variables if provided
        if env_vars:
            set_environment_variables(env_vars)

        # Deploy the application
        deploy_application()

    elif action == "setup":
        if not project_arg:
            print("❌ Framework type required for setup action")
            return

        framework = project_arg
        create_service_config(framework=framework, port=port)

        if db_type:
            db_env_vars = setup_database_connection(db_type)
            if db_env_vars:
                env_vars.update(db_env_vars)

        if env_vars:
            set_environment_variables(env_vars)

        print(f"✅ Setup complete for {framework} framework")

    else:
        print(f"❌ Unknown action: {action}")
        print("Available actions: init, deploy, link, setup")

if __name__ == "__main__":
    main()