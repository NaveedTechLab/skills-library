# Argo CD GitOps Best Practices

## GitOps Fundamentals

### Repository Structure
- Use a dedicated Git repository for infrastructure manifests
- Separate application configurations from infrastructure
- Implement proper branching strategy (main, develop, feature branches)
- Use tags for versioned releases

### Commit Practices
- Atomic commits for each configuration change
- Clear and descriptive commit messages
- Signed commits for security verification
- Consistent naming conventions

## Argo CD Application Design

### Basic Application Specification
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/your-app.git
    targetRevision: HEAD
    path: kubernetes/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    automated:
      enabled: true
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

### Advanced Application Patterns

#### Multiple Sources (Argo CD 2.3+)
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app-with-crds
spec:
  project: default
  sources:
  - repoURL: https://github.com/your-org/your-app.git
    targetRevision: HEAD
    path: manifests
  - repoURL: https://github.com/argoproj/argo-cd.git
    targetRevision: HEAD
    path: manifests/crds
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy: ...
```

#### Helm Chart Application
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-helm-app
spec:
  project: default
  source:
    repoURL: https://charts.helm.sh/stable
    chart: nginx-ingress
    targetRevision: 1.41.3
    helm:
      parameters:
      - name: controller.service.type
        value: LoadBalancer
  destination:
    server: https://kubernetes.default.svc
    namespace: nginx-ingress
  syncPolicy: ...
```

## GitOps Workflow Patterns

### Environment Promotion
- Separate directories for each environment
- Use overlays for environment-specific configurations
- Automated promotion through pull requests
- Manual approval gates for production

### Branch Strategy
- main branch for production
- develop branch for staging
- feature branches for development
- Tag releases for version tracking

### Sync Policies

#### Automated Sync with Pruning
```yaml
syncPolicy:
  automated:
    enabled: true
    prune: true
    selfHeal: true
  syncOptions:
  - CreateNamespace=true
  - ApplyOutOfSyncOnly=true
  - PruneLast=true
```

#### Manual Sync for Critical Systems
```yaml
syncPolicy:
  automated:
    enabled: false
  syncOptions:
  - CreateNamespace=true
```

## Security Best Practices

### RBAC Configuration
- Least-privilege principle for Argo CD accounts
- Separate projects for different teams
- Repository and cluster access controls
- Automated policy enforcement

### Repository Security
- Private repositories with access controls
- SSH keys for repository access
- GPG signing for commits
- Image signature verification

### Sync Options Security
```yaml
syncOptions:
- CreateNamespace=true
- ApplyOutOfSyncOnly=true
- PruneLast=true
- RespectIgnoreDifferences=true
- Validate=false  # Only for trusted sources
```

## Health Assessment

### Built-in Health Checks
- Default health assessments for standard K8s resources
- Custom health checks for CRDs
- Health comparison exclusions for expected differences

### Custom Health Check Example
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
spec:
  source:
    repoURL: https://github.com/your-org/your-app.git
    path: .
    targetRevision: HEAD
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
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
```

## Monitoring and Observability

### Argo CD Metrics
- Monitor application sync status
- Track deployment frequency and lead time
- Alert on sync failures
- Monitor resource health

### Logging
- Centralized logs for sync operations
- Audit logs for configuration changes
- Health check logs
- Performance metrics

## Troubleshooting Common Issues

### Sync Failures
- Check repository access and credentials
- Verify manifest syntax and validity
- Review RBAC permissions
- Check cluster connectivity

### Health Assessment Issues
- Validate health check configurations
- Check for expected status differences
- Review custom health check logic
- Verify resource dependencies

### Performance Issues
- Optimize repository structure
- Limit revision history
- Use appropriate sync intervals
- Monitor resource consumption

## Application Lifecycle Management

### Creation
- Template-based application creation
- Standardized naming conventions
- Consistent sync policies
- Automated testing

### Updates
- Git-based change management
- Automated sync triggers
- Rollback procedures
- Change approval workflows

### Deletion
- Cascading deletion configuration
- Finalizer management
- Cleanup procedures
- Resource orphan detection

## Common Anti-Patterns to Avoid

1. **Direct K8s Changes**: Never modify resources directly in K8s cluster
2. **Manual Interventions**: Avoid manual fixes that bypass GitOps
3. **Complex Sync Options**: Don't overcomplicate sync options
4. **Inconsistent Naming**: Use consistent naming conventions
5. **Large Applications**: Split large applications into smaller ones
6. **Missing Health Checks**: Always configure appropriate health checks
7. **No Sync Policies**: Define clear sync policies for each application
8. **Unsecured Repositories**: Always secure Git repositories

## Configuration Templates

### Production Application Template
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: production-app
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:
  project: production
  source:
    repoURL: https://github.com/your-org/your-app.git
    targetRevision: HEAD
    path: kubernetes/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: production-app
  syncPolicy:
    automated:
      enabled: true
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
    - ApplyOutOfSyncOnly=true
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
  - group: ""
    kind: Service
    jsonPointers:
    - /spec/clusterIP
```

### Staging Application Template
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: staging-app
  namespace: argocd
spec:
  project: staging
  source:
    repoURL: https://github.com/your-org/your-app.git
    targetRevision: HEAD
    path: kubernetes/overlays/staging
  destination:
    server: https://kubernetes.default.svc
    namespace: staging-app
  syncPolicy:
    automated:
      enabled: true
      prune: true
      selfHeal: false  # Disable self-heal for staging
    syncOptions:
    - CreateNamespace=true
  revisionHistoryLimit: 5
```

Following these best practices ensures robust, secure, and maintainable GitOps workflows with Argo CD.