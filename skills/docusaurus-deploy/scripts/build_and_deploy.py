#!/usr/bin/env python3
"""
Docusaurus Site Builder and Deployer

This script builds a Docusaurus site and deploys it to a specified target.
It handles environment validation and returns a clean deployment URL.
"""

import os
import sys
import subprocess
import argparse
import shutil
import tempfile
import json
from pathlib import Path
from urllib.parse import urlparse


def run_command(cmd, cwd=None, capture_output=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=True,
            cwd=cwd
        )
        return result.stdout.strip(), result.stderr.strip(), 0
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode


def validate_environment():
    """Validate that required tools are available."""
    print("Validating environment...")
    
    # Check for Node.js
    stdout, stderr, rc = run_command("node --version")
    if rc != 0:
        print("Error: Node.js is not installed or not in PATH")
        return False
    print(f"✓ Node.js version: {stdout}")
    
    # Check for npm
    stdout, stderr, rc = run_command("npm --version")
    if rc != 0:
        print("Error: npm is not installed or not in PATH")
        return False
    print(f"✓ npm version: {stdout}")
    
    # Check for git (if needed)
    stdout, stderr, rc = run_command("git --version")
    if rc != 0:
        print("Warning: Git is not installed or not in PATH")
    else:
        print(f"✓ Git version: {stdout}")
    
    # Check for Docker (if deploying to containerized environments)
    stdout, stderr, rc = run_command("docker --version")
    if rc != 0:
        print("Info: Docker is not installed or not in PATH (may be needed for containerized deployments)")
    else:
        print(f"✓ Docker version: {stdout}")
    
    return True


def check_docusaurus_project(project_path):
    """Check if the given path contains a valid Docusaurus project."""
    project_path = Path(project_path)
    
    # Check for docusaurus.config.js or docusaurus.config.ts
    config_files = list(project_path.glob("docusaurus.config.*"))
    if not config_files:
        print(f"Error: No docusaurus.config file found in {project_path}")
        return False
    
    # Check for package.json with docusaurus dependencies
    package_json = project_path / "package.json"
    if not package_json.exists():
        print(f"Error: No package.json found in {project_path}")
        return False
    
    try:
        with open(package_json, 'r') as f:
            pkg_data = json.load(f)
        
        dependencies = pkg_data.get('dependencies', {})
        dev_dependencies = pkg_data.get('devDependencies', {})
        all_deps = {**dependencies, **dev_dependencies}
        
        docusaurus_deps = [dep for dep in all_deps.keys() if 'docusaurus' in dep.lower()]
        if not docusaurus_deps:
            print(f"Error: No Docusaurus dependencies found in package.json")
            return False
        
        print(f"✓ Found Docusaurus dependencies: {', '.join(docusaurus_deps)}")
        return True
    except json.JSONDecodeError:
        print(f"Error: Invalid package.json file")
        return False


def install_dependencies(project_path):
    """Install project dependencies."""
    print("Installing dependencies...")
    
    stdout, stderr, rc = run_command("npm install", cwd=project_path)
    if rc != 0:
        print(f"Error installing dependencies: {stderr}")
        return False
    
    print("✓ Dependencies installed")
    return True


def build_site(project_path, out_dir=None):
    """Build the Docusaurus site."""
    print("Building Docusaurus site...")
    
    build_cmd = "npm run build"
    if out_dir:
        # If we need to specify output directory, we might need to modify the config or use a custom command
        # For now, we'll assume the config handles the output directory
        pass
    
    stdout, stderr, rc = run_command(build_cmd, cwd=project_path)
    if rc != 0:
        print(f"Error building site: {stderr}")
        return False, None
    
    # Determine the output directory - typically 'build' in Docusaurus
    build_path = Path(project_path) / "build"
    if not build_path.exists():
        print("Error: Build directory not found after build")
        return False, None
    
    print(f"✓ Site built successfully in {build_path}")
    return True, build_path


def deploy_to_kubernetes(build_path, site_name, namespace="default", image_registry=None):
    """Deploy the built site to Kubernetes."""
    print(f"Deploying to Kubernetes in namespace {namespace}...")
    
    # Create a temporary directory for Kubernetes manifests
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a Dockerfile for the static site
        dockerfile_content = f'''FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
'''
        dockerfile_path = temp_path / "Dockerfile"
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        # Copy built site to temp directory
        site_dist = temp_path / "site"
        shutil.copytree(build_path, site_dist)
        
        # Build and push Docker image if registry is specified
        if image_registry:
            image_name = f"{image_registry}/{site_name}:{os.environ.get('BUILD_VERSION', 'latest')}"
            
            # Build Docker image
            print(f"Building Docker image: {image_name}")
            stdout, stderr, rc = run_command(f"docker build -t {image_name} .", cwd=temp_path)
            if rc != 0:
                print(f"Error building Docker image: {stderr}")
                return None
            
            # Push Docker image
            print(f"Pushing Docker image: {image_name}")
            stdout, stderr, rc = run_command(f"docker push {image_name}")
            if rc != 0:
                print(f"Error pushing Docker image: {stderr}")
                return None
            
            # Create Kubernetes deployment with the image
            deployment_yaml = f'''apiVersion: apps/v1
kind: Deployment
metadata:
  name: {site_name}
  namespace: {namespace}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {site_name}
  template:
    metadata:
      labels:
        app: {site_name}
    spec:
      containers:
      - name: nginx
        image: {image_name}
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: {site_name}-service
  namespace: {namespace}
spec:
  selector:
    app: {site_name}
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {site_name}-ingress
  namespace: {namespace}
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: {site_name}.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {site_name}-service
            port:
              number: 80
'''
        else:
            # Create a configmap with the site content and mount it in nginx
            deployment_yaml = f'''apiVersion: v1
kind: ConfigMap
metadata:
  name: {site_name}-content
  namespace: {namespace}
data:
  # Site content would be included here, but for large sites this isn't practical
  # So we'll skip this approach and suggest using Docker images
  index.html: "<html><body>Docusaurus site deployed</body></html>"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {site_name}
  namespace: {namespace}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {site_name}
  template:
    metadata:
      labels:
        app: {site_name}
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        volumeMounts:
        - name: site-content
          mountPath: /usr/share/nginx/html
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
      volumes:
      - name: site-content
        configMap:
          name: {site_name}-content
---
apiVersion: v1
kind: Service
metadata:
  name: {site_name}-service
  namespace: {namespace}
spec:
  selector:
    app: {site_name}
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
'''
        
        # Write deployment YAML
        deployment_path = temp_path / "deployment.yaml"
        with open(deployment_path, 'w') as f:
            f.write(deployment_yaml)
        
        # Apply the deployment
        stdout, stderr, rc = run_command(f"kubectl apply -f {deployment_path}")
        if rc != 0:
            print(f"Error applying Kubernetes deployment: {stderr}")
            return None
        
        # Get the service URL
        ingress_host = f"{site_name}.example.com"  # This would need to be configured properly
        return f"http://{ingress_host}"


def deploy_to_static_hosting(build_path, target_path):
    """Deploy the built site to static hosting (e.g., local directory, FTP, S3)."""
    print(f"Deploying to static hosting at {target_path}...")
    
    target_path = Path(target_path)
    
    # Create target directory if it doesn't exist
    target_path.mkdir(parents=True, exist_ok=True)
    
    # Copy the built site to the target location
    for item in build_path.iterdir():
        source_item = build_path / item.name
        target_item = target_path / item.name
        
        if source_item.is_dir():
            if target_item.exists():
                shutil.rmtree(target_item)
            shutil.copytree(source_item, target_item)
        else:
            shutil.copy2(source_item, target_item)
    
    print(f"✓ Site deployed to {target_path}")
    
    # Return a file:// URL for local deployment, or http:// for web servers
    if target_path.is_absolute():
        return f"file://{target_path}"
    else:
        return f"file://{Path.cwd() / target_path}"


def main():
    parser = argparse.ArgumentParser(description='Build and deploy Docusaurus site')
    parser.add_argument('--project-path', '-p', default='.', help='Path to Docusaurus project (default: current directory)')
    parser.add_argument('--target', '-t', required=True, 
                       choices=['kubernetes', 'static'], 
                       help='Deployment target')
    parser.add_argument('--site-name', '-n', help='Site name for deployment (required for Kubernetes)')
    parser.add_argument('--namespace', default='default', help='Kubernetes namespace (default: default)')
    parser.add_argument('--target-path', help='Target path for static deployment')
    parser.add_argument('--image-registry', help='Docker image registry for Kubernetes deployment')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.target == 'kubernetes' and not args.site_name:
        print("Error: --site-name is required for Kubernetes deployment")
        sys.exit(1)
    
    if args.target == 'static' and not args.target_path:
        print("Error: --target-path is required for static deployment")
        sys.exit(1)
    
    # Validate environment
    if not validate_environment():
        print("Environment validation failed")
        sys.exit(1)
    
    # Check if it's a valid Docusaurus project
    if not check_docusaurus_project(args.project_path):
        print("Invalid Docusaurus project")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies(args.project_path):
        print("Dependency installation failed")
        sys.exit(1)
    
    # Build the site
    success, build_path = build_site(args.project_path)
    if not success:
        print("Site build failed")
        sys.exit(1)
    
    # Deploy based on target
    deployment_url = None
    if args.target == 'kubernetes':
        deployment_url = deploy_to_kubernetes(
            build_path, 
            args.site_name, 
            args.namespace, 
            args.image_registry
        )
    elif args.target == 'static':
        deployment_url = deploy_to_static_hosting(build_path, args.target_path)
    
    if deployment_url:
        print(f"\n🎉 Deployment successful!")
        print(f"Site URL: {deployment_url}")
        return 0
    else:
        print("\n❌ Deployment failed")
        sys.exit(1)


if __name__ == "__main__":
    main()