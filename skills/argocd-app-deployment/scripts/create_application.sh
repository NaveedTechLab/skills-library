#!/bin/bash
"""
Argo CD application creator for argocd-app-deployment skill

This script creates Argo CD Application CRs for GitOps deployments.
"""

set -e  # Exit on any error

# Function to check if argocd CLI is available
check_argocd_cli() {
    if ! command -v argocd &> /dev/null; then
        echo "FAILURE: argocd CLI is not installed or not in PATH"
        echo "Please install argocd CLI from: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
        exit 1
    fi

    # Check if argocd server is accessible
    if ! argocd version --client &> /dev/null; then
        echo "WARNING: Cannot connect to Argo CD server, but client is available"
    fi
}

# Function to create Argo CD Application manifest
create_application_manifest() {
    local app_name=${1}
    local repo_url=${2}
    local path=${3:-"."}
    local target_namespace=${4:-"default"}
    local target_server=${5:-"https://kubernetes.default.svc"}
    local auto_sync=${6:-"false"}
    local prune=${7:-"true"}
    local self_heal=${8:-"false"}
    local output_file=${9:-"application.yaml"}

    echo "Creating Argo CD Application manifest for $app_name..."

    cat <<EOF > "$output_file"
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: $app_name
  namespace: argocd  # Argo CD instance namespace
spec:
  project: default
  source:
    repoURL: $repo_url
    path: $path
    targetRevision: HEAD
  destination:
    server: $target_server
    namespace: $target_namespace
  syncPolicy:
    automated:
      enabled: $auto_sync
      prune: $prune
      selfHeal: $self_heal
    syncOptions:
    - CreateNamespace=true
    - ApplyOutOfSyncOnly=true
  revisionHistoryLimit: 10
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /status
  - group: argoproj.io
    kind: Application
    jsonPointers:
    - /status
EOF

    echo "SUCCESS: Argo CD Application manifest created at $output_file"
}

# Function to create application with advanced options
create_advanced_application() {
    local app_name=${1}
    local repo_url=${2}
    local path=${3:-"."}
    local target_namespace=${4:-"default"}
    local target_server=${5:-"https://kubernetes.default.svc"}
    local auto_sync=${6:-"false"}
    local prune=${7:-"true"}
    local self_heal=${8:-"false"}
    local project=${9:-"default"}
    local revision=${10:-"HEAD"}
    local output_file=${11:-"application-advanced.yaml"}

    echo "Creating advanced Argo CD Application manifest for $app_name..."

    cat <<EOF > "$output_file"
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: $app_name
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:
  project: $project
  source:
    repoURL: $repo_url
    path: $path
    targetRevision: $revision
    helm: {}
    kustomize: {}
    directory: {}
  destination:
    server: $target_server
    namespace: $target_namespace
  syncPolicy:
    automated:
      enabled: $auto_sync
      prune: $prune
      selfHeal: $self_heal
    syncOptions:
    - CreateNamespace=true
    - ApplyOutOfSyncOnly=true
    - Validate=false
    - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  revisionHistoryLimit: 10
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /status
  - group: argoproj.io
    kind: Application
    jsonPointers:
    - /status
  - group: ""
    kind: Service
    jsonPointers:
    - /spec/clusterIP
    - /spec/loadBalancerIP
  info:
  - name: Documentation
    value: 'https://argoproj.github.io/argo-cd/'
  - name: Support
    value: 'https://argoproj.github.io/argo-cd/support/'
EOF

    echo "SUCCESS: Advanced Argo CD Application manifest created at $output_file"
}

# Function to create application with multiple sources (for Argo CD 2.3+)
create_multi_source_application() {
    local app_name=${1}
    local repo_url=${2}
    local path=${3:-"."}
    local target_namespace=${4:-"default"}
    local target_server=${5:-"https://kubernetes.default.svc"}
    local output_file=${6:-"application-multi-source.yaml"}

    echo "Creating multi-source Argo CD Application manifest for $app_name..."

    cat <<EOF > "$output_file"
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: $app_name
  namespace: argocd
spec:
  project: default
  sources:
  - repoURL: $repo_url
    path: $path
    targetRevision: HEAD
  - repoURL: https://github.com/argoproj/argo-cd.git
    path: manifests/crds
    targetRevision: HEAD
  destination:
    server: $target_server
    namespace: $target_namespace
  syncPolicy:
    automated:
      enabled: true
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
  revisionHistoryLimit: 10
EOF

    echo "SUCCESS: Multi-source Argo CD Application manifest created at $output_file"
}

# Function to apply the application to Argo CD
apply_application() {
    local app_manifest=${1}
    local argocd_namespace=${2:-"argocd"}

    echo "Applying Argo CD Application from $app_manifest..."

    if [ ! -f "$app_manifest" ]; then
        echo "ERROR: Application manifest file $app_manifest does not exist"
        exit 1
    fi

    kubectl apply -f "$app_manifest" -n "$argocd_namespace"

    echo "SUCCESS: Argo CD Application applied"
}

# Function to create and apply application in one step
create_and_apply_application() {
    local app_name=${1}
    local repo_url=${2}
    local path=${3:-"."}
    local target_namespace=${4:-"default"}
    local target_server=${5:-"https://kubernetes.default.svc"}
    local auto_sync=${6:-"false"}
    local prune=${7:-"true"}
    local self_heal=${8:-"false"}
    local argocd_namespace=${9:-"argocd"}

    echo "Creating and applying Argo CD Application: $app_name"

    # Create temporary manifest file
    local temp_manifest="/tmp/application_${app_name}_$(date +%s).yaml"

    create_application_manifest "$app_name" "$repo_url" "$path" "$target_namespace" "$target_server" "$auto_sync" "$prune" "$self_heal" "$temp_manifest"

    # Apply the application
    apply_application "$temp_manifest" "$argocd_namespace"

    # Clean up temporary file
    rm "$temp_manifest"

    echo "SUCCESS: Argo CD Application $app_name created and applied"
}

# Main execution
main() {
    local mode=${1:-"basic"}
    local app_name=${2}
    local repo_url=${3}
    local param1=${4}
    local param2=${5}
    local param3=${6}
    local param4=${7}
    local param5=${8}
    local param6=${9}
    local param7=${10}
    local param8=${11}

    case "$mode" in
        "basic")
            if [ -z "$app_name" ] || [ -z "$repo_url" ]; then
                echo "ERROR: app_name and repo_url are required for basic mode"
                exit 1
            fi
            create_application_manifest "$app_name" "$repo_url" "$param1" "$param2" "$param3" "$param4" "$param5" "$param6" "$param7"
            ;;
        "advanced")
            if [ -z "$app_name" ] || [ -z "$repo_url" ]; then
                echo "ERROR: app_name and repo_url are required for advanced mode"
                exit 1
            fi
            create_advanced_application "$app_name" "$repo_url" "$param1" "$param2" "$param3" "$param4" "$param5" "$param6" "$param7" "$param8" "${12}"
            ;;
        "multi-source")
            if [ -z "$app_name" ] || [ -z "$repo_url" ]; then
                echo "ERROR: app_name and repo_url are required for multi-source mode"
                exit 1
            fi
            create_multi_source_application "$app_name" "$repo_url" "$param1" "$param2" "$param3" "$param4"
            ;;
        "apply")
            if [ -z "$param1" ]; then
                echo "ERROR: manifest file is required for apply mode"
                exit 1
            fi
            check_argocd_cli
            apply_application "$param1" "$param2"
            ;;
        "create-and-apply")
            if [ -z "$app_name" ] || [ -z "$repo_url" ]; then
                echo "ERROR: app_name and repo_url are required for create-and-apply mode"
                exit 1
            fi
            check_argocd_cli
            create_and_apply_application "$app_name" "$repo_url" "$param1" "$param2" "$param3" "$param4" "$param5" "$param6" "$param7"
            ;;
        *)
            echo "USAGE: $0 [basic|advanced|multi-source|apply|create-and-apply] [app_name] [repo_url] [params...]"
            echo ""
            echo "Examples:"
            echo "  $0 basic my-app https://github.com/org/repo.git . default https://kubernetes.default.svc true true false application.yaml"
            echo "  $0 create-and-apply my-app https://github.com/org/repo.git . default https://kubernetes.default.svc true true true argocd"
            echo "  $0 apply application.yaml argocd"
            exit 1
            ;;
    esac
}

# Run main function with arguments
main "$@"