# Security Best Practices for Kubernetes

## Overview

This document provides comprehensive security best practices for deploying and operating the CRM platform on Kubernetes. It covers cluster security, workload security, network security, and security monitoring.

## Cluster Security

### RBAC Configuration

#### Least Privilege RBAC
```yaml
# rbac-security.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: crm-app-sa
  namespace: crm-platform
  labels:
    security: restricted
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: crm-app-role
  namespace: crm-platform
rules:
# Only grant necessary permissions
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]  # Read-only access
- apiGroups: [""]
  resources: ["pods/exec"]
  verbs: ["create"]  # Only if needed for debugging
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: crm-app-rolebinding
  namespace: crm-platform
subjects:
- kind: ServiceAccount
  name: crm-app-sa
  namespace: crm-platform
roleRef:
  kind: Role
  name: crm-app-role
  apiGroup: rbac.authorization.k8s.io
---
# Cluster-wide role for monitoring (if needed)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: crm-monitoring-role
rules:
- apiGroups: [""]
  resources: ["pods", "nodes", "services"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: crm-monitoring-binding
subjects:
- kind: ServiceAccount
  name: crm-monitoring-sa
  namespace: monitoring
roleRef:
  kind: ClusterRole
  name: crm-monitoring-role
  apiGroup: rbac.authorization.k8s.io
```

#### Namespace Isolation
```yaml
# namespace-isolation.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: crm-platform
  labels:
    name: crm-platform
    security: isolated
  annotations:
    seccomp.security.alpha.kubernetes.io/defaultProfileName: runtime/default
    apparmor.security.beta.kubernetes.io/defaultProfileName: runtime/default
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: crm-app-quota
  namespace: crm-platform
spec:
  hard:
    requests.cpu: "8"
    requests.memory: 16Gi
    limits.cpu: "16"
    limits.memory: 32Gi
    persistentvolumeclaims: "10"
    secrets: "20"
    configmaps: "30"
    services: "20"
    pods: "50"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: crm-app-limits
  namespace: crm-platform
spec:
  limits:
  - default:
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
    type: Container
```

## Pod Security Standards

### Pod Security Admission Configuration
```yaml
# pod-security-admission.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: crm-platform-strict
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
---
# Alternative: Using Pod Security Policy (deprecated but still used in older clusters)
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: crm-restricted-psp
spec:
  privileged: false
  # Prevent root user
  runAsUser:
    rule: MustRunAsNonRoot
  # Prevent root group
  fsGroup:
    rule: MustRunAs
    ranges:
    - min: 1
      max: 65535
  # Prevent root group for supplemental groups
  supplementalGroups:
    rule: MustRunAs
    ranges:
    - min: 1
      max: 65535
  # Only allow specific volumes
  volumes:
  - configMap
  - emptyDir
  - projected
  - secret
  - downwardAPI
  - persistentVolumeClaim
  # Drop all capabilities
  allowedCapabilities: []
  # Required to drop all capabilities
  defaultAddCapabilities: []
  # Allow only specific host ports
  hostPorts:
  - min: 8000
    max: 8000
  - min: 8080
    max: 8080
  # Prevent host path volumes
  hostPath:
    allowed: false
  # Prevent host networking
  hostNetwork: false
  # Prevent host PID
  hostPID: false
  # Prevent host IPC
  hostIPC: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: psp:crm-restricted
rules:
- apiGroups: ['policy']
  resources: ['podsecuritypolicies']
  verbs:     ['use']
  resourceNames:
  - crm-restricted-psp
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: psp:crm-restricted
  namespace: crm-platform
subjects:
- kind: Group
  name: system:authenticated
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: psp:crm-restricted
  apiGroup: rbac.authorization.k8s.io
```

### Security Context Configuration
```yaml
# security-context.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-app-secure
  namespace: crm-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crm-app-secure
  template:
    metadata:
      labels:
        app: crm-app-secure
    spec:
      serviceAccountName: crm-app-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 3000
        fsGroup: 2000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: crm-app:latest
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false  # Set to true if app doesn't need write access
          runAsNonRoot: true
          runAsUser: 1000
          runAsGroup: 3000
          capabilities:
            drop:
            - ALL
            add:
            - NET_BIND_SERVICE  # Only if needed for binding to port 80/443
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        env:
        - name: SECURE_MODE
          value: "true"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
        volumeMounts:
        - name: app-logs
          mountPath: /app/logs
        - name: temp-storage
          mountPath: /tmp
      volumes:
      - name: app-logs
        emptyDir:
          medium: Memory
          sizeLimit: 100Mi
      - name: temp-storage
        emptyDir: {}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: crm-app-sa
  namespace: crm-platform
  annotations:
    kubernetes.io/enforce-mountable-secrets: "true"
```

## Network Security

### Network Policies
```yaml
# network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: crm-app-netpol
  namespace: crm-platform
spec:
  podSelector:
    matchLabels:
      app: crm-app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Allow traffic from ingress controller
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-controllers
      podSelector:
        matchLabels:
          app: nginx-ingress-controller
    ports:
    - protocol: TCP
      port: 8000
  # Allow traffic from monitoring
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 8000
  egress:
  # Allow DNS resolution
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  # Allow database connections
  - to:
    - podSelector:
        matchLabels:
          app: crm-db
    ports:
    - protocol: TCP
      port: 5432
  # Allow Redis connections
  - to:
    - podSelector:
        matchLabels:
          app: crm-redis
    ports:
    - protocol: TCP
      port: 6379
  # Allow Kafka connections
  - to:
    - podSelector:
        matchLabels:
          app: crm-kafka
    ports:
    - protocol: TCP
      port: 9092
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: crm-db-netpol
  namespace: crm-platform
spec:
  podSelector:
    matchLabels:
      app: crm-db
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: crm-app
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: crm-redis-netpol
  namespace: crm-platform
spec:
  podSelector:
    matchLabels:
      app: crm-redis
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: crm-app
    ports:
    - protocol: TCP
      port: 6379
---
# Deny all traffic by default in the namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-default
  namespace: crm-platform
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

## Secret Management

### External Secret Management

#### External Secrets Operator Configuration
```yaml
# external-secrets.yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: crm-platform
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "crm-app-role"
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: crm-db-credentials
  namespace: crm-platform
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: crm-db-secret
    creationPolicy: Owner
  data:
  - secretKey: username
    remoteRef:
      key: crm/database
      property: username
  - secretKey: password
    remoteRef:
      key: crm/database
      property: password
  - secretKey: url
    remoteRef:
      key: crm/database
      property: url
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: crm-api-keys
  namespace: crm-platform
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: crm-api-keys-secret
    creationPolicy: Owner
  data:
  - secretKey: twilio_sid
    remoteRef:
      key: crm/integrations/twilio
      property: sid
  - secretKey: twilio_token
    remoteRef:
      key: crm/integrations/twilio
      property: token
  - secretKey: gmail_oauth_token
    remoteRef:
      key: crm/integrations/gmail
      property: oauth_token
```

#### Sealed Secrets Configuration
```yaml
# sealed-secrets.yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: crm-sealed-secret
  namespace: crm-platform
spec:
  encryptedData:
    username: AgBy33ud7XzS4pHZzJWvQxJzZ3R2...
    password: AgCC33ud7XzS4pHZzJWvQxJzZ3R2...
    api_key: AgDD33ud7XzS4pHZzJWvQxJzZ3R2...
  template:
    metadata:
      name: crm-secret
      namespace: crm-platform
    type: Opaque
```

## Container Security

### Image Security Scanning

#### Trivy Scanner Configuration
```yaml
# trivy-scanner.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: crm-image-scanner
  namespace: security
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: trivy-sa
          containers:
          - name: trivy
            image: aquasec/trivy:latest
            command:
            - /bin/sh
            - -c
            - |
              trivy image --format json --output /tmp/report.json ghcr.io/myorg/crm-app:latest
              # Upload results to security dashboard
              curl -X POST -H "Content-Type: application/json" \
                -d @/tmp/report.json \
                http://security-dashboard:8080/api/vulnerabilities
          restartPolicy: OnFailure
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: trivy-sa
  namespace: security
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: trivy-role
  namespace: security
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: trivy-rolebinding
  namespace: security
subjects:
- kind: ServiceAccount
  name: trivy-sa
  namespace: security
roleRef:
  kind: Role
  name: trivy-role
  apiGroup: rbac.authorization.k8s.io
```

### Admission Controllers

#### Kyverno Policy for Security
```yaml
# kyverno-security-policies.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: crm-security-controls
spec:
  validationFailureAction: Enforce
  background: false
  rules:
  - name: require-run-as-non-root
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Containers must not run as root"
      pattern:
        spec:
          =(securityContext):
            runAsNonRoot: true
          containers:
          - securityContext:
              runAsNonRoot: true
  - name: require-drop-all-capabilities
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Containers must drop all capabilities"
      pattern:
        spec:
          containers:
          - securityContext:
              capabilities:
                drop:
                - ALL
  - name: disallow-privileged-containers
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Privileged containers are not allowed"
      pattern:
        spec:
          containers:
          - =(securityContext):
              =(privileged): false
  - name: require-read-only-root-filesystem
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Containers must have read-only root filesystem"
      pattern:
        spec:
          containers:
          - securityContext:
              readOnlyRootFilesystem: true
---
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: crm-image-policy
spec:
  validationFailureAction: Enforce
  rules:
  - name: require-digest
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Images must be referenced by digest"
      pattern:
        spec:
          containers:
          - image: "?*:*@*"  # Must contain both tag and digest
```

## Security Monitoring

### Security Event Monitoring
```yaml
# security-monitoring.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: security-exporter
  namespace: security
spec:
  selector:
    matchLabels:
      app: security-exporter
  endpoints:
  - port: metrics
    interval: 30s
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: security-exporter
  namespace: security
spec:
  replicas: 1
  selector:
    matchLabels:
      app: security-exporter
  template:
    metadata:
      labels:
        app: security-exporter
    spec:
      containers:
      - name: security-exporter
        image: myorg/security-exporter:latest
        ports:
        - containerPort: 8080
        env:
        - name: PROMETHEUS_METRICS_PORT
          value: "8080"
        - name: SECURITY_LOG_LEVEL
          value: "INFO"
---
apiVersion: v1
kind: Service
metadata:
  name: security-exporter-service
  namespace: security
  labels:
    app: security-exporter
spec:
  selector:
    app: security-exporter
  ports:
  - name: metrics
    port: 8080
    targetPort: 8080
```

### Falco Security Monitoring
```yaml
# falco-monitoring.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: falco
  namespace: security
spec:
  selector:
    matchLabels:
      app: falco
  template:
    metadata:
      labels:
        app: falco
    spec:
      hostPID: true
      hostNetwork: true
      initContainers:
      - name: falco-driver-loader
        image: falcosecurity/falco-driver-loader:latest
        securityContext:
          privileged: true
      containers:
      - name: falco
        image: falcosecurity/falco:latest
        securityContext:
          privileged: true
        env:
        - name: FALCO_K8S_NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: FALCO_GRPC_ENABLED
          value: "true"
        - name: FALCO_GRPC_UNENCRYPTED
          value: "true"
        volumeMounts:
        - name: dev-fs
          mountPath: /host/dev
          readOnly: true
        - name: proc-fs
          mountPath: /host/proc
          readOnly: true
        - name: boot-fs
          mountPath: /host/boot
          readOnly: true
        - name: modules-fs
          mountPath: /host/lib/modules
          readOnly: true
        - name: usr-fs
          mountPath: /host/usr
          readOnly: true
        - name: etc-fs
          mountPath: /host/etc
          readOnly: true
        - name: var-fs
          mountPath: /host/var
          readOnly: true
        - name: run-fs
          mountPath: /host/run
          readOnly: true
        - name: falco-config
          mountPath: /etc/falco
        - name: ssl-certs
          mountPath: /etc/ssl/certs
          readOnly: true
      volumes:
      - name: dev-fs
        hostPath:
          path: /dev
      - name: proc-fs
        hostPath:
          path: /proc
      - name: boot-fs
        hostPath:
          path: /boot
      - name: modules-fs
        hostPath:
          path: /lib/modules
      - name: usr-fs
        hostPath:
          path: /usr
      - name: etc-fs
        hostPath:
          path: /etc
      - name: var-fs
        hostPath:
          path: /var
      - name: run-fs
        hostPath:
          path: /run
      - name: falco-config
        configMap:
          name: falco-config
      - name: ssl-certs
        hostPath:
          path: /etc/ssl/certs
      tolerations:
      - effect: NoSchedule
        operator: Exists
      - effect: NoExecute
        operator: Exists
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: falco-config
  namespace: security
data:
  falco.yaml: |
    # Falco configuration
    syscall_event_drops:
      enabled: true
      rate: 0.1
      max_burst: 10
    rules_file:
    - /etc/falco/falco_rules.yaml
    - /etc/falco/falco_rules.local.yaml
    - /etc/falco/k8s_audit_rules.yaml
    json_output: true
    program_output:
      enabled: true
      keep_alive: false
      program: "jq -r '. | \"\\(.time) \\(.rule) \\(.output)\"' | logger -t falco"
---
apiVersion: v1
kind: Service
metadata:
  name: falco-service
  namespace: security
  labels:
    app: falco
spec:
  selector:
    app: falco
  ports:
  - port: 8765
    targetPort: 8765
    name: grpc
```

## Security Best Practices Summary

### Security Checklist
```yaml
# security-checklist.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: security-checklist
  namespace: security
data:
  checklist.md: |
    # Kubernetes Security Checklist for CRM Platform

    ## Cluster Security
    - [ ] RBAC configured with least privilege principle
    - [ ] Pod Security Standards enforced
    - [ ] Network policies implemented
    - [ ] TLS enabled for all communications
    - [ ] Regular security audits performed

    ## Workload Security
    - [ ] Images scanned for vulnerabilities
    - [ ] Non-root users used in containers
    - [ ] ReadOnlyRootFilesystem enabled
    - [ ] All capabilities dropped except necessary ones
    - [ ] Resource limits set for all containers

    ## Secret Management
    - [ ] External secret management (Vault/External Secrets Operator)
    - [ ] No hardcoded secrets in manifests
    - [ ] Sealed Secrets for GitOps workflows
    - [ ] Regular secret rotation

    ## Monitoring
    - [ ] Runtime security monitoring (Falco)
    - [ ] Admission controllers (Kyverno/Polaris)
    - [ ] Security event aggregation
    - [ ] Incident response procedures

    ## Compliance
    - [ ] CIS Kubernetes Benchmark compliance
    - [ ] SOC 2 compliance checks
    - [ ] Regular penetration testing
    - [ ] Security training for team members
```

This comprehensive security guide provides all the patterns and best practices needed to secure the CRM platform on Kubernetes.