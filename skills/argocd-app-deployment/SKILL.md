---
name: argocd-app-deployment
description: Deploy applications to Kubernetes using Argo CD GitOps workflows. Use when Claude needs to work with Argo CD for GitOps-based deployments. GitOps pattern enforced, no CI pipeline design, application manifests only.
---

# ArgoCD App Deployment

## Overview

This skill provides tools for deploying applications to Kubernetes using Argo CD GitOps workflows. It focuses on GitOps patterns with application manifests, without involving CI pipeline design.

## Primary Functions

1. **Argo CD Application Management**: Create and manage Argo CD Applications
2. **GitOps Workflow**: Enforce GitOps patterns for deployment management
3. **Manifest Generation**: Create Kubernetes manifests for applications
4. **Sync Operations**: Trigger and monitor application synchronization

## GitOps Workflow

Follow these steps to deploy applications using GitOps:

1. **Prepare Application Manifests**: Create Kubernetes manifests in Git repository
2. **Create Argo CD Application**: Define Application CR with repository details
3. **Configure Sync Settings**: Set up auto-sync and pruning options
4. **Monitor Synchronization**: Track sync status and health
5. **Manage Lifecycle**: Handle updates, rollbacks, and deletions

## Application Definition Patterns

### Basic Application
- Source repository and path
- Destination cluster and namespace
- Sync policy configuration
- Health assessment settings

### Advanced Application
- Multiple sources configuration
- Sync windows and exclusions
- Resource hooks and finalizers
- Signature verification

## Argo CD Best Practices

### Security
- Use least-privilege RBAC permissions
- Enable signature verification for manifests
- Implement proper repository access controls
- Secure Argo CD instance with proper authentication

### Synchronization
- Configure appropriate sync policies
- Use pruning for resource cleanup
- Implement cascading deletes
- Monitor sync status continuously

### Health Assessment
- Define proper health checks for resources
- Use custom health checks when needed
- Monitor application health status
- Implement proper health assessment rules

## Scripts Provided

This skill includes scripts for common Argo CD operations:

### Application Management Scripts
- `create_application.sh`: Create Argo CD Application CR
- `sync_application.sh`: Trigger application synchronization
- `delete_application.sh`: Delete Argo CD Application
- `update_application.sh`: Update application configuration

### Manifest Management Scripts
- `generate_app_manifests.sh`: Generate application manifests
- `validate_manifests.sh`: Validate Kubernetes manifests
- `diff_manifests.sh`: Compare local and deployed manifests

### GitOps Workflow Scripts
- `setup_gitops_repo.sh`: Prepare Git repository for GitOps
- `commit_manifests.sh`: Commit manifests to Git repository
- `trigger_sync.sh`: Trigger sync from command line

### Monitoring Scripts
- `check_health.sh`: Check application health status
- `monitor_sync.sh`: Monitor sync progress
- `get_status.sh`: Get detailed application status

## Resources

### scripts/
Executable scripts for Argo CD application management and GitOps workflows.

**Examples:**
- `create_application.sh` - Script to create Argo CD Application CR
- `sync_application.sh` - Script to trigger application synchronization
- `check_health.sh` - Script to check application health status

**Appropriate for:** Argo CD Application management, GitOps workflows, and application lifecycle operations.

### references/
Documentation about Argo CD best practices and GitOps configuration patterns.

**Examples:**
- Argo CD Application CR specifications
- GitOps workflow best practices
- Security configuration guides
- Troubleshooting guides

**Appropriate for:** In-depth information about Argo CD configuration and GitOps practices.

### assets/
Template files and configurations for Argo CD applications.

**Examples:**
- Argo CD Application CR templates
- Git repository configuration templates
- Sync policy templates
- Health check configuration templates

**Appropriate for:** Standard templates used in Argo CD deployments.

---

**Any unneeded directories can be deleted.** Not every skill requires all three types of resources.