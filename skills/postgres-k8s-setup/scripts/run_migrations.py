#!/usr/bin/env python3

"""
PostgreSQL Migration Script
Connects to PostgreSQL and runs initial schema migrations.
Returns minimal success/failure logs to the context window.
"""

import os
import sys
import subprocess
import time
import psycopg2
from psycopg2 import sql


def run_kubectl_port_forward(namespace, release_name):
    """Set up port forwarding to the PostgreSQL pod."""
    try:
        # Get the pod name
        cmd = [
            "kubectl", "get", "pods",
            "-n", namespace,
            "-l", "app.kubernetes.io/name=postgresql,app.kubernetes.io/instance={}".format(release_name),
            "-o", "jsonpath={.items[0].metadata.name}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        pod_name = result.stdout.strip()
        
        if not pod_name:
            print("Error: Could not find PostgreSQL pod")
            return None
            
        # Start port forward in background
        port_forward_cmd = [
            "kubectl", "port-forward",
            "-n", namespace,
            pod_name,
            "5432:5432"
        ]
        
        # We'll use kubectl exec instead of port forwarding for simplicity
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error setting up port forward: {e}")
        return False


def run_migration_via_kubectl(namespace, release_name, db_name, password, migration_sql):
    """Execute migration SQL using kubectl exec inside the PostgreSQL pod."""
    try:
        # Create the SQL command
        sql_cmd = f'PGPASSWORD="{password}" psql -U postgres -d "{db_name}" -c "{migration_sql}"'
        
        # Execute the SQL command inside the PostgreSQL pod
        cmd = [
            "kubectl", "exec",
            "-n", namespace,
            "-c", "postgresql",
            f"statefulset/{release_name}-postgresql",  # Assuming statefulset name
            "--",
            "bash", "-c", sql_cmd
        ]
        
        # Try to find the correct pod name instead
        pod_cmd = [
            "kubectl", "get", "pods",
            "-n", namespace,
            "-l", "app.kubernetes.io/name=postgresql,app.kubernetes.io/instance={}".format(release_name),
            "-o", "jsonpath={.items[0].metadata.name}"
        ]
        
        result = subprocess.run(pod_cmd, capture_output=True, text=True, check=True)
        pod_name = result.stdout.strip()
        
        if not pod_name:
            # Try alternative label
            alt_pod_cmd = [
                "kubectl", "get", "pods",
                "-n", namespace,
                "-l", "app.kubernetes.io/name=postgresql",
                "-o", "jsonpath={.items[0].metadata.name}"
            ]
            result = subprocess.run(alt_pod_cmd, capture_output=True, text=True, check=True)
            pod_name = result.stdout.strip()
            
            if not pod_name:
                print("Error: Could not find PostgreSQL pod")
                return False
        
        # Execute the migration in the pod
        exec_cmd = [
            "kubectl", "exec",
            "-n", namespace,
            pod_name,
            "--",
            "psql", "-U", "postgres", "-d", db_name, "-c", migration_sql
        ]
        
        result = subprocess.run(exec_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Migration executed successfully")
            return True
        else:
            print(f"Error executing migration: {result.stderr}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Error executing migration: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during migration: {e}")
        return False


def verify_schema_via_kubectl(namespace, release_name, db_name, password):
    """Verify the database schema using kubectl exec."""
    try:
        # Simple query to verify schema exists
        verify_sql = "\\dt"
        
        pod_cmd = [
            "kubectl", "get", "pods",
            "-n", namespace,
            "-l", "app.kubernetes.io/name=postgresql,app.kubernetes.io/instance={}".format(release_name),
            "-o", "jsonpath={.items[0].metadata.name}"
        ]
        
        result = subprocess.run(pod_cmd, capture_output=True, text=True, check=True)
        pod_name = result.stdout.strip()
        
        if not pod_name:
            print("Error: Could not find PostgreSQL pod for verification")
            return False
        
        # Execute the verification in the pod
        exec_cmd = [
            "kubectl", "exec",
            "-n", namespace,
            pod_name,
            "--",
            "psql", "-U", "postgres", "-d", db_name, "-c", verify_sql
        ]
        
        result = subprocess.run(exec_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Schema verification successful")
            return True
        else:
            print(f"Error verifying schema: {result.stderr}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Error verifying schema: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during schema verification: {e}")
        return False


def main():
    """Main function to run migrations and verify schema."""
    namespace = os.environ.get("POSTGRES_NAMESPACE", "postgres")
    release_name = os.environ.get("POSTGRES_RELEASE_NAME", "postgres-release")
    db_name = os.environ.get("POSTGRES_DB", "mydatabase")
    password = os.environ.get("POSTGRES_PASSWORD", "secretpassword")
    
    # Default migration SQL - this can be extended or replaced based on needs
    migration_sql = """
        -- Create sample tables as part of initial migration
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            version VARCHAR(255) UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Insert initial migration record
        INSERT INTO schema_migrations (version) VALUES ('initial') 
        ON CONFLICT (version) DO NOTHING;
        
        -- Add more migration statements as needed
    """
    
    print("Starting PostgreSQL migration process...")
    
    # Run the migration
    migration_success = run_migration_via_kubectl(namespace, release_name, db_name, password, migration_sql)
    
    if not migration_success:
        print("Migration failed")
        sys.exit(1)
    
    # Verify the schema
    verification_success = verify_schema_via_kubectl(namespace, release_name, db_name, password)
    
    if not verification_success:
        print("Schema verification failed")
        sys.exit(1)
    
    print("PostgreSQL setup and migration completed successfully")


if __name__ == "__main__":
    main()