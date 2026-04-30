# CI/CD Pipelines for Kubernetes

## Overview

This document provides comprehensive guidance on setting up CI/CD pipelines for the CRM platform deployed on Kubernetes. It covers various CI/CD tools, pipeline patterns, security considerations, and best practices.

## GitHub Actions Pipeline

### Complete GitHub Actions Pipeline
```yaml
# .github/workflows/deploy.yml
name: Build, Test & Deploy

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  security-scan:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
    - uses: actions/checkout@v3

    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        format: 'sarif'
        output: 'trivy-results.sarif'
        severity: 'CRITICAL,HIGH'

    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      if: always()
      with:
        sarif_file: 'trivy-results.sarif'

  build-and-test:
    runs-on: ubuntu-latest
    needs: security-scan
    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata for Docker
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}

    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Run unit tests
      run: |
        docker run --rm \
          -e ENVIRONMENT=test \
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
          python -m pytest tests/unit/

    - name: Run integration tests
      run: |
        docker run --rm \
          -e ENVIRONMENT=test \
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
          python -m pytest tests/integration/

  deploy-staging:
    runs-on: ubuntu-latest
    needs: build-and-test
    if: github.ref == 'refs/heads/develop'
    environment: staging
    steps:
    - uses: actions/checkout@v3

    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'latest'

    - name: Set up Helm
      uses: azure/setup-helm@v3
      with:
        version: 'latest'

    - name: Set up Kustomize
      run: |
        wget -O kustomize.tar.gz https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v5.0.1/kustomize_v5.0.1_linux_amd64.tar.gz
        tar -xzf kustomize.tar.gz
        chmod u+x kustomize
        sudo mv kustomize /usr/local/bin/kustomize

    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        kubeconfig: ${{ secrets.KUBE_CONFIG_STAGING }}

    - name: Deploy to staging using Kustomize
      run: |
        kustomize edit set image ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
        kubectl apply -k overlays/staging/

    - name: Run smoke tests
      run: |
        # Wait for deployment to be ready
        kubectl wait --for=condition=ready pod -l app=crm-app --timeout=300s
        # Run basic health checks
        kubectl port-forward svc/crm-app-service 8080:80 &
        sleep 10
        curl -f http://localhost:8080/health

  deploy-production:
    runs-on: ubuntu-latest
    needs: build-and-test
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
    - uses: actions/checkout@v3

    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'latest'

    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        kubeconfig: ${{ secrets.KUBE_CONFIG_PRODUCTION }}

    - name: Deploy to production
      run: |
        # Create deployment with new image
        kubectl set image deployment/crm-app app=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} -n crm-platform
        kubectl rollout status deployment/crm-app -n crm-platform --timeout=300s

    - name: Run production smoke tests
      run: |
        # Wait for deployment to be ready
        kubectl wait --for=condition=ready pod -l app=crm-app -n crm-platform --timeout=300s
        # Run basic health checks
        export POD_NAME=$(kubectl get pods -l app=crm-app -n crm-platform -o jsonpath="{.items[0].metadata.name}")
        kubectl port-forward -n crm-platform pod/$POD_NAME 8080:8000 &
        sleep 10
        curl -f http://localhost:8080/health

  notify:
    runs-on: ubuntu-latest
    needs: [deploy-staging, deploy-production]
    if: always()
    steps:
    - name: Slack notification
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ needs.deploy-staging.result || needs.deploy-production.result }}
        channel: '#deployments'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        username: GitHub Actions
```

### Advanced GitHub Actions with Matrix Builds
```yaml
# .github/workflows/matrix-build.yml
name: Matrix Build & Test

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test-matrix:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
        os: [ubuntu-latest, windows-latest, macos-latest]
      fail-fast: false
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest tests/ --cov=app --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  build-matrix:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        include:
        - os: ubuntu-latest
          platform: linux/amd64
        - os: windows-latest
          platform: windows/amd64
        - os: macos-latest
          platform: darwin/amd64
    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=sha,prefix=${{ matrix.os }}-

    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        platforms: ${{ matrix.platform }}
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

## GitLab CI/CD Pipeline

### GitLab CI Configuration
```yaml
# .gitlab-ci.yml
stages:
  - security
  - build
  - test
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"
  CONTAINER_IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

.docker-login: &docker-login
  before_script:
    - echo $CI_REGISTRY_PASSWORD | docker login -u $CI_REGISTRY_USER $CI_REGISTRY --password-stdin

.security-template: &security-template
  stage: security
  image: docker:stable
  services:
    - docker:dind
  script:
    - echo "Running security scans..."
    - docker run --rm -v $(pwd):/app aquasec/trivy:latest filesystem --security-checks vuln,config,secret /app

build-image:
  <<: *docker-login
  stage: build
  image: docker:stable
  services:
    - docker:dind
  script:
    - echo "Building Docker image..."
    - docker build -t $CONTAINER_IMAGE .
    - docker push $CONTAINER_IMAGE
  only:
    - main
    - develop

unit-tests:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest tests/unit/ --cov=app
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      junit: test-results.xml

integration-tests:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest tests/integration/ --cov=app
  dependencies:
    - build-image
  artifacts:
    reports:
      junit: integration-results.xml

security-scan:
  <<: *security-template
  only:
    - main
    - develop

deploy-staging:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl set image deployment/crm-app app=$CONTAINER_IMAGE -n crm-platform
    - kubectl rollout status deployment/crm-app -n crm-platform --timeout=300s
  environment:
    name: staging
    url: https://staging.crm.example.com
  only:
    - develop

deploy-production:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl set image deployment/crm-app app=$CONTAINER_IMAGE -n crm-platform
    - kubectl rollout status deployment/crm-app -n crm-platform --timeout=300s
  environment:
    name: production
    url: https://crm.example.com
  when: manual
  only:
    - main
```

## Jenkins Pipeline

### Jenkinsfile for Kubernetes Deployment
```groovy
// Jenkinsfile
pipeline {
    agent {
        kubernetes {
            yaml """
                apiVersion: v1
                kind: Pod
                spec:
                  containers:
                  - name: docker
                    image: docker:latest
                    command:
                    - cat
                    tty: true
                    volumeMounts:
                    - mountPath: /var/run/docker.sock
                      name: docker-sock
                  volumes:
                  - name: docker-sock
                    hostPath:
                      path: /var/run/docker.sock
                      type: Socket
            """
        }
    }

    environment {
        REGISTRY = 'ghcr.io'
        IMAGE_NAME = 'myorg/crm-app'
        NAMESPACE = 'crm-platform'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Security Scan') {
            steps {
                container('docker') {
                    sh '''
                        docker run --rm -v $(pwd):/app aquasec/trivy:latest filesystem --security-checks vuln,config,secret /app
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                container('docker') {
                    withCredentials([usernamePassword(credentialsId: 'docker-registry-creds', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                        sh '''
                            echo $PASSWORD | docker login $REGISTRY -u $USERNAME --password-stdin
                            docker build -t $REGISTRY/$IMAGE_NAME:$BUILD_NUMBER .
                            docker push $REGISTRY/$IMAGE_NAME:$BUILD_NUMBER
                        '''
                    }
                }
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    docker run --rm $REGISTRY/$IMAGE_NAME:$BUILD_NUMBER python -m pytest tests/unit/
                '''
            }
        }

        stage('Integration Tests') {
            steps {
                sh '''
                    docker run --rm $REGISTRY/$IMAGE_NAME:$BUILD_NUMBER python -m pytest tests/integration/
                '''
            }
        }

        stage('Deploy to Staging') {
            when {
                branch 'develop'
            }
            steps {
                withKubeConfig([credentialsId: 'kubeconfig-staging']) {
                    sh '''
                        kubectl set image deployment/crm-app app=$REGISTRY/$IMAGE_NAME:$BUILD_NUMBER -n $NAMESPACE
                        kubectl rollout status deployment/crm-app -n $NAMESPACE --timeout=300s
                    '''
                }
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                input message: 'Deploy to production?', ok: 'Deploy'
                withKubeConfig([credentialsId: 'kubeconfig-production']) {
                    sh '''
                        kubectl set image deployment/crm-app app=$REGISTRY/$IMAGE_NAME:$BUILD_NUMBER -n $NAMESPACE
                        kubectl rollout status deployment/crm-app -n $NAMESPACE --timeout=300s
                    '''
                }
            }
        }
    }

    post {
        always {
            sh '''
                docker rmi $REGISTRY/$IMAGE_NAME:$BUILD_NUMBER || true
            '''
        }
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
}
```

## ArgoCD Pipeline

### ArgoCD Application Configuration
```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: crm-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/crm-platform.git
    targetRevision: HEAD
    path: k8s/overlays/production
    kustomize:
      images:
      - crm-app=ghcr.io/your-org/crm-app:latest
  destination:
    server: https://kubernetes.default.svc
    namespace: crm-platform
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
    - ApplyOutOfSyncOnly=true
---
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: crm-project
  namespace: argocd
spec:
  destinations:
  - namespace: crm-platform
    server: https://kubernetes.default.svc
  sourceRepos:
  - https://github.com/your-org/crm-platform.git
  roles:
  - name: developer
    policies:
    - p, proj:crm-project:developer, applications, *, crm-project/*, allow
    groups:
    - developers
```

### ArgoCD Sync Wave Configuration
```yaml
# argocd-sync-waves.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: crm-full-stack
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/crm-platform.git
    targetRevision: HEAD
    path: k8s/apps
  destination:
    server: https://kubernetes.default.svc
    namespace: crm-platform
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
---
# crm-database.yaml with sync wave annotation
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: crm-db
  namespace: crm-platform
  annotations:
    argocd.argoproj.io/sync-wave: "-5"  # Deploy first
spec:
  # ... database configuration
---
# crm-app.yaml with sync wave annotation
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-app
  namespace: crm-platform
  annotations:
    argocd.argoproj.io/sync-wave: "0"  # Deploy after dependencies
spec:
  # ... app configuration
---
# crm-hpa.yaml with sync wave annotation
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-app-hpa
  namespace: crm-platform
  annotations:
    argocd.argoproj.io/sync-wave: "5"  # Deploy after app
spec:
  # ... HPA configuration
```

## Tekton Pipeline

### Tekton Pipeline Definition
```yaml
# tekton-pipeline.yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: crm-deployment-pipeline
spec:
  params:
  - name: image-tag
    type: string
    default: latest
  - name: git-url
    type: string
  - name: git-revision
    type: string
    default: main

  workspaces:
  - name: shared-workspace

  tasks:
  - name: fetch-source
    taskRef:
      name: git-clone
    workspaces:
    - name: output
      workspace: shared-workspace
    params:
    - name: url
      value: $(params.git-url)
    - name: revision
      value: $(params.git-revision)

  - name: security-scan
    taskRef:
      name: trivy-scan
    runAfter:
    - fetch-source
    workspaces:
    - name: source
      workspace: shared-workspace
    params:
    - name: image
      value: $(params.image-tag)

  - name: build-image
    taskRef:
      name: buildah
    runAfter:
    - security-scan
    workspaces:
    - name: source
      workspace: shared-workspace
    params:
    - name: IMAGE
      value: $(params.image-tag)

  - name: unit-tests
    taskRef:
      name: run-tests
    runAfter:
    - build-image
    workspaces:
    - name: source
      workspace: shared-workspace
    params:
    - name: image
      value: $(params.image-tag)

  - name: deploy-staging
    taskRef:
      name: kubectl-apply
    runAfter:
    - unit-tests
    workspaces:
    - name: manifest-dir
      workspace: shared-workspace
    params:
    - name: manifest_dir
      value: k8s/overlays/staging
    - name: kubectl_args
      value: "-n crm-platform-staging"
```

### Tekton Task Definitions
```yaml
# tekton-tasks.yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: trivy-scan
spec:
  workspaces:
  - name: source
  params:
  - name: image
    type: string
  steps:
  - name: scan
    image: aquasec/trivy:latest
    workingDir: $(workspaces.source.path)
    script: |
      trivy image --security-checks vuln,config,secret $(params.image)
---
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: run-tests
spec:
  workspaces:
  - name: source
  params:
  - name: image
    type: string
  steps:
  - name: run-unit-tests
    image: $(params.image)
    script: |
      python -m pytest tests/unit/
  - name: run-integration-tests
    image: $(params.image)
    script: |
      python -m pytest tests/integration/
---
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: kubectl-apply
spec:
  workspaces:
  - name: manifest-dir
  params:
  - name: manifest_dir
    type: string
    default: .
  - name: kubectl_args
    type: string
    default: ""
  steps:
  - name: kubectl-apply
    image: bitnami/kubectl:latest
    workingDir: $(workspaces.manifest-dir.path)/$(params.manifest_dir)
    script: |
      kubectl apply $(params.kubectl_args) -f .
```

## Pipeline Security

### Security Scanning Pipeline
```yaml
# security-pipeline.yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: security-scanning-pipeline
spec:
  params:
  - name: git-url
    type: string
  - name: git-revision
    type: string
    default: main
  - name: image-name
    type: string

  workspaces:
  - name: shared-workspace

  tasks:
  - name: fetch-source
    taskRef:
      name: git-clone
    workspaces:
    - name: output
      workspace: shared-workspace
    params:
    - name: url
      value: $(params.git-url)
    - name: revision
      value: $(params.git-revision)

  - name: trivy-scan-source
    taskRef:
      name: trivy-scan
    runAfter:
    - fetch-source
    workspaces:
    - name: source
      workspace: shared-workspace
    params:
    - name: target
      value: $(workspaces.source.path)

  - name: build-image
    taskRef:
      name: buildah
    runAfter:
    - trivy-scan-source
    workspaces:
    - name: source
      workspace: shared-workspace
    params:
    - name: IMAGE
      value: $(params.image-name):$(params.git-revision)

  - name: trivy-scan-image
    taskRef:
      name: trivy-scan
    runAfter:
    - build-image
    params:
    - name: target
      value: $(params.image-name):$(params.git-revision)

  - name: snyk-scan
    taskRef:
      name: snyk-scan
    runAfter:
    - trivy-scan-image
    workspaces:
    - name: source
      workspace: shared-workspace
    params:
    - name: image
      value: $(params.image-name):$(params.git-revision)
```

## Pipeline Best Practices

### Multi-Environment Pipeline Template
```yaml
# multi-env-pipeline.yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: multi-environment-pipeline
  labels:
    environment: multi-env
spec:
  params:
  - name: environment
    type: string
    description: Target environment (dev, staging, prod)
  - name: git-url
    type: string
  - name: git-revision
    type: string
    default: main
  - name: image-registry
    type: string
    default: ghcr.io

  workspaces:
  - name: shared-workspace

  tasks:
  - name: fetch-source
    taskRef:
      name: git-clone
    workspaces:
    - name: output
      workspace: shared-workspace
    params:
    - name: url
      value: $(params.git-url)
    - name: revision
      value: $(params.git-revision)

  - name: run-tests
    taskRef:
      name: run-tests
    runAfter:
    - fetch-source
    workspaces:
    - name: source
      workspace: shared-workspace

  - name: build-and-push
    taskRef:
      name: buildah
    runAfter:
    - run-tests
    workspaces:
    - name: source
      workspace: shared-workspace
    params:
    - name: IMAGE
      value: $(params.image-registry)/$(params.git-url):$(params.git-revision)-$(params.environment)

  - name: deploy
    taskRef:
      name: deploy-to-env
    runAfter:
    - build-and-push
    params:
    - name: environment
      value: $(params.environment)
    - name: image
      value: $(params.image-registry)/$(params.git-url):$(params.git-revision)-$(params.environment)

---
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: deploy-to-env
spec:
  params:
  - name: environment
    type: string
  - name: image
    type: string
  steps:
  - name: deploy
    image: bitnami/kubectl:latest
    script: |
      # Set environment-specific configurations
      case $(params.environment) in
        "dev")
          NAMESPACE="crm-dev"
          ;;
        "staging")
          NAMESPACE="crm-staging"
          ;;
        "prod")
          NAMESPACE="crm-platform"
          ;;
        *)
          echo "Unknown environment: $(params.environment)"
          exit 1
          ;;
      esac

      # Deploy to the appropriate namespace
      kubectl set image deployment/crm-app app=$(params.image) -n $NAMESPACE
      kubectl rollout status deployment/crm-app -n $NAMESPACE --timeout=300s

      # Verify deployment
      kubectl get pods -n $NAMESPACE
```

This comprehensive CI/CD pipeline guide provides all the necessary configurations for implementing robust CI/CD processes for the CRM platform on Kubernetes.