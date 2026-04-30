---
name: infra_devops
description: Handles containerization with Docker and deployment orchestration on Kubernetes. Manages K8s manifests, auto-scaling configurations, and health monitoring for all system components. Use when Claude needs to work with Docker containerization, Kubernetes deployment orchestration, K8s manifests, auto-scaling configurations, or health monitoring for system components.
---

# Infrastructure DevOps Skill

This skill provides guidance for containerization with Docker and deployment orchestration on Kubernetes. It covers Docker containerization, Kubernetes manifests, auto-scaling configurations, and health monitoring for all system components.

## Overview

The infrastructure DevOps system handles containerization and orchestration of the CRM platform components. It provides:

- Docker containerization for all services
- Kubernetes deployment orchestration
- Auto-scaling configurations
- Health monitoring and observability
- CI/CD pipeline integration
- Resource management and optimization

## Containerization with Docker

### Docker Best Practices

#### Multi-stage Builds
```dockerfile
# Multi-stage build for optimized container size
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt


# Production stage
FROM python:3.11-slim

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app \
    && chown -R app:app /app
WORKDIR /app

# Copy Python wheels from builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/* \
    && rm -rf /wheels

# Copy application code
COPY --chown=app:app . .

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]
```

#### Docker Security Best Practices
```dockerfile
# Use specific base image tags (not 'latest')
FROM python:3.11.6-slim

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set working directory with proper permissions
WORKDIR /app
RUN chown appuser:appgroup /app

# Copy application files with proper ownership
COPY --chown=appuser:appgroup . .

# Use non-root user for running the application
USER appuser

# Minimize attack surface by not installing unnecessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

### Docker Compose for Local Development
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/mydb
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
```

## Kubernetes Deployment

### Core Kubernetes Manifests

#### Deployment Manifest
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-app
  labels:
    app: crm-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: crm-app
  template:
    metadata:
      labels:
        app: crm-app
    spec:
      containers:
      - name: app
        image: crm-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: redis_url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          capabilities:
            drop:
            - ALL
```

#### Service Manifest
```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: crm-app-service
  labels:
    app: crm-app
spec:
  selector:
    app: crm-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP
```

#### Ingress Manifest
```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: crm-app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - crm.example.com
    secretName: crm-tls-secret
  rules:
  - host: crm.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: crm-app-service
            port:
              number: 80
```

### Configuration Management

#### ConfigMap
```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  environment: "production"
  log_level: "info"
  redis_url: "redis://redis-service:6379"
  feature_flags: |
    {
      "enable_new_ui": true,
      "beta_features": false
    }
```

#### Secret Management
```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  url: <base64-encoded-database-url>
  username: <base64-encoded-username>
  password: <base64-encoded-password>
```

## Auto-Scaling Configurations

### Horizontal Pod Autoscaler (HPA)
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

### Custom Metrics Scaling
```yaml
# custom-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-app-custom-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-app
  minReplicas: 2
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

## Health Monitoring

### Prometheus Metrics
```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
```

### Service Monitor (Prometheus Operator)
```yaml
# service-monitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: crm-app-monitor
  labels:
    app: crm-app
spec:
  selector:
    matchLabels:
      app: crm-app
  endpoints:
  - port: http
    interval: 30s
    path: /metrics
```

### Health Checks and Readiness Probes
```python
# health_check.py
from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

@app.route('/health')
def health():
    """Liveness probe - check if the app is running"""
    return jsonify({"status": "healthy"}), 200

@app.route('/ready')
def ready():
    """Readiness probe - check if the app is ready to serve traffic"""
    # Check database connectivity
    db_connected = check_database_connection()

    # Check external dependencies
    external_services_ok = check_external_dependencies()

    if db_connected and external_services_ok:
        return jsonify({"status": "ready"}), 200
    else:
        return jsonify({
            "status": "not_ready",
            "checks": {
                "database": db_connected,
                "external_services": external_services_ok
            }
        }), 503

def check_database_connection():
    """Check database connectivity"""
    try:
        # Implement your database connection check
        # For example, with SQLAlchemy:
        # db.session.execute(text('SELECT 1')).fetchone()
        return True
    except Exception:
        return False

def check_external_dependencies():
    """Check external service dependencies"""
    try:
        # Check Redis
        redis_host = os.getenv('REDIS_URL', 'redis://localhost:6379')
        # Implement Redis connectivity check

        # Check other external services
        return True
    except Exception:
        return False

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

## CI/CD Pipeline Integration

### GitHub Actions Example
```yaml
# .github/workflows/deploy.yml
name: Deploy to Kubernetes

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Login to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata for Docker
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ghcr.io/${{ github.repository_owner }}/crm-app
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-

    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3

    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'latest'

    - name: Set up Kustomize
      run: |
        wget -O kustomize.tar.gz https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v5.0.1/kustomize_v5.0.1_linux_amd64.tar.gz
        tar -xzf kustomize.tar.gz
        chmod u+x kustomize
        sudo mv kustomize /usr/local/bin/kustomize

    - name: Update deployment image
      run: |
        kustomize edit set image ghcr.io/${{ github.repository_owner }}/crm-app:${{ github.sha }} ghcr.io/${{ github.repository_owner }}/crm-app:${{ github.sha }}

    - name: Deploy to Kubernetes
      run: |
        kubectl apply -k ./
```

## Advanced Kubernetes Patterns

### StatefulSets for Stateful Applications
```yaml
# statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres-db
spec:
  serviceName: postgres-service
  replicas: 1  # For PostgreSQL, typically 1 replica with persistent storage
  selector:
    matchLabels:
      app: postgres-db
  template:
    metadata:
      labels:
        app: postgres-db
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: db_name
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
      storageClassName: fast-ssd
```

### DaemonSets for Cluster-Wide Services
```yaml
# daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit-logging
  labels:
    app: fluent-bit-logging
spec:
  selector:
    matchLabels:
      app: fluent-bit-logging
  template:
    metadata:
      labels:
        app: fluent-bit-logging
    spec:
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:latest
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 20Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
      terminationGracePeriodSeconds: 10
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```

## Resource Management and Optimization

### Resource Quotas
```yaml
# resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: crm-app-quota
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    persistentvolumeclaims: "10"
    secrets: "20"
    configmaps: "30"
```

### Limit Ranges
```yaml
# limit-range.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: crm-app-limits
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

## Security Best Practices

### Network Policies
```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: crm-app-network-policy
spec:
  podSelector:
    matchLabels:
      app: crm-app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53  # DNS
  - to:
    - podSelector:
        matchLabels:
          app: postgres-db
    ports:
    - protocol: TCP
      port: 5432
```

### RBAC Configuration
```yaml
# rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: crm-app-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: crm-app-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: crm-app-rolebinding
subjects:
- kind: ServiceAccount
  name: crm-app-sa
  namespace: default
roleRef:
  kind: Role
  name: crm-app-role
  apiGroup: rbac.authorization.k8s.io
```

## Monitoring and Observability

For detailed implementation patterns, see:
- [DOCKER_PATTERNS.md](references/DOCKER_PATTERNS.md) - Docker containerization patterns
- [KUBERNETES_MANIFESTS.md](references/KUBERNETES_MANIFESTS.md) - Kubernetes manifest templates
- [AUTOSCALING_STRATEGIES.md](references/AUTOSCALING_STRATEGIES.md) - Auto-scaling configurations
- [MONITORING_STACK.md](references/MONITORING_STACK.md) - Monitoring and observability stack
- [CI_CD_PIPELINES.md](references/CI_CD_PIPELINES.md) - CI/CD pipeline configurations
- [SECURITY_BEST_PRACTICES.md](references/SECURITY_BEST_PRACTICES.md) - Security implementations
- [RESOURCE_OPTIMIZATION.md](references/RESOURCE_OPTIMIZATION.md) - Resource management and optimization