#!/usr/bin/env python3
"""
Next.js Kubernetes Deployment Orchestrator

This script orchestrates the complete deployment of a Next.js application to Kubernetes.
It generates the necessary Dockerfile, Kubernetes manifests, applies them, and verifies the deployment.
"""

import os
import sys
import subprocess
import argparse
import tempfile
from pathlib import Path
import yaml


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd
        )
        return result.stdout.strip(), result.stderr.strip(), 0
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode


def create_production_dockerfile(output_dir, app_path="."):
    """Create a multi-stage production-ready Dockerfile for Next.js."""
    dockerfile_content = f'''# Multi-stage build for Next.js application
# Stage 1: Build dependencies
FROM node:18-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY {app_path}/package.json {app_path}/package-lock.json ./

# Install dependencies
RUN npm ci --only=production

# Stage 2: Build the application
FROM node:18-alpine AS builder
WORKDIR /app

# Copy dependencies from previous stage
COPY --from=deps --chown=node:node /app/node_modules ./node_modules
COPY {app_path} .

# Build the application
RUN npm run build

# Stage 3: Production server
FROM node:18-alpine AS runner
WORKDIR /app

# Don't run production as root
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy dependencies from previous stage
COPY --from=deps --chown=nextjs:nodejs /app/node_modules ./node_modules

# Copy built application from builder stage
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV NODE_ENV production

# Final command to run the application
CMD ["node", "server.js"]
'''
    
    dockerfile_path = Path(output_dir) / "Dockerfile"
    with open(dockerfile_path, 'w') as f:
        f.write(dockerfile_content)
    
    return dockerfile_path


def create_deployment(output_dir, app_name, image, namespace="default", replicas=1, port=3000):
    """Create a Kubernetes Deployment manifest for Next.js."""
    deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': app_name,
            'namespace': namespace,
            'labels': {
                'app': app_name,
                'tier': 'frontend'
            }
        },
        'spec': {
            'replicas': replicas,
            'selector': {
                'matchLabels': {
                    'app': app_name
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app': app_name,
                        'tier': 'frontend'
                    }
                },
                'spec': {
                    'containers': [
                        {
                            'name': app_name,
                            'image': image,
                            'ports': [
                                {
                                    'containerPort': port,
                                    'protocol': 'TCP'
                                }
                            ],
                            'env': [
                                {
                                    'name': 'NODE_ENV',
                                    'value': 'production'
                                },
                                {
                                    'name': 'PORT',
                                    'value': str(port)
                                }
                            ],
                            'resources': {
                                'requests': {
                                    'memory': '256Mi',
                                    'cpu': '250m'
                                },
                                'limits': {
                                    'memory': '512Mi',
                                    'cpu': '500m'
                                }
                            },
                            'livenessProbe': {
                                'httpGet': {
                                    'path': '/',
                                    'port': port
                                },
                                'initialDelaySeconds': 30,
                                'periodSeconds': 10
                            },
                            'readinessProbe': {
                                'httpGet': {
                                    'path': '/',
                                    'port': port
                                },
                                'initialDelaySeconds': 5,
                                'periodSeconds': 5
                            }
                        }
                    ]
                }
            }
        }
    }
    
    deployment_path = Path(output_dir) / f"{app_name}-deployment.yaml"
    with open(deployment_path, 'w') as f:
        yaml.dump(deployment, f, default_flow_style=False)
    
    return deployment_path


def create_service(output_dir, app_name, namespace="default", port=3000, target_port=3000):
    """Create a Kubernetes Service manifest for Next.js."""
    service = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': f"{app_name}-service",
            'namespace': namespace,
            'labels': {
                'app': app_name,
                'tier': 'frontend'
            }
        },
        'spec': {
            'selector': {
                'app': app_name
            },
            'ports': [
                {
                    'port': port,
                    'targetPort': target_port,
                    'protocol': 'TCP',
                    'name': 'http'
                }
            ],
            'type': 'ClusterIP'
        }
    }
    
    service_path = Path(output_dir) / f"{app_name}-service.yaml"
    with open(service_path, 'w') as f:
        yaml.dump(service, f, default_flow_style=False)
    
    return service_path


def create_ingress(output_dir, app_name, namespace="default", host="app.example.com", path="/", port=3000):
    """Create a Kubernetes Ingress manifest for Next.js."""
    ingress = {
        'apiVersion': 'networking.k8s.io/v1',
        'kind': 'Ingress',
        'metadata': {
            'name': f"{app_name}-ingress",
            'namespace': namespace,
            'labels': {
                'app': app_name,
                'tier': 'frontend'
            },
            'annotations': {
                'kubernetes.io/ingress.class': 'nginx',
                'nginx.ingress.kubernetes.io/rewrite-target': '/',
                'cert-manager.io/cluster-issuer': 'letsencrypt-prod',
                'nginx.ingress.kubernetes.io/ssl-redirect': 'true'
            }
        },
        'spec': {
            'tls': [
                {
                    'hosts': [host],
                    'secretName': f"{app_name}-tls"
                }
            ],
            'rules': [
                {
                    'host': host,
                    'http': {
                        'paths': [
                            {
                                'path': path,
                                'pathType': 'Prefix',
                                'backend': {
                                    'service': {
                                        'name': f"{app_name}-service",
                                        'port': {
                                            'number': port
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }
    
    ingress_path = Path(output_dir) / f"{app_name}-ingress.yaml"
    with open(ingress_path, 'w') as f:
        yaml.dump(ingress, f, default_flow_style=False)
    
    return ingress_path


def build_and_push_image(dockerfile_path, image_name, context_path="."):
    """Build and push the Docker image."""
    print(f"Building Docker image: {image_name}")
    
    # Build the image
    cmd = f"docker build -t {image_name} -f {dockerfile_path} {context_path}"
    stdout, stderr, rc = run_command(cmd)
    
    if rc != 0:
        print(f"Error building image: {stderr}")
        return False
    
    print("✓ Docker image built successfully")
    
    # Push the image (optional - might need registry login)
    print(f"Pushing image: {image_name}")
    cmd = f"docker push {image_name}"
    stdout, stderr, rc = run_command(cmd)
    
    if rc != 0:
        print(f"Warning: Could not push image: {stderr}")
        print("Assuming image is available locally or in registry")
    else:
        print("✓ Docker image pushed successfully")
    
    return True


def apply_kubernetes_manifests(manifest_dir, namespace="default"):
    """Apply Kubernetes manifests to the cluster."""
    print(f"Applying Kubernetes manifests from {manifest_dir}")
    
    # Apply all YAML files in the manifest directory
    success_count = 0
    total_count = 0
    
    for manifest_file in Path(manifest_dir).glob("*.yaml"):
        total_count += 1
        print(f"Applying {manifest_file.name}")
        cmd = f"kubectl apply -f {manifest_file} -n {namespace}"
        stdout, stderr, rc = run_command(cmd)
        
        if rc != 0:
            print(f"Error applying {manifest_file}: {stderr}")
        else:
            print(f"✓ Applied {manifest_file.name}")
            success_count += 1
    
    return success_count == total_count


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
    
    import time
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
                    available_replicas = int(parts[1]) if parts[1] != '<none>' else 0
                    
                    ready_parts = ready_replicas_info.split('/')
                    if len(ready_parts) == 2:
                        ready = int(ready_parts[0]) if ready_parts[0] != '<none>' else 0
                        total = int(ready_parts[1]) if ready_parts[1] != '<none>' else 0
                        
                        if ready == total and total > 0 and available_replicas == total:
                            print(f"✓ Deployment {app_name} is ready ({ready}/{total} replicas)")
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


def verify_complete_deployment(app_name, namespace="default", timeout=300):
    """Verify the complete deployment status."""
    print(f"Verifying complete deployment for {app_name} in namespace {namespace}")
    print("="*60)
    
    # Check deployment
    deployment_ok = check_deployment_status(app_name, namespace, timeout)
    
    if deployment_ok:
        print(f"✓ All checks passed for {app_name}")
        return True
    else:
        print(f"✗ Deployment verification failed for {app_name}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Deploy Next.js application to Kubernetes')
    parser.add_argument('--app-name', '-n', required=True, help='Name of the application')
    parser.add_argument('--image', '-i', required=True, help='Docker image name')
    parser.add_argument('--namespace', default='default', help='Kubernetes namespace (default: default)')
    parser.add_argument('--replicas', type=int, default=1, help='Number of replicas (default: 1)')
    parser.add_argument('--port', type=int, default=3000, help='Application port (default: 3000)')
    parser.add_argument('--host', default='app.example.com', help='Ingress host (default: app.example.com)')
    parser.add_argument('--path', default='/', help='Ingress path (default: /)')
    parser.add_argument('--context-path', default='.', help='Docker build context path (default: .)')
    parser.add_argument('--skip-build', action='store_true', help='Skip Docker build step')
    parser.add_argument('--skip-push', action='store_true', help='Skip Docker push step')
    parser.add_argument('--timeout', type=int, default=300, help='Verification timeout in seconds (default: 300)')
    
    args = parser.parse_args()
    
    print(f"Starting Next.js deployment for: {args.app_name}")
    print("="*60)
    
    # Create temporary directory for manifests
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Step 1: Generate Dockerfile
        print("\nStep 1: Generating Dockerfile...")
        try:
            dockerfile_path = create_production_dockerfile(Path(temp_dir), ".")
            print(f"✓ Dockerfile generated at {dockerfile_path}")
        except Exception as e:
            print(f"✗ Error generating Dockerfile: {e}")
            sys.exit(1)
        
        # Step 2: Build and push image (if not skipped)
        if not args.skip_build:
            print("\nStep 2: Building Docker image...")
            success = build_and_push_image(dockerfile_path, args.image, args.context_path)
            if not success and not args.skip_push:
                print("✗ Image build/push failed")
                sys.exit(1)
        else:
            print("\nStep 2: Skipping Docker build (as requested)")
        
        # Step 3: Generate Kubernetes manifests
        print("\nStep 3: Generating Kubernetes manifests...")
        try:
            create_deployment(Path(temp_dir), args.app_name, args.image, args.namespace, args.replicas, args.port)
            create_service(Path(temp_dir), args.app_name, args.namespace, args.port, args.port)
            create_ingress(Path(temp_dir), args.app_name, args.namespace, args.host, args.path, args.port)
            print("✓ Kubernetes manifests generated")
        except Exception as e:
            print(f"✗ Error generating manifests: {e}")
            sys.exit(1)
        
        # Step 4: Apply Kubernetes manifests
        print("\nStep 4: Applying Kubernetes manifests...")
        success = apply_kubernetes_manifests(temp_dir, args.namespace)
        if not success:
            print("✗ Failed to apply Kubernetes manifests")
            sys.exit(1)
        
        # Step 5: Verify deployment
        print("\nStep 5: Verifying deployment...")
        success = verify_complete_deployment(
            args.app_name, 
            args.namespace, 
            args.timeout
        )
        
        if success:
            print("\n🎉 Complete! Next.js application deployed successfully to Kubernetes")
            print(f"   Application: {args.app_name}")
            print(f"   Namespace: {args.namespace}")
            print(f"   URL: https://{args.host}{args.path}")
            sys.exit(0)
        else:
            print("\n❌ Deployment verification failed")
            sys.exit(1)


if __name__ == "__main__":
    main()