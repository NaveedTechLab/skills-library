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
## When NOT to Use This Skill

- **Simple one-off kubectl deployments** — if you only need to apply a manifest once without GitOps tracking, use `kubernetes-deployer` directly
- **Environments without a Git repository** — ArgoCD is GitOps-first; without a Git source of truth the sync model doesn't work
- **Non-Kubernetes targets** — ArgoCD is Kubernetes-native; use standard CI/CD pipelines for VMs or serverless deployments

## Common Mistakes

- Not setting `syncPolicy.automated` with `selfHeal: true` — manual drift from the desired state won't be corrected automatically
- Committing secrets directly to the Git repo that ArgoCD syncs — use Sealed Secrets or external secret operators instead
- Not configuring health checks for custom resources — ArgoCD marks apps as Healthy before they're actually ready

## Related Skills

- [`k8s-foundation`](../k8s-foundation/SKILL.md) — Kubernetes cluster prerequisites for ArgoCD
- [`kubernetes-deployer`](../kubernetes-deployer/SKILL.md) — Imperative Kubernetes deployments when GitOps is not required
- [`infra-devops`](../infra-devops/SKILL.md) — Full infrastructure and DevOps pipeline including ArgoCD integration
