#!/bin/bash
"""
Argo CD application deleter for argocd-app-deployment skill

This script deletes Argo CD Application CRs.
"""

set -e  # Exit on any error

# Function to check if argocd CLI is available
check_argocd_cli() {
    if ! command -v argocd &> /dev/null; then
        echo "FAILURE: argocd CLI is not installed or not in PATH"
        echo "Please install argocd CLI from: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
        exit 1
    fi
}

# Function to delete Argo CD application
delete_application() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}
    local cascade=${3:-"true"}  # Whether to delete deployed resources as well

    echo "Deleting Argo CD Application: $app_name"

    # Check if the application exists
    if ! kubectl get application "$app_name" -n "$argocd_namespace" &> /dev/null; then
        echo "ERROR: Application $app_name not found in namespace $argocd_namespace"
        exit 1
    fi

    # Get current sync status
    local sync_status
    if command -v argocd &> /dev/null; then
        sync_status=$(argocd app get "$app_name" --insecure 2>/dev/null | grep "Sync Status" | awk '{print $NF}' 2>/dev/null)
    else
        sync_status=$(kubectl get application "$app_name" -n "$argocd_namespace" -o jsonpath='{.status.sync.status}' 2>/dev/null)
    fi

    echo "Current sync status: $sync_status"

    # Prepare delete command
    local delete_cmd
    if [ "$cascade" = "true" ]; then
        # Delete with cascade (also delete deployed resources)
        delete_cmd="kubectl patch application $app_name -n $argocd_namespace -p '{\"metadata\":{\"finalizers\":[]}}' --type merge; kubectl delete application $app_name -n $argocd_namespace"
    else
        # Delete without cascade (keep deployed resources)
        delete_cmd="kubectl delete application $app_name -n $argocd_namespace"
    fi

    echo "Executing: $delete_cmd"
    eval $delete_cmd

    echo "SUCCESS: Application $app_name deleted"
}

# Function to delete application with Argo CD CLI
delete_application_cli() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}
    local cascade=${3:-"background"}  # background, foreground, or orphan

    echo "Deleting Argo CD Application using CLI: $app_name"

    # Check if the application exists
    if ! argocd app get "$app_name" --insecure &> /dev/null; then
        echo "ERROR: Application $app_name not found"
        exit 1
    fi

    # Delete the application
    argocd app delete "$app_name" --insecure --cascade="$cascade"

    echo "SUCCESS: Application $app_name deleted via CLI"
}

# Function to check if application exists
check_application_exists() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}

    if kubectl get application "$app_name" -n "$argocd_namespace" &> /dev/null; then
        echo "INFO: Application $app_name exists in namespace $argocd_namespace"
        return 0
    else
        echo "INFO: Application $app_name does not exist in namespace $argocd_namespace"
        return 1
    fi
}

# Function to get application status before deletion
get_status_before_delete() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}

    echo "Getting status for $app_name before deletion..."

    if command -v argocd &> /dev/null; then
        argocd app get "$app_name" --insecure
    else
        kubectl get application "$app_name" -n "$argocd_namespace" -o yaml
    fi
}

# Function to delete application with confirmation
delete_application_with_confirmation() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}
    local cascade=${3:-"true"}

    echo "Preparing to delete application: $app_name"
    echo "Namespace: $argocd_namespace"
    echo "Cascade delete: $cascade"
    echo ""

    get_status_before_delete "$app_name" "$argocd_namespace"

    echo ""
    read -p "Are you sure you want to delete application $app_name? (yes/no): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        delete_application "$app_name" "$argocd_namespace" "$cascade"
    else
        echo "Deletion cancelled."
        exit 0
    fi
}

# Main execution
main() {
    local mode=${1:-"delete"}
    local app_name=${2}
    local param1=${3}
    local param2=${4}
    local param3=${5}

    case "$mode" in
        "delete")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for delete mode"
                exit 1
            fi
            check_argocd_cli
            delete_application "$app_name" "$param1" "$param2"
            ;;
        "delete-cli")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for delete-cli mode"
                exit 1
            fi
            check_argocd_cli
            delete_application_cli "$app_name" "$param1" "$param2"
            ;;
        "check")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for check mode"
                exit 1
            fi
            check_application_exists "$app_name" "$param1"
            ;;
        "status")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for status mode"
                exit 1
            fi
            get_status_before_delete "$app_name" "$param1"
            ;;
        "delete-confirm")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for delete-confirm mode"
                exit 1
            fi
            check_argocd_cli
            delete_application_with_confirmation "$app_name" "$param1" "$param2"
            ;;
        *)
            echo "USAGE: $0 [delete|delete-cli|check|status|delete-confirm] [app_name] [params...]"
            echo ""
            echo "Examples:"
            echo "  $0 delete my-app argocd true"  # Delete app with cascade
            echo "  $0 delete-cli my-app argocd background"  # Delete via CLI
            echo "  $0 check my-app argocd"  # Check if app exists
            echo "  $0 delete-confirm my-app argocd true"  # Delete with confirmation
            exit 1
            ;;
    esac
}

# Run main function with arguments
main "$@"