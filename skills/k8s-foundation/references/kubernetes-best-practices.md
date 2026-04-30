# Kubernetes Best Practices for Foundation Setup

## Cluster Readiness Criteria

### Pre-deployment Checks
- Verify cluster connectivity with `kubectl cluster-info`
- Ensure all nodes are in "Ready" state
- Check that system pods are running properly
- Validate available resources (CPU, memory, storage)
- Confirm required permissions for operations

### Health Indicators
- All control plane components should be healthy
- Node disk space and memory should be sufficient
- Network policies should allow necessary traffic
- Pod security policies should be properly configured

## Foundational Components Priority

### Critical Components (Deploy First)
1. **CNI Plugin** - Network connectivity
2. **Metrics Server** - Resource metrics
3. **Ingress Controller** - External access
4. **Storage Classes** - Persistent storage

### Important Components (Deploy Second)
1. **Cert Manager** - TLS certificates
2. **Monitoring Stack** - Prometheus/Grafana
3. **Logging Stack** - Loki/Promtail or ELK
4. **Secret Management** - External Secrets or Vault

### Optional Components (Deploy as Needed)
1. **Service Mesh** - Istio, Linkerd
2. **Policy Engine** - OPA Gatekeeper
3. **Backup Solutions** - Velero
4. **Autoscaling** - Cluster Autoscaler

## Helm Chart Configuration Best Practices

### Values Configuration
- Use dedicated values files for each environment
- Separate sensitive values using sealed secrets or external secret stores
- Enable monitoring and alerting by default
- Configure resource limits and requests appropriately

### Security Considerations
- Always verify chart signatures and provenance
- Scan charts for security vulnerabilities
- Use non-root users where possible
- Enable PSPs or Pod Security Standards
- Limit RBAC permissions to minimum required

## Validation Strategies

### Pre-deployment Validation
- Dry-run installations with `helm install --dry-run`
- Validate YAML manifests with linters
- Check resource conflicts
- Verify namespace existence

### Post-deployment Validation
- Confirm pods are in "Running" state
- Verify services are accessible
- Test basic functionality
- Check logs for errors

## Troubleshooting Common Issues

### Cluster Connectivity
```bash
kubectl cluster-info
kubectl get nodes
kubectl get cs  # For control plane components
```

### Pod Issues
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
kubectl get events -n <namespace>
```

### Helm Issues
```bash
helm list -A
helm status <release-name> -n <namespace>
helm history <release-name> -n <namespace>
```

## Rollback Procedures

Always have rollback plans:
- Maintain backup of previous configurations
- Use Helm's rollback functionality: `helm rollback <release-name> <revision>`
- Test rollback procedures in non-production environments first
- Document manual cleanup steps if needed