#!/bin/bash
"""
GitOps repository setup for argocd-app-deployment skill

This script helps prepare Git repositories for GitOps workflows.
"""

set -e  # Exit on any error

# Function to initialize a Git repository for GitOps
initialize_gitops_repo() {
    local repo_path=${1:-"."}
    local app_name=${2:-"my-app"}
    local environment=${3:-"production"}

    echo "Initializing GitOps repository structure in $repo_path for $app_name..."

    cd "$repo_path"

    # Create the repository if it doesn't exist
    if [ ! -d ".git" ]; then
        git init
        echo "Initialized Git repository"
    fi

    # Create standard GitOps directory structure
    mkdir -p "$environment"
    mkdir -p "$environment/base"
    mkdir -p "$environment/overlays"

    # Create a basic kustomization.yaml in base
    cat <<EOF > "$environment/base/kustomization.yaml"
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- deployment.yaml
- service.yaml
- ingress.yaml

namePrefix: ${app_name}-

commonLabels:
  app: $app_name
  environment: $environment
EOF

    # Create a basic deployment in base
    cat <<EOF > "$environment/base/deployment.yaml"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: $app_name
  template:
    metadata:
      labels:
        app: $app_name
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
EOF

    # Create a basic service in base
    cat <<EOF > "$environment/base/service.yaml"
apiVersion: v1
kind: Service
metadata:
  name: app
spec:
  selector:
    app: $app_name
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
EOF

    # Create a basic ingress in base
    cat <<EOF > "$environment/base/ingress.yaml"
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app
spec:
  rules:
  - host: $app_name.$environment.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app
            port:
              number: 80
EOF

    # Create an overlay directory for the environment
    mkdir -p "$environment/overlays/$environment"

    # Create kustomization for the environment overlay
    cat <<EOF > "$environment/overlays/$environment/kustomization.yaml"
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
- ../../base

patchesStrategicMerge:
- deployment-patch.yaml

images:
- name: nginx
  newName: nginx
  newTag: "1.21"

commonLabels:
  environment: $environment
EOF

    # Create a patch for environment-specific settings
    cat <<EOF > "$environment/overlays/$environment/deployment-patch.yaml"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: app
        resources:
          requests:
            memory: "128Mi"
            cpu: "500m"
          limits:
            memory: "256Mi"
            cpu: "1000m"
EOF

    # Create .gitignore
    cat <<EOF > .gitignore
# Built assets
/dist/
/build/
/out/

# Logs
*.log

# Environment specific
.env*
!.env.example

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
EOF

    # Create README
    cat <<EOF > README.md
# GitOps Repository for $app_name

This repository contains Kubernetes manifests for $app_name deployed using Argo CD GitOps.

## Directory Structure

- \`$environment/base/\`: Base Kubernetes manifests
- \`$environment/overlays/$environment/\`: Environment-specific overlays

## Deploying

To deploy this application using Argo CD, create an Application CR pointing to this repository:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: $app_name-$environment
  namespace: argocd
spec:
  project: default
  source:
    repoURL: <REPO_URL>
    path: $environment/overlays/$environment
    targetRevision: HEAD
  destination:
    server: https://kubernetes.default.svc
    namespace: $app_name
  syncPolicy:
    automated:
      enabled: true
      prune: true
      selfHeal: true
\`\`\`
EOF

    echo "SUCCESS: GitOps repository structure initialized"
    echo "Repository structure:"
    find . -type f -not -path "./.git/*" | sort
}

# Function to add manifests to Git repository
add_manifests_to_repo() {
    local repo_path=${1:-"."}
    local manifests_dir=${2:-"."}
    local environment=${3:-"production"}

    echo "Adding manifests from $manifests_dir to Git repository in $repo_path..."

    cd "$repo_path"

    # Create or update the environment directory
    mkdir -p "$environment/base"

    # Copy manifests to the base directory
    cp -r "$manifests_dir"/* "$environment/base/" 2>/dev/null || echo "No manifests found in $manifests_dir"

    echo "SUCCESS: Manifests added to Git repository"
}

# Function to commit changes to Git repository
commit_changes() {
    local repo_path=${1:-"."}
    local commit_message=${2:-"Add GitOps manifests"}

    echo "Committing changes to Git repository in $repo_path..."

    cd "$repo_path"

    # Add all changes
    git add .

    # Check if there are changes to commit
    if ! git diff --cached --quiet; then
        git commit -m "$commit_message"
        echo "SUCCESS: Changes committed with message: $commit_message"
    else
        echo "INFO: No changes to commit"
    fi
}

# Function to validate GitOps repository structure
validate_gitops_repo() {
    local repo_path=${1:-"."}
    local environment=${2:-"production"}

    echo "Validating GitOps repository structure in $repo_path..."

    cd "$repo_path"

    local is_valid=true

    # Check for required directories
    if [ ! -d "$environment/base" ]; then
        echo "ERROR: $environment/base directory not found"
        is_valid=false
    fi

    if [ ! -d "$environment/overlays" ]; then
        echo "ERROR: $environment/overlays directory not found"
        is_valid=false
    fi

    # Check for required files
    if [ ! -f "$environment/base/kustomization.yaml" ]; then
        echo "ERROR: $environment/base/kustomization.yaml not found"
        is_valid=false
    fi

    if [ ! -f ".gitignore" ]; then
        echo "WARNING: .gitignore file not found"
    fi

    if [ "$is_valid" = true ]; then
        echo "SUCCESS: GitOps repository structure is valid"
        return 0
    else
        echo "FAILURE: GitOps repository structure validation failed"
        return 1
    fi
}

# Function to generate Argo CD Application manifest for this repo
generate_argocd_application() {
    local repo_path=${1:-"."}
    local app_name=${2:-"my-app"}
    local repo_url=${3:-"<REPO_URL>"}
    local environment=${4:-"production"}
    local output_file=${5:-"application.yaml"}

    echo "Generating Argo CD Application manifest for $app_name..."

    cat <<EOF > "$output_file"
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: $app_name-$environment
  namespace: argocd
spec:
  project: default
  source:
    repoURL: $repo_url
    path: $environment/overlays/$environment
    targetRevision: HEAD
  destination:
    server: https://kubernetes.default.svc
    namespace: $app_name
  syncPolicy:
    automated:
      enabled: true
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
    - ApplyOutOfSyncOnly=true
EOF

    echo "SUCCESS: Argo CD Application manifest generated at $output_file"
}

# Function to run complete GitOps setup
run_complete_setup() {
    local repo_path=${1:-"."}
    local app_name=${2:-"my-app"}
    local environment=${3:-"production"}
    local repo_url=${4:-"<REPO_URL>"}

    echo "Starting complete GitOps setup for $app_name in $environment..."

    initialize_gitops_repo "$repo_path" "$app_name" "$environment"
    validate_gitops_repo "$repo_path" "$environment"
    generate_argocd_application "$repo_path" "$app_name" "$repo_url" "$environment" "application-$app_name-$environment.yaml"

    echo ""
    echo "GITOPS SETUP COMPLETE"
    echo "Repository prepared for Argo CD GitOps deployment"
    echo ""
    echo "Next steps:"
    echo "1. Push this repository to your Git provider"
    echo "2. Apply the generated Application manifest to your Argo CD instance"
    echo "3. Monitor the sync in Argo CD UI"
}

# Main execution
main() {
    local mode=${1:-"setup"}
    local param1=${2}
    local param2=${3}
    local param3=${4}
    local param4=${5}
    local param5=${6}

    case "$mode" in
        "init")
            if [ -z "$param1" ] || [ -z "$param2" ]; then
                echo "ERROR: repo_path and app_name are required for init mode"
                exit 1
            fi
            initialize_gitops_repo "$param1" "$param2" "$param3"
            ;;
        "add-manifests")
            if [ -z "$param1" ] || [ -z "$param2" ]; then
                echo "ERROR: repo_path and manifests_dir are required for add-manifests mode"
                exit 1
            fi
            add_manifests_to_repo "$param1" "$param2" "$param3"
            ;;
        "commit")
            if [ -z "$param1" ]; then
                echo "ERROR: repo_path is required for commit mode"
                exit 1
            fi
            commit_changes "$param1" "$param2"
            ;;
        "validate")
            if [ -z "$param1" ]; then
                echo "ERROR: repo_path is required for validate mode"
                exit 1
            fi
            validate_gitops_repo "$param1" "$param2"
            ;;
        "generate-app")
            if [ -z "$param1" ] || [ -z "$param2" ]; then
                echo "ERROR: repo_path and app_name are required for generate-app mode"
                exit 1
            fi
            generate_argocd_application "$param1" "$param2" "$param3" "$param4" "$param5"
            ;;
        "setup")
            run_complete_setup "$param1" "$param2" "$param3" "$param4"
            ;;
        *)
            echo "USAGE: $0 [init|add-manifests|commit|validate|generate-app|setup] [params...]"
            echo ""
            echo "Examples:"
            echo "  $0 init . my-app production"  # Initialize GitOps repo
            echo "  $0 setup . my-app production https://github.com/org/repo.git"  # Complete setup
            echo "  $0 commit . \"Initial commit\""  # Commit changes
            echo "  $0 validate . production"  # Validate repo structure
            exit 1
            ;;
    esac
}

# Run main function with arguments
main "$@"