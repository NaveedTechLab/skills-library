---
name: k8s-foundation
description: Validate Kubernetes cluster health and apply foundational Helm charts. Use when Claude needs to check cluster status, deploy core infrastructure components, or ensure cluster readiness for applications. Must use kubectl and helm via scripts. No environment setup instructions. Return minimal success/failure output.
---

# K8s Foundation

## Overview

This skill provides tools for validating Kubernetes cluster health and applying foundational Helm charts. It focuses on cluster readiness assessment and deployment of essential infrastructure components.

## Primary Functions

1. **Cluster Health Validation**: Check if the Kubernetes cluster is operational and healthy
2. **Foundational Chart Deployment**: Apply essential Helm charts that form the foundation of the cluster
3. **Readiness Assessment**: Verify that the cluster is ready for application deployments

## Validation Workflow

Follow these steps to validate cluster health:

1. **Check Cluster Connectivity**: Verify kubectl can reach the cluster
2. **Assess Node Status**: Validate all nodes are ready and operational
3. **Review System Pods**: Ensure core Kubernetes pods are running properly
4. **Test Resource Availability**: Confirm sufficient resources are available
5. **Validate Access Rights**: Verify required permissions for operations

## Deployment Workflow

For applying foundational Helm charts:

1. **Prerequisite Check**: Ensure cluster meets requirements for chart deployment
2. **Helm Repo Update**: Update Helm repositories to latest versions
3. **Chart Installation**: Deploy charts with appropriate values
4. **Post-Installation Validation**: Verify successful deployment
5. **Status Reporting**: Return minimal success/failure output

## Essential Foundational Charts

Common foundational charts that might be deployed:

- **ingress-nginx**: Ingress controller for external traffic
- **cert-manager**: Certificate management for TLS
- **metrics-server**: Resource metrics for HPA and monitoring
- **prometheus-stack**: Monitoring and alerting stack
- **loki-stack**: Logging aggregation
- **external-secrets**: External secret management
- **vault**: Secret management solution

## Scripts Provided

This skill includes scripts for common Kubernetes and Helm operations:

### Cluster Validation Scripts
- `check_cluster_health.sh`: Comprehensive cluster health validation
- `validate_nodes.sh`: Node status verification
- `check_system_pods.sh`: Core pod readiness check

### Deployment Scripts
- `apply_foundational_charts.sh`: Deploy all foundational charts
- `install_ingress_controller.sh`: Deploy ingress controller
- `install_monitoring.sh`: Deploy monitoring stack
- `install_logging.sh`: Deploy logging stack

### Utility Scripts
- `wait_for_deployment.sh`: Wait until deployment is ready
- `check_helm_status.sh`: Verify Helm release status

## Resources

### scripts/
Executable scripts that use kubectl and helm commands for cluster operations.

**Examples:**
- `validate_cluster.sh` - Script to check cluster connectivity and node status
- `deploy_foundation.sh` - Script to apply foundational Helm charts
- `health_check.sh` - Script to validate cluster readiness

**Appropriate for:** Kubernetes validation, Helm chart deployment, cluster readiness checks, and infrastructure provisioning.

### references/
Documentation about Kubernetes cluster validation best practices and foundational chart configurations.

**Examples:**
- Kubernetes readiness criteria
- Common Helm chart values for foundational components
- Troubleshooting guides for common cluster issues
- Best practices for infrastructure deployment

**Appropriate for:** In-depth information about cluster validation techniques and chart configurations.

### assets/
Template files and configurations for foundational charts.

**Examples:**
- Default values.yaml files for common foundational charts
- RBAC configuration templates
- Namespace configuration files

**Appropriate for:** Standard configurations and templates used in deployments.

---

**Any unneeded directories can be deleted.** Not every skill requires all three types of resources.