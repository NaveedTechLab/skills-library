#!/usr/bin/env python3
"""
Docusaurus Environment Validator

This script validates that the environment has all required tools and dependencies
for building and deploying Docusaurus sites.
"""

import os
import sys
import subprocess
import json
import argparse
from pathlib import Path


def run_command(cmd, capture_output=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=True
        )
        return result.stdout.strip(), result.stderr.strip(), 0
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode


def validate_node_js():
    """Validate Node.js installation."""
    print("Checking Node.js...")
    stdout, stderr, rc = run_command("node --version")
    if rc != 0:
        return False, "Node.js is not installed or not in PATH", {}
    
    version = stdout.replace("v", "")
    print(f"  ✓ Node.js version: {version}")
    return True, "", {"node_version": version}


def validate_npm():
    """Validate npm installation."""
    print("Checking npm...")
    stdout, stderr, rc = run_command("npm --version")
    if rc != 0:
        return False, "npm is not installed or not in PATH", {}
    
    version = stdout
    print(f"  ✓ npm version: {version}")
    return True, "", {"npm_version": version}


def validate_git():
    """Validate Git installation."""
    print("Checking Git...")
    stdout, stderr, rc = run_command("git --version")
    if rc != 0:
        return False, "Git is not installed or not in PATH", {}
    
    version = stdout
    print(f"  ✓ Git version: {version}")
    return True, "", {"git_version": version}


def validate_docker():
    """Validate Docker installation."""
    print("Checking Docker...")
    stdout, stderr, rc = run_command("docker --version")
    if rc != 0:
        return False, "Docker is not installed or not in PATH", {}
    
    version = stdout
    print(f"  ✓ Docker version: {version}")
    return True, "", {"docker_version": version}


def validate_kubectl():
    """Validate kubectl installation."""
    print("Checking kubectl...")
    stdout, stderr, rc = run_command("kubectl version --client=true --output=json")
    if rc != 0:
        # Even if server connection fails, client version check can still work
        stdout, stderr, rc = run_command("kubectl version --client=true")
        if rc != 0:
            return False, "kubectl is not installed or not in PATH", {}
        
        version = stdout
        print(f"  ✓ kubectl client version: {version}")
        return True, "", {"kubectl_client_version": version}
    
    try:
        version_info = json.loads(stdout)
        client_version = version_info.get("clientVersion", {}).get("gitVersion", "unknown")
        print(f"  ✓ kubectl client version: {client_version}")
        return True, "", {"kubectl_client_version": client_version}
    except json.JSONDecodeError:
        return False, "Could not parse kubectl version output", {}


def validate_docusaurus_project(project_path):
    """Validate Docusaurus project structure."""
    print(f"Checking Docusaurus project at {project_path}...")
    
    project_path = Path(project_path)
    
    # Check for docusaurus.config.js or docusaurus.config.ts
    config_files = list(project_path.glob("docusaurus.config.*"))
    if not config_files:
        return False, f"No docusaurus.config file found in {project_path}", {}
    
    print(f"  ✓ Found Docusaurus config: {config_files[0].name}")
    
    # Check for package.json
    package_json = project_path / "package.json"
    if not package_json.exists():
        return False, f"No package.json found in {project_path}", {}
    
    try:
        with open(package_json, 'r') as f:
            pkg_data = json.load(f)
    except json.JSONDecodeError:
        return False, f"Invalid package.json file in {project_path}", {}
    
    # Check for Docusaurus dependencies
    dependencies = pkg_data.get('dependencies', {})
    dev_dependencies = pkg_data.get('devDependencies', {})
    all_deps = {**dependencies, **dev_dependencies}
    
    docusaurus_deps = [dep for dep in all_deps.keys() if 'docusaurus' in dep.lower()]
    if not docusaurus_deps:
        return False, f"No Docusaurus dependencies found in package.json", {}
    
    print(f"  ✓ Found Docusaurus dependencies: {', '.join(docusaurus_deps)}")
    
    # Check for required scripts
    scripts = pkg_data.get('scripts', {})
    required_scripts = ['build', 'start', 'swizzle', 'deploy', 'serve', 'clear']
    found_scripts = [script for script in required_scripts if script in scripts]
    
    if 'build' not in scripts:
        return False, "No 'build' script found in package.json", {}
    
    print(f"  ✓ Found build script")
    
    return True, "", {
        "docusaurus_config": config_files[0].name,
        "docusaurus_dependencies": docusaurus_deps,
        "available_scripts": found_scripts
    }


def validate_available_space(path, required_mb=100):
    """Validate available disk space."""
    print(f"Checking available disk space...")
    
    try:
        statvfs = os.statvfs(path)
        available_bytes = statvfs.f_frsize * statvfs.f_bavail
        available_mb = available_bytes / (1024 * 1024)
        
        if available_mb < required_mb:
            return False, f"Not enough disk space: {available_mb:.2f}MB available, {required_mb}MB required", {}
        
        print(f"  ✓ Available disk space: {available_mb:.2f}MB")
        return True, "", {"available_disk_space_mb": round(available_mb, 2)}
    except OSError:
        return False, f"Cannot check disk space for {path}", {}


def validate_all(project_path="."):
    """Run all validations."""
    print("Running environment validation...\n")
    
    results = {
        "validations": {},
        "overall_success": True,
        "details": {}
    }
    
    # Run each validation
    validations = [
        ("node_js", validate_node_js),
        ("npm", validate_npm),
        ("git", validate_git),
        ("docker", validate_docker),
        ("kubectl", validate_kubectl),
        ("disk_space", lambda: validate_available_space(os.getcwd())),
        ("docusaurus_project", lambda: validate_docusaurus_project(project_path)),
    ]
    
    for name, validator in validations:
        try:
            success, error_msg, details = validator()
            results["validations"][name] = {
                "success": success,
                "error": error_msg
            }
            
            if details:
                results["details"].update(details)
            
            if not success:
                results["overall_success"] = False
                print(f"  ✗ {error_msg}\n")
            else:
                print()
        except Exception as e:
            results["validations"][name] = {
                "success": False,
                "error": str(e)
            }
            results["overall_success"] = False
            print(f"  ✗ Validation failed with exception: {e}\n")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Validate environment for Docusaurus deployment')
    parser.add_argument('--project-path', '-p', default='.', help='Path to Docusaurus project (default: current directory)')
    parser.add_argument('--format', '-f', choices=['text', 'json'], default='text', help='Output format (default: text)')
    
    args = parser.parse_args()
    
    results = validate_all(args.project_path)
    
    if args.format == 'json':
        import json as json_module
        print(json_module.dumps(results, indent=2))
    else:
        print("="*60)
        print("ENVIRONMENT VALIDATION RESULTS")
        print("="*60)
        
        for name, result in results["validations"].items():
            status = "✓" if result["success"] else "✗"
            print(f"{status} {name.replace('_', ' ').title()}: {'PASS' if result['success'] else 'FAIL'}")
            if not result["success"]:
                print(f"    Error: {result['error']}")
        
        print("\n" + "="*60)
        if results["overall_success"]:
            print("🎉 All validations PASSED! Environment is ready for Docusaurus deployment.")
            sys.exit(0)
        else:
            print("❌ Some validations FAILED. Please fix the issues before proceeding.")
            sys.exit(1)


if __name__ == "__main__":
    main()