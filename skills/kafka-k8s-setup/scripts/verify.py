#!/usr/bin/env python3

"""
Kafka Deployment Verification Script
Uses the MCP Code Execution pattern to check pod status via kubectl
and return a minimal "Done" or "Error" result to the agent context.
"""

import subprocess
import sys
import json
import time


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


def check_kafka_pods(namespace="kafka"):
    """Check the status of Kafka pods in the specified namespace."""
    # Check if namespace exists
    stdout, stderr, rc = run_kubectl_command(f"kubectl get namespace {namespace}")
    if rc != 0:
        print("Error")
        print(f"Namespace {namespace} does not exist")
        return False

    # Get Kafka pods
    stdout, stderr, rc = run_kubectl_command(
        f"kubectl get pods -n {namespace} -l app.kubernetes.io/name=kafka -o json"
    )
    
    if rc != 0:
        print("Error")
        print(f"Failed to get Kafka pods: {stderr}")
        return False

    try:
        pods_data = json.loads(stdout)
        pods = pods_data.get('items', [])
        
        if not pods:
            print("Error")
            print("No Kafka pods found in the namespace")
            return False
        
        # Check if all pods are running and ready
        for pod in pods:
            pod_name = pod['metadata']['name']
            phase = pod['status'].get('phase', 'Unknown')
            
            # Check if pod is running
            if phase != 'Running':
                print("Error")
                print(f"Pod {pod_name} is not running, phase: {phase}")
                return False
            
            # Check if all containers in the pod are ready
            container_statuses = pod['status'].get('containerStatuses', [])
            if not container_statuses:
                print("Error")
                print(f"No container statuses found for pod {pod_name}")
                return False
                
            for container_status in container_statuses:
                if not container_status.get('ready', False):
                    print("Error")
                    print(f"Container {container_status['name']} in pod {pod_name} is not ready")
                    return False
        
        # Also check Zookeeper pods if they exist
        zk_stdout, zk_stderr, zk_rc = run_kubectl_command(
            f"kubectl get pods -n {namespace} -l app.kubernetes.io/name=zookeeper -o json"
        )
        
        if zk_rc == 0:  # Zookeeper exists, check its status too
            try:
                zk_pods_data = json.loads(zk_stdout)
                zk_pods = zk_pods_data.get('items', [])
                
                for zk_pod in zk_pods:
                    zk_pod_name = zk_pod['metadata']['name']
                    zk_phase = zk_pod['status'].get('phase', 'Unknown')
                    
                    if zk_phase != 'Running':
                        print("Error")
                        print(f"Zookeeper pod {zk_pod_name} is not running, phase: {zk_phase}")
                        return False
                    
                    zk_container_statuses = zk_pod['status'].get('containerStatuses', [])
                    if not zk_container_statuses:
                        print("Error")
                        print(f"No container statuses found for zookeeper pod {zk_pod_name}")
                        return False
                        
                    for zk_container_status in zk_container_statuses:
                        if not zk_container_status.get('ready', False):
                            print("Error")
                            print(f"Zookeeper container {zk_container_status['name']} in pod {zk_pod_name} is not ready")
                            return False
            except json.JSONDecodeError:
                # If JSON parsing fails, continue without Zookeeper check
                pass
        
        print("Done")
        return True
        
    except json.JSONDecodeError:
        print("Error")
        print("Failed to parse kubectl output as JSON")
        return False
    except KeyError as e:
        print("Error")
        print(f"Missing expected field in kubectl output: {e}")
        return False


def main():
    """Main function to verify Kafka deployment."""
    # Allow namespace to be passed as command line argument
    namespace = sys.argv[1] if len(sys.argv) > 1 else "kafka"
    
    success = check_kafka_pods(namespace)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()