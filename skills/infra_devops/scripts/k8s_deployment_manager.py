#!/usr/bin/env python3
"""
Kubernetes Deployment Manager
Handles containerization with Docker and deployment orchestration on Kubernetes.
Manages K8s manifests, auto-scaling configurations, and health monitoring for all system components.
"""

import os
import sys
import json
import time
import yaml
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import required libraries
try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    import docker
    from docker.errors import DockerException
    import requests
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install required packages: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class K8SDeploymentManager:
    def __init__(self, kubeconfig_path: Optional[str] = None):
        self.kubeconfig_path = kubeconfig_path
        self.docker_client = None
        self.apps_v1 = None
        self.core_v1 = None
        self.networking_v1 = None
        self.autoscaling_v2 = None

        # Initialize Kubernetes client
        self._initialize_k8s_client()

        # Initialize Docker client
        self._initialize_docker_client()

    def _initialize_k8s_client(self):
        """Initialize Kubernetes client."""
        try:
            if self.kubeconfig_path:
                config.load_kube_config(config_file=self.kubeconfig_path)
            else:
                # Try to load in-cluster config first, then kubeconfig
                try:
                    config.load_incluster_config()
                except:
                    config.load_kube_config()

            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
            self.networking_v1 = client.NetworkingV1Api()
            self.autoscaling_v2 = client.AutoscalingV2Api()

            logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise

    def _initialize_docker_client(self):
        """Initialize Docker client."""
        try:
            self.docker_client = docker.from_env()
            # Test Docker connection
            self.docker_client.version()
            logger.info("Docker client initialized successfully")
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise

    def build_docker_image(self, dockerfile_path: str, image_name: str, build_args: Dict[str, str] = None) -> bool:
        """Build a Docker image."""
        try:
            logger.info(f"Building Docker image: {image_name}")

            # Read the Dockerfile
            with open(dockerfile_path, 'r') as f:
                dockerfile_content = f.read()

            # Build the image
            image, build_logs = self.docker_client.images.build(
                path=os.path.dirname(dockerfile_path) or '.',
                dockerfile=os.path.basename(dockerfile_path),
                tag=image_name,
                buildargs=build_args or {},
                rm=True,  # Remove intermediate containers
                quiet=False
            )

            # Print build logs
            for log in build_logs:
                if 'stream' in log:
                    print(log['stream'], end='')

            logger.info(f"Successfully built image: {image_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to build Docker image: {e}")
            return False

    def push_docker_image(self, image_name: str, registry_url: str = None) -> bool:
        """Push Docker image to registry."""
        try:
            logger.info(f"Pushing Docker image: {image_name}")

            # Tag image if registry is specified
            if registry_url:
                tagged_name = f"{registry_url}/{image_name}"
                image = self.docker_client.images.get(image_name)
                image.tag(tagged_name)
                image_name = tagged_name

            # Push the image
            push_logs = self.docker_client.images.push(repository=image_name, stream=True, decode=True)

            # Print push logs
            for log in push_logs:
                if 'status' in log:
                    print(log['status'])
                elif 'error' in log:
                    print(f"Error: {log['error']}")
                    return False

            logger.info(f"Successfully pushed image: {image_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to push Docker image: {e}")
            return False

    def apply_k8s_manifest(self, manifest_path: str) -> bool:
        """Apply Kubernetes manifest."""
        try:
            logger.info(f"Applying Kubernetes manifest: {manifest_path}")

            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)

            # Determine the API to use based on the manifest kind
            if isinstance(manifest, list):
                # Handle list of resources
                for item in manifest:
                    self._apply_single_resource(item)
            else:
                # Handle single resource
                self._apply_single_resource(manifest)

            logger.info(f"Successfully applied manifest: {manifest_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply Kubernetes manifest: {e}")
            return False

    def _apply_single_resource(self, resource: Dict[str, Any]):
        """Apply a single Kubernetes resource."""
        api_version = resource.get('apiVersion', '')
        kind = resource.get('kind', '')
        metadata = resource.get('metadata', {})
        name = metadata.get('name', 'unknown')
        namespace = metadata.get('namespace', 'default')

        try:
            if kind == 'Deployment':
                if 'apps/v1' in api_version:
                    self.apps_v1.create_namespaced_deployment(
                        namespace=namespace,
                        body=resource,
                        _preload_content=False
                    )
                    logger.info(f"Created deployment: {name} in namespace: {namespace}")

            elif kind == 'Service':
                self.core_v1.create_namespaced_service(
                    namespace=namespace,
                    body=resource,
                    _preload_content=False
                )
                logger.info(f"Created service: {name} in namespace: {namespace}")

            elif kind == 'Ingress':
                self.networking_v1.create_namespaced_ingress(
                    namespace=namespace,
                    body=resource,
                    _preload_content=False
                )
                logger.info(f"Created ingress: {name} in namespace: {namespace}")

            elif kind == 'HorizontalPodAutoscaler':
                self.autoscaling_v2.create_namespaced_horizontal_pod_autoscaler(
                    namespace=namespace,
                    body=resource,
                    _preload_content=False
                )
                logger.info(f"Created HPA: {name} in namespace: {namespace}")

            elif kind == 'ConfigMap':
                self.core_v1.create_namespaced_config_map(
                    namespace=namespace,
                    body=resource,
                    _preload_content=False
                )
                logger.info(f"Created ConfigMap: {name} in namespace: {namespace}")

            elif kind == 'Secret':
                self.core_v1.create_namespaced_secret(
                    namespace=namespace,
                    body=resource,
                    _preload_content=False
                )
                logger.info(f"Created Secret: {name} in namespace: {namespace}")

            else:
                logger.warning(f"Unsupported resource kind: {kind}")

        except ApiException as e:
            if e.status == 409:  # Conflict - resource already exists
                # Update the existing resource
                logger.info(f"Resource {name} already exists, updating...")
                self._update_existing_resource(resource)
            else:
                logger.error(f"API error applying resource {name}: {e}")
                raise

    def _update_existing_resource(self, resource: Dict[str, Any]):
        """Update an existing Kubernetes resource."""
        api_version = resource.get('apiVersion', '')
        kind = resource.get('kind', '')
        metadata = resource.get('metadata', {})
        name = metadata.get('name', 'unknown')
        namespace = metadata.get('namespace', 'default')

        try:
            if kind == 'Deployment':
                if 'apps/v1' in api_version:
                    self.apps_v1.patch_namespaced_deployment(
                        name=name,
                        namespace=namespace,
                        body=resource,
                        _preload_content=False
                    )

            elif kind == 'Service':
                self.core_v1.patch_namespaced_service(
                    name=name,
                    namespace=namespace,
                    body=resource,
                    _preload_content=False
                )

            elif kind == 'Ingress':
                self.networking_v1.patch_namespaced_ingress(
                    name=name,
                    namespace=namespace,
                    body=resource,
                    _preload_content=False
                )

            elif kind == 'HorizontalPodAutoscaler':
                self.autoscaling_v2.patch_namespaced_horizontal_pod_autoscaler(
                    name=name,
                    namespace=namespace,
                    body=resource,
                    _preload_content=False
                )

            elif kind == 'ConfigMap':
                self.core_v1.patch_namespaced_config_map(
                    name=name,
                    namespace=namespace,
                    body=resource,
                    _preload_content=False
                )

            elif kind == 'Secret':
                self.core_v1.patch_namespaced_secret(
                    name=name,
                    namespace=namespace,
                    body=resource,
                    _preload_content=False
                )

            logger.info(f"Updated resource: {name}")

        except ApiException as e:
            logger.error(f"API error updating resource {name}: {e}")
            raise

    def deploy_application(self, app_name: str, image_name: str,
                          namespace: str = "default",
                          replicas: int = 3) -> bool:
        """Deploy a complete application with deployment, service, and ingress."""
        try:
            logger.info(f"Deploying application: {app_name} with image: {image_name}")

            # Create deployment manifest
            deployment_manifest = {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'metadata': {
                    'name': app_name,
                    'namespace': namespace,
                    'labels': {
                        'app': app_name,
                        'tier': 'backend'
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
                                'tier': 'backend'
                            }
                        },
                        'spec': {
                            'containers': [
                                {
                                    'name': 'app',
                                    'image': image_name,
                                    'ports': [
                                        {
                                            'containerPort': 8000,
                                            'name': 'http'
                                        }
                                    ],
                                    'resources': {
                                        'requests': {
                                            'cpu': '250m',
                                            'memory': '256Mi'
                                        },
                                        'limits': {
                                            'cpu': '500m',
                                            'memory': '512Mi'
                                        }
                                    },
                                    'livenessProbe': {
                                        'httpGet': {
                                            'path': '/health',
                                            'port': 8000
                                        },
                                        'initialDelaySeconds': 60,
                                        'periodSeconds': 30
                                    },
                                    'readinessProbe': {
                                        'httpGet': {
                                            'path': '/ready',
                                            'port': 8000
                                        },
                                        'initialDelaySeconds': 10,
                                        'periodSeconds': 5
                                    }
                                }
                            ]
                        }
                    }
                }
            }

            # Create service manifest
            service_manifest = {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {
                    'name': f'{app_name}-service',
                    'namespace': namespace,
                    'labels': {
                        'app': app_name
                    }
                },
                'spec': {
                    'selector': {
                        'app': app_name
                    },
                    'ports': [
                        {
                            'protocol': 'TCP',
                            'port': 80,
                            'targetPort': 8000
                        }
                    ],
                    'type': 'ClusterIP'
                }
            }

            # Create ingress manifest
            ingress_manifest = {
                'apiVersion': 'networking.k8s.io/v1',
                'kind': 'Ingress',
                'metadata': {
                    'name': f'{app_name}-ingress',
                    'namespace': namespace,
                    'labels': {
                        'app': app_name
                    },
                    'annotations': {
                        'nginx.ingress.kubernetes.io/rewrite-target': '/',
                        'cert-manager.io/cluster-issuer': 'letsencrypt-prod'
                    }
                },
                'spec': {
                    'tls': [
                        {
                            'hosts': [f'{app_name}.example.com'],
                            'secretName': f'{app_name}-tls-secret'
                        }
                    ],
                    'rules': [
                        {
                            'host': f'{app_name}.example.com',
                            'http': {
                                'paths': [
                                    {
                                        'path': '/',
                                        'pathType': 'Prefix',
                                        'backend': {
                                            'service': {
                                                'name': f'{app_name}-service',
                                                'port': {
                                                    'number': 80
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

            # Apply all manifests
            manifests = [
                deployment_manifest,
                service_manifest,
                ingress_manifest
            ]

            for manifest in manifests:
                temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml')
                yaml.dump(manifest, temp_file)
                temp_file.close()

                success = self.apply_k8s_manifest(temp_file.name)
                os.unlink(temp_file.name)

                if not success:
                    logger.error(f"Failed to apply manifest for {app_name}")
                    return False

            logger.info(f"Successfully deployed application: {app_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to deploy application {app_name}: {e}")
            return False

    def create_horizontal_pod_autoscaler(self, name: str, namespace: str,
                                       deployment_name: str,
                                       min_replicas: int = 2,
                                       max_replicas: int = 10,
                                       target_cpu_utilization: int = 70) -> bool:
        """Create a Horizontal Pod Autoscaler."""
        try:
            logger.info(f"Creating HPA: {name} for deployment: {deployment_name}")

            hpa_manifest = {
                'apiVersion': 'autoscaling/v2',
                'kind': 'HorizontalPodAutoscaler',
                'metadata': {
                    'name': name,
                    'namespace': namespace
                },
                'spec': {
                    'scaleTargetRef': {
                        'apiVersion': 'apps/v1',
                        'kind': 'Deployment',
                        'name': deployment_name
                    },
                    'minReplicas': min_replicas,
                    'maxReplicas': max_replicas,
                    'metrics': [
                        {
                            'type': 'Resource',
                            'resource': {
                                'name': 'cpu',
                                'target': {
                                    'type': 'Utilization',
                                    'averageUtilization': target_cpu_utilization
                                }
                            }
                        }
                    ]
                }
            }

            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml')
            yaml.dump(hpa_manifest, temp_file)
            temp_file.close()

            success = self.apply_k8s_manifest(temp_file.name)
            os.unlink(temp_file.name)

            return success

        except Exception as e:
            logger.error(f"Failed to create HPA {name}: {e}")
            return False

    def check_deployment_status(self, deployment_name: str, namespace: str = "default") -> Dict[str, Any]:
        """Check the status of a deployment."""
        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )

            status = {
                'available_replicas': deployment.status.available_replicas or 0,
                'ready_replicas': deployment.status.ready_replicas or 0,
                'updated_replicas': deployment.status.updated_replicas or 0,
                'desired_replicas': deployment.spec.replicas,
                'conditions': [
                    {
                        'type': condition.type,
                        'status': condition.status,
                        'reason': condition.reason,
                        'message': condition.message
                    }
                    for condition in deployment.status.conditions or []
                ] if deployment.status.conditions else []
            }

            logger.info(f"Deployment {deployment_name} status: {status}")
            return status

        except ApiException as e:
            logger.error(f"Failed to get deployment status: {e}")
            return {}

    def get_pod_logs(self, deployment_name: str, namespace: str = "default",
                    container_name: str = "app", tail_lines: int = 100) -> List[str]:
        """Get logs from pods in a deployment."""
        try:
            # Get pods for the deployment
            pods = self.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={deployment_name}"
            )

            logs = []
            for pod in pods.items:
                try:
                    pod_logs = self.core_v1.read_namespaced_pod_log(
                        name=pod.metadata.name,
                        namespace=namespace,
                        container=container_name,
                        tail_lines=tail_lines
                    )
                    logs.extend(pod_logs.split('\n'))
                except ApiException as e:
                    logger.warning(f"Failed to get logs for pod {pod.metadata.name}: {e}")

            return logs

        except Exception as e:
            logger.error(f"Failed to get pod logs: {e}")
            return []

    def scale_deployment(self, deployment_name: str, namespace: str = "default",
                        replicas: int = 3) -> bool:
        """Scale a deployment to a specific number of replicas."""
        try:
            logger.info(f"Scaling deployment {deployment_name} to {replicas} replicas")

            # Patch the deployment to change the replica count
            body = {
                'spec': {
                    'replicas': replicas
                }
            }

            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=body
            )

            logger.info(f"Successfully scaled deployment {deployment_name} to {replicas} replicas")
            return True

        except Exception as e:
            logger.error(f"Failed to scale deployment {deployment_name}: {e}")
            return False

def main():
    """Main function demonstrating the K8S Deployment Manager."""
    print("Kubernetes Deployment Manager")
    print("=" * 50)

    # Get configuration from environment or use defaults
    kubeconfig_path = os.getenv("KUBECONFIG")

    try:
        # Initialize the K8S Deployment Manager
        k8s_manager = K8SDeploymentManager(kubeconfig_path)

        # Example 1: Build and push Docker image
        print("\n1. Building Docker image...")
        dockerfile_path = "./Dockerfile"  # This would be the path to your Dockerfile
        image_name = "crm-app:latest"

        # Check if Dockerfile exists
        if os.path.exists(dockerfile_path):
            success = k8s_manager.build_docker_image(dockerfile_path, image_name)
            if success:
                print(f"   Docker image built successfully: {image_name}")

                # Push to registry (example)
                # registry_url = os.getenv("DOCKER_REGISTRY_URL")
                # if registry_url:
                #     k8s_manager.push_docker_image(image_name, registry_url)
            else:
                print("   Failed to build Docker image")
        else:
            print(f"   Dockerfile not found at {dockerfile_path}, skipping build")

        # Example 2: Deploy application
        print("\n2. Deploying application...")
        app_name = "crm-app-demo"
        namespace = "crm-platform"

        # Create namespace if it doesn't exist
        try:
            k8s_manager.core_v1.read_namespace(name=namespace)
        except ApiException:
            namespace_manifest = {
                'apiVersion': 'v1',
                'kind': 'Namespace',
                'metadata': {
                    'name': namespace
                }
            }
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml')
            yaml.dump(namespace_manifest, temp_file)
            temp_file.close()
            k8s_manager.apply_k8s_manifest(temp_file.name)
            os.unlink(temp_file.name)

        # Use a sample image for demonstration
        sample_image = "nginx:latest"  # Replace with actual image
        success = k8s_manager.deploy_application(
            app_name=app_name,
            image_name=sample_image,
            namespace=namespace,
            replicas=2
        )

        if success:
            print(f"   Application deployed successfully: {app_name}")
        else:
            print(f"   Failed to deploy application: {app_name}")

        # Example 3: Create HPA
        print("\n3. Creating Horizontal Pod Autoscaler...")
        hpa_success = k8s_manager.create_horizontal_pod_autoscaler(
            name=f"{app_name}-hpa",
            namespace=namespace,
            deployment_name=app_name,
            min_replicas=1,
            max_replicas=5,
            target_cpu_utilization=60
        )

        if hpa_success:
            print(f"   HPA created successfully for {app_name}")
        else:
            print(f"   Failed to create HPA for {app_name}")

        # Example 4: Check deployment status
        print("\n4. Checking deployment status...")
        status = k8s_manager.check_deployment_status(app_name, namespace)
        print(f"   Deployment status: {status}")

        # Example 5: Scale deployment
        print("\n5. Scaling deployment...")
        scale_success = k8s_manager.scale_deployment(
            deployment_name=app_name,
            namespace=namespace,
            replicas=3
        )

        if scale_success:
            print(f"   Successfully scaled {app_name} to 3 replicas")
        else:
            print(f"   Failed to scale {app_name}")

        print("\nKubernetes Deployment Manager demonstration completed successfully!")

    except Exception as e:
        logger.error(f"Error running K8S Deployment Manager: {e}")
        print(f"\nError: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())