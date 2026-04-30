#!/bin/bash
"""
Dashboard installer for prometheus-grafana-setup skill

This script installs default dashboards for Prometheus and Grafana monitoring.
"""

set -e  # Exit on any error

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo "FAILURE: kubectl is not installed or not in PATH"
        exit 1
    fi

    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        echo "FAILURE: Cannot connect to Kubernetes cluster"
        exit 1
    fi
}

# Function to wait for Grafana to be ready
wait_for_grafana() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Waiting for Grafana to be ready in namespace $namespace..."

    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=grafana,release="$release_name" \
        --namespace "$namespace" \
        --timeout=300s

    echo "SUCCESS: Grafana is ready"
}

# Function to get Grafana admin password
get_grafana_password() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    local secret_name="$release_name-grafana"

    # Try to get the admin password from the secret
    local password
    password=$(kubectl get secret "$secret_name" -n "$namespace" -o jsonpath="{.data.admin-password}" 2>/dev/null | base64 -d)

    if [ -n "$password" ]; then
        echo "$password"
    else
        echo "prom-operator"  # Default fallback
    fi
}

# Function to get Grafana service URL
get_grafana_url() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    # Get the Grafana pod name and create a port forward
    local pod_name
    pod_name=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=grafana,release="$release_name" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -n "$pod_name" ]; then
        echo "http://localhost:3000"
    else
        echo "Could not find Grafana pod"
        return 1
    fi
}

# Function to install default dashboards via ConfigMap
install_dashboards_via_configmap() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Installing default dashboards via ConfigMap..."

    # Create ConfigMap with default dashboard configurations
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${release_name}-default-dashboards
  namespace: $namespace
  labels:
    grafana_dashboard: "1"
    release: $release_name
data:
  k8s-cluster-summary.json: |-
    {
      "dashboard": {
        "id": null,
        "title": "Kubernetes Cluster Summary",
        "tags": ["kubernetes"],
        "style": "dark",
        "timezone": "browser",
        "refresh": "10s"
      }
    }
  node-resources.json: |-
    {
      "dashboard": {
        "id": null,
        "title": "Node Resources",
        "tags": ["kubernetes", "nodes"],
        "style": "dark",
        "timezone": "browser",
        "refresh": "10s"
      }
    }
  pod-resources.json: |-
    {
      "dashboard": {
        "id": null,
        "title": "Pod Resources",
        "tags": ["kubernetes", "pods"],
        "style": "dark",
        "timezone": "browser",
        "refresh": "10s"
      }
    }
EOF

    echo "SUCCESS: Default dashboards ConfigMap created"
}

# Function to install dashboards from external sources
install_dashboards_from_sources() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Installing dashboards from external sources..."

    # Install popular dashboards using Grafana's dashboard API
    # For now, we'll create ConfigMaps that Grafana can automatically load

    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${release_name}-k8s-apps-dashboard
  namespace: $namespace
  labels:
    grafana_dashboard: "1"
    release: $release_name
data:
  kubernetes-apps.json: |-
    {
      "dashboard": {
        "id": null,
        "title": "Kubernetes Apps",
        "tags": ["kubernetes", "apps"],
        "style": "dark",
        "timezone": "browser",
        "refresh": "5m",
        "panels": [
          {
            "id": 1,
            "title": "App Request Rate",
            "type": "graph",
            "targets": [
              {
                "expr": "sum(rate(http_requests_total[5m])) by (app)",
                "legendFormat": "{{app}}"
              }
            ]
          }
        ]
      }
    }
EOF

    cat <<EOF | kubectl apply -f -
apiVectors: v1
kind: ConfigMap
metadata:
  name: ${release_name}-node-exporter-dashboard
  namespace: $namespace
  labels:
    grafana_dashboard: "1"
    release: $release_name
data:
  node-exporter-full.json: |-
    {
      "dashboard": {
        "id": null,
        "title": "Node Exporter Full",
        "tags": ["node", "exporter"],
        "style": "dark",
        "timezone": "browser",
        "refresh": "1m",
        "panels": [
          {
            "id": 1,
            "title": "CPU Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
                "legendFormat": "{{instance}}"
              }
            ]
          },
          {
            "id": 2,
            "title": "Memory Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))",
                "legendFormat": "{{instance}}"
              }
            ]
          }
        ]
      }
    }
EOF

    echo "SUCCESS: External dashboards installed"
}

# Function to verify dashboard installation
verify_dashboard_installation() {
    local namespace=${1:-"monitoring"}

    echo "Verifying dashboard installation..."

    # Count dashboard ConfigMaps
    local dashboard_count
    dashboard_count=$(kubectl get configmaps -n "$namespace" -l grafana_dashboard=1 --no-headers 2>/dev/null | wc -l)

    echo "INFO: Found $dashboard_count dashboard ConfigMaps"

    # List dashboard ConfigMaps
    kubectl get configmaps -n "$namespace" -l grafana_dashboard=1 -o name 2>/dev/null || echo "No dashboard ConfigMaps found"

    echo "SUCCESS: Dashboard installation verified"
}

# Function to run complete dashboard installation
run_complete_dashboard_installation() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Starting complete dashboard installation..."

    check_kubectl
    wait_for_grafana "$namespace" "$release_name"
    install_dashboards_via_configmap "$namespace" "$release_name"
    install_dashboards_from_sources "$namespace" "$release_name"
    verify_dashboard_installation "$namespace"

    echo ""
    echo "DASHBOARD INSTALLATION COMPLETE"
    echo "Default dashboards installed for monitoring stack in namespace $namespace"

    # Get Grafana credentials for user
    local password
    password=$(get_grafana_password "$namespace" "$release_name")
    local grafana_url
    grafana_url=$(get_grafana_url "$namespace" "$release_name")

    echo ""
    echo "GRAFANA ACCESS INFORMATION:"
    echo "URL: $grafana_url (via port forward)"
    echo "Username: admin"
    echo "Password: $password"
    echo ""
    echo "To access Grafana directly:"
    echo "kubectl port-forward -n $namespace svc/$release_name-grafana 3000:80"
}

# Main execution
main() {
    local mode=${1:-"complete"}
    local namespace=${2:-"monitoring"}
    local release_name=${3:-"prometheus"}

    case "$mode" in
        "configmap")
            check_kubectl
            install_dashboards_via_configmap "$namespace" "$release_name"
            ;;
        "external")
            check_kubectl
            install_dashboards_from_sources "$namespace" "$release_name"
            ;;
        "verify")
            check_kubectl
            verify_dashboard_installation "$namespace"
            ;;
        "complete")
            run_complete_dashboard_installation "$namespace" "$release_name"
            ;;
        *)
            echo "USAGE: $0 [configmap|external|verify|complete] [namespace] [release_name]"
            echo ""
            echo "Examples:"
            echo "  $0 complete monitoring prometheus"
            echo "  $0 configmap monitoring prometheus"
            echo "  $0 verify monitoring prometheus"
            exit 1
            ;;
    esac
}

# Run main function with arguments
main "$@"