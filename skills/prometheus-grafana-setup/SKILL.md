---
name: prometheus-grafana-setup
description: Deploy Prometheus and Grafana for Kubernetes monitoring. Use when Claude needs to set up monitoring infrastructure using Helm charts. Helm-based installation with default dashboards only, and minimal health verification output.
---

# Prometheus Grafana Setup

## Overview

This skill provides tools for deploying Prometheus and Grafana monitoring stack on Kubernetes using Helm charts. It focuses on Helm-based installation with default dashboards and minimal health verification output.

## Primary Functions

1. **Helm-based Installation**: Deploy Prometheus and Grafana using official Helm charts
2. **Default Dashboards**: Install standard dashboards for Kubernetes monitoring
3. **Health Verification**: Verify monitoring stack with minimal output
4. **Configuration**: Set up basic monitoring configuration

## Installation Workflow

Follow these steps to install Prometheus and Grafana:

1. **Check Prerequisites**: Verify Helm and Kubernetes access
2. **Add Helm Repositories**: Add Prometheus and Grafana Helm repositories
3. **Install Charts**: Deploy Prometheus and Grafana using Helm
4. **Configure Default Dashboards**: Install standard Kubernetes monitoring dashboards
5. **Verify Health**: Check minimal health status

## Chart Configuration

### Prometheus Configuration
- Resource limits and requests
- Storage configuration for long-term metrics
- Service discovery for Kubernetes
- Default alerting rules

### Grafana Configuration
- Admin credentials setup
- Default dashboard installation
- Data source configuration
- Ingress configuration for access

## Default Dashboards

The installation includes standard dashboards for:
- Kubernetes cluster overview
- Node monitoring
- Pod monitoring
- API server metrics
- ETCD monitoring
- Kubelet metrics

## Scripts Provided

This skill includes scripts for common monitoring operations:

### Installation Scripts
- `install_monitoring.sh`: Install complete monitoring stack
- `add_helm_repos.sh`: Add required Helm repositories
- `configure_values.sh`: Generate Helm values for customization

### Dashboard Scripts
- `install_dashboards.sh`: Install default dashboards
- `import_dashboard.sh`: Import specific dashboard
- `update_dashboards.sh`: Update installed dashboards

### Verification Scripts
- `check_health.sh`: Verify monitoring stack health
- `test_prometheus.sh`: Test Prometheus connectivity
- `test_grafana.sh`: Test Grafana connectivity

### Utility Scripts
- `get_credentials.sh`: Retrieve admin credentials
- `cleanup_monitoring.sh`: Remove monitoring stack

## Resources

### scripts/
Executable scripts for Prometheus and Grafana installation and management.

**Examples:**
- `install_monitoring.sh` - Script to install complete monitoring stack via Helm
- `check_health.sh` - Script to verify monitoring stack with minimal output
- `install_dashboards.sh` - Script to install default dashboards

**Appropriate for:** Helm-based monitoring stack installation and verification.

### references/
Documentation about Prometheus and Grafana configuration best practices.

**Examples:**
- Prometheus Helm chart configuration options
- Grafana dashboard customization guides
- Kubernetes monitoring best practices
- Security configuration guides

**Appropriate for:** In-depth information about monitoring stack configuration.

### assets/
Template files and configurations for monitoring setup.

**Examples:**
- Default values files for Helm charts
- Dashboard JSON configurations
- Data source configurations
- Ingress configurations

**Appropriate for:** Standard configurations used in monitoring setups.

---

**Any unneeded directories can be deleted.** Not every skill requires all three types of resources.
## When NOT to Use This Skill

- **Managed observability platforms** (Datadog, New Relic, Grafana Cloud) — if your organization pays for a managed monitoring service, use its native agent instead of self-hosting Prometheus/Grafana
- **Development-only environments** — full Prometheus/Grafana stacks add operational overhead; use simple console logging and local metrics in development
- **Serverless or ephemeral workloads** — the pull-based Prometheus scrape model doesn't work well with short-lived serverless functions; use push-based metrics (StatsD, CloudWatch) instead

## Common Mistakes

- Not setting retention limits on Prometheus storage — Prometheus's default local storage grows unboundedly; always configure `--storage.tsdb.retention.time` to cap disk usage
- Creating dashboards without setting alert thresholds — dashboards that only show data without alerting require humans to watch them continuously; always add Alertmanager rules
- Not labeling metrics with meaningful labels (service, environment, version) — metrics without labels are impossible to filter by environment or deployment version in multi-tenant setups

## Related Skills

- [`k8s-foundation`](../k8s-foundation/SKILL.md) — Kubernetes cluster on which Prometheus and Grafana are deployed
- [`watchdog-process-manager`](../watchdog-process-manager/SKILL.md) — Process-level monitoring that complements metrics-level monitoring
- [`audit-logging-system`](../audit-logging-system/SKILL.md) — Structured logging that works alongside metrics for full observability
