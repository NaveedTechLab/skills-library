#!/usr/bin/env python3
"""
Next.js Kubernetes Deployment Verifier

This script verifies that a Next.js application has been deployed successfully to Kubernetes.
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path


def run_kubectl_command(cmd):
    """Run a kubectl command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip(), result.stderr.strip(), 0
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode


def check_deployment_status(app_name, namespace="default", timeout=300):
    """Check the status of the deployment."""
    print(f"Checking deployment status for {app_name} in namespace {namespace}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check deployment status
        stdout, stderr, rc = run_kubectl_command(
            f"kubectl get deployment {app_name} -n {namespace} -o jsonpath='{{.status.readyReplicas}}/{{.status.replicas}} {{.status.availableReplicas}}'"
        )
        
        if rc != 0:
            print(f"Error checking deployment: {stderr}")
            time.sleep(5)
            continue
        
        if stdout:
            try:
                parts = stdout.split()
                if len(parts) >= 2:
                    ready_replicas_info = parts[0]
                    available_replicas = int(parts[1])
                    
                    ready_parts = ready_replicas_info.split('/')
                    if len(ready_parts) == 2:
                        ready = int(ready_parts[0]) if ready_parts[0] != '<none>' else 0
                        total = int(ready_parts[1]) if ready_parts[1] != '<none>' else 0
                        
                        if ready == total and total > 0 and available_replicas == total:
                            print(f"✓ Deployment {app_name} is ready ({ready}/{total} replicas)")
                            
                            # Check if pods are running
                            check_pods_status(app_name, namespace)
                            return True
                        else:
                            print(f"  Waiting for deployment: {ready}/{total} ready, {available_replicas} available")
                else:
                    print(f"  Unexpected output format: {stdout}")
            except ValueError:
                print(f"  Error parsing deployment status: {stdout}")
        
        time.sleep(5)
    
    print(f"✗ Deployment {app_name} did not become ready within {timeout} seconds")
    return False


def check_pods_status(app_name, namespace="default"):
    """Check the status of pods in the deployment."""
    print(f"Checking pod status for {app_name} in namespace {namespace}...")
    
    # Get pods for the app
    stdout, stderr, rc = run_kubectl_command(
        f"kubectl get pods -n {namespace} -l app={app_name} -o json"
    )
    
    if rc != 0:
        print(f"Error checking pods: {stderr}")
        return False
    
    import json
    try:
        pods_data = json.loads(stdout)
        pods = pods_data.get('items', [])
        
        if not pods:
            print(f"✗ No pods found for app {app_name}")
            return False
        
        all_ready = True
        for pod in pods:
            pod_name = pod['metadata']['name']
            phase = pod['status'].get('phase', 'Unknown')
            container_statuses = pod['status'].get('containerStatuses', [])
            
            # Check if pod is running
            if phase != 'Running':
                print(f"  ✗ Pod {pod_name} is not running, phase: {phase}")
                all_ready = False
                continue
            
            # Check if all containers in the pod are ready
            for container_status in container_statuses:
                if not container_status.get('ready', False):
                    print(f"  ✗ Container {container_status['name']} in pod {pod_name} is not ready")
                    all_ready = False
                    break
        
        if all_ready:
            print(f"✓ All pods for {app_name} are running and ready")
            return True
        else:
            return False
            
    except json.JSONDecodeError:
        print(f"✗ Failed to parse kubectl output as JSON")
        return False


def check_service_status(app_name, namespace="default"):
    """Check the status of the service."""
    print(f"Checking service status for {app_name}-service in namespace {namespace}...")
    
    stdout, stderr, rc = run_kubectl_command(
        f"kubectl get service {app_name}-service -n {namespace} -o json"
    )
    
    if rc != 0:
        print(f"✗ Service {app_name}-service not found: {stderr}")
        return False
    
    print(f"✓ Service {app_name}-service exists")
    return True


def check_ingress_status(app_name, namespace="default"):
    """Check the status of the ingress."""
    print(f"Checking ingress status for {app_name}-ingress in namespace {namespace}...")
    
    stdout, stderr, rc = run_kubectl_command(
        f"kubectl get ingress {app_name}-ingress -n {namespace} -o json"
    )
    
    if rc != 0:
        print(f"✗ Ingress {app_name}-ingress not found: {stderr}")
        return False
    
    import json
    try:
        ingress_data = json.loads(stdout)
        status = ingress_data.get('status', {})
        load_balancer = status.get('loadBalancer', {})
        ingress_list = load_balancer.get('ingress', [])
        
        if ingress_list:
            print(f"✓ Ingress {app_name}-ingress is configured with load balancer addresses")
            for ing in ingress_list:
                ip = ing.get('ip')
                hostname = ing.get('hostname')
                if ip:
                    print(f"  - IP: {ip}")
                if hostname:
                    print(f"  - Hostname: {hostname}")
        else:
            print(f"⚠ Ingress {app_name}-ingress exists but may not have an external address yet")
        
        return True
    except json.JSONDecodeError:
        print(f"✗ Failed to parse ingress status as JSON")
        return False


def verify_complete_deployment(app_name, namespace="default", timeout=300):
    """Verify the complete deployment status."""
    print(f"Verifying complete deployment for {app_name} in namespace {namespace}")
    print("="*60)
    
    # Check deployment
    deployment_ok = check_deployment_status(app_name, namespace, timeout)
    
    print()
    
    # Check service
    service_ok = check_service_status(app_name, namespace)
    
    print()
    
    # Check ingress
    ingress_ok = check_ingress_status(app_name, namespace)
    
    print()
    print("="*60)
    
    if deployment_ok and service_ok and ingress_ok:
        print("✓ All components are successfully deployed!")
        print("✓ Next.js application is running in Kubernetes")
        return True
    else:
        print("✗ Some components failed to deploy properly")
        return False


def main():
    parser = argparse.ArgumentParser(description='Verify Next.js deployment status in Kubernetes')
    parser.add_argument('--app-name', '-n', required=True, help='Name of the application')
    parser.add_argument('--namespace', default='default', help='Kubernetes namespace (default: default)')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout in seconds (default: 300)')
    
    args = parser.parse_args()
    
    success = verify_complete_deployment(args.app_name, args.namespace, args.timeout)
    
    if success:
        print("\\n🎉 Deployment verification completed successfully!")
        sys.exit(0)
    else:
        print("\\n❌ Deployment verification failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()