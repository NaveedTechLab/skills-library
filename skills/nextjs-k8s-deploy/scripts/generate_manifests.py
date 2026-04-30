#!/usr/bin/env python3
"""
Next.js Kubernetes Manifests Generator

This script creates Kubernetes manifests for deploying Next.js applications.
"""

import os
import sys
import argparse
from pathlib import Path
import yaml


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
    
    print(f"Created Deployment manifest: {deployment_path}")


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
    
    print(f"Created Service manifest: {service_path}")


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
    
    print(f"Created Ingress manifest: {ingress_path}")


def create_all_manifests(output_dir, app_name, image, namespace="default", replicas=1, port=3000, host="app.example.com", path="/"):
    """Create all Kubernetes manifests for Next.js deployment."""
    create_deployment(output_dir, app_name, image, namespace, replicas, port)
    create_service(output_dir, app_name, namespace, port, port)
    create_ingress(output_dir, app_name, namespace, host, path, port)


def main():
    parser = argparse.ArgumentParser(description='Generate Kubernetes manifests for Next.js apps')
    parser.add_argument('--output', '-o', default='.', help='Output directory (default: current directory)')
    parser.add_argument('--app-name', '-n', required=True, help='Name of the application')
    parser.add_argument('--image', '-i', required=True, help='Docker image name')
    parser.add_argument('--namespace', default='default', help='Kubernetes namespace (default: default)')
    parser.add_argument('--replicas', type=int, default=1, help='Number of replicas (default: 1)')
    parser.add_argument('--port', type=int, default=3000, help='Application port (default: 3000)')
    parser.add_argument('--host', default='app.example.com', help='Ingress host (default: app.example.com)')
    parser.add_argument('--path', default='/', help='Ingress path (default: /)')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating Kubernetes manifests for '{args.app_name}' in {output_dir}")
    print(f"Using image: {args.image}")
    print(f"Namespace: {args.namespace}")
    
    create_all_manifests(
        output_dir, 
        args.app_name, 
        args.image, 
        args.namespace, 
        args.replicas, 
        args.port, 
        args.host, 
        args.path
    )
    
    print("\\nKubernetes manifests generated successfully!")


if __name__ == "__main__":
    main()