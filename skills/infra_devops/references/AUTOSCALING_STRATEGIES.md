# Auto-Scaling Strategies for Kubernetes

## Overview

This document provides comprehensive guidance on auto-scaling strategies for the CRM platform deployed on Kubernetes. It covers Horizontal Pod Autoscaler (HPA), Vertical Pod Autoscaler (VPA), Cluster Autoscaler, and custom scaling strategies.

## Horizontal Pod Autoscaler (HPA)

### Basic CPU/Memory Scaling

#### Simple HPA Configuration
```yaml
# simple-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-app-simple-hpa
  namespace: crm-platform
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
```

#### Advanced HPA with Behavior Configuration
```yaml
# advanced-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-app-advanced-hpa
  namespace: crm-platform
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
        averageUtilization: 65
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 75
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 2
        periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
      - type: Pods
        value: 1
        periodSeconds: 60
      selectPolicy: Max
```

### Custom Metrics Scaling

#### Custom Metric from Application
```yaml
# custom-metric-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-app-custom-metric-hpa
  namespace: crm-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-app
  minReplicas: 2
  maxReplicas: 30
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
  - type: Pods
    pods:
      metric:
        name: queue_depth
      target:
        type: Value
        value: "50"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 45
      policies:
      - type: Percent
        value: 100
        periodSeconds: 10
    scaleDown:
      stabilizationWindowSeconds: 180
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

#### External Metrics Scaling
```yaml
# external-metric-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-app-external-metric-hpa
  namespace: crm-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-app
  minReplicas: 2
  maxReplicas: 25
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
  - type: External
    external:
      metric:
        name: aws_sqs_messages_visible
        selector:
          matchLabels:
            queue_name: crm-processing-queue
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
      - type: Percent
        value: 50
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 120
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

## Vertical Pod Autoscaler (VPA)

### VPA Recommendations and Updates
```yaml
# vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: crm-app-vpa
  namespace: crm-platform
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-app
  updatePolicy:
    updateMode: "Auto"  # or "Off" or "Initial"
  resourcePolicy:
    containerPolicies:
    - containerName: app
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 2
        memory: 4Gi
      controlledResources: ["cpu", "memory"]
      controlledValues: RequestsAndLimits
```

### VPA with Custom Resource Policy
```yaml
# vpa-custom.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: crm-app-vpa-custom
  namespace: crm-platform
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: app
      minAllowed:
        cpu: 250m
        memory: 256Mi
      maxAllowed:
        cpu: 1
        memory: 2Gi
      controlledResources: ["cpu", "memory"]
      controlledValues: RequestsAndLimits
    - containerName: sidecar
      minAllowed:
        cpu: 50m
        memory: 64Mi
      maxAllowed:
        cpu: 200m
        memory: 256Mi
      controlledResources: ["cpu", "memory"]
      controlledValues: RequestsAndLimits
```

## Cluster Autoscaler

### Cluster Autoscaler Configuration

#### AWS EKS Cluster Autoscaler
```yaml
# cluster-autoscaler-aws.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  labels:
    app: cluster-autoscaler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.21.0
        name: cluster-autoscaler
        resources:
          limits:
            cpu: 100m
            memory: 600Mi
          requests:
            cpu: 100m
            memory: 600Mi
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/crm-cluster
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
        - --scale-down-delay-after-add=10m
        - --scale-down-unneeded-time=10m
        - --scale-down-utilization-threshold=0.5
        volumeMounts:
        - name: ssl-certs
          mountPath: /etc/ssl/certs/ca-certificates.crt
          readOnly: true
      volumes:
      - name: ssl-certs
        hostPath:
          path: /etc/ssl/certs/ca-certificates.crt
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cluster-autoscaler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-autoscaler
  namespace: kube-system
rules:
- apiGroups: [""]
  resources: ["events", "endpoints"]
  verbs: ["create", "patch"]
- apiGroups: [""]
  resources: ["pods/eviction"]
  verbs: ["create"]
- apiGroups: [""]
  resources: ["pods/status"]
  verbs: ["update"]
- apiGroups: [""]
  resources: ["endpoints"]
  resourceNames: ["cluster-autoscaler"]
  verbs: ["get", "update"]
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["*"]
- apiGroups: [""]
  resources: ["pods", "services", "replicationcontrollers", "persistentvolumeclaims", "persistentvolumes"]
  verbs: ["*"]
- apiGroups: ["extensions"]
  resources: ["replicasets", "daemonsets"]
  verbs: ["*"]
- apiGroups: ["policy"]
  resources: ["poddisruptionbudgets"]
  verbs: ["*"]
- apiGroups: ["apps"]
  resources: ["statefulsets", "replicasets", "daemonsets"]
  verbs: ["*"]
- apiGroups: ["storage.k8s.io"]
  resources: ["storageclasses", "csinodes", "csidrivers", "csistoragecapacities"]
  verbs: ["*"]
- apiGroups: ["batch", "extensions"]
  resources: ["jobs"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: cluster-autoscaler
  namespace: kube-system
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["create","list","watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  resourceNames: ["cluster-autoscaler-status", "cluster-autoscaler-priority-expander"]
  verbs: ["delete","get","update","watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cluster-autoscaler
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-autoscaler
subjects:
- kind: ServiceAccount
  name: cluster-autoscaler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: cluster-autoscaler
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: cluster-autoscaler
subjects:
- kind: ServiceAccount
  name: cluster-autoscaler
  namespace: kube-system
```

#### GKE Cluster Autoscaler Configuration
```yaml
# cluster-autoscaler-gke.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.21.0
        name: cluster-autoscaler
        resources:
          limits:
            cpu: 100m
            memory: 600Mi
          requests:
            cpu: 100m
            memory: 600Mi
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=gce
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=google:{"NodeGroupUrls":["gce://projects/PROJECT_ID/zones/*/instanceGroupManagers/*"]}
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
        - --scale-down-delay-after-add=10m
        - --scale-down-unneeded-time=10m
        - --scale-down-utilization-threshold=0.5
```

## Custom Metrics Server Setup

### Prometheus Adapter Configuration
```yaml
# prometheus-adapter-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: adapter-config
  namespace: monitoring
data:
  config.yaml: |
    rules:
    - seriesQuery: 'http_requests_total'
      seriesFilters: []
      resources:
        overrides:
          kubernetes_namespace:
            resource: namespace
          kubernetes_pod_name:
            resource: pod
      name:
        matches: "^(.*)_total"
        as: "${1}_per_second"
      metricsQuery: 'sum(rate(<<.Series>>{<<.LabelMatchers>>}[2m])) by (<<.GroupBy>>)'
    - seriesQuery: 'redis_connected_clients'
      resources:
        template: <<.Resource>>
      name:
        matches: "^(.*)"
        as: "redis_connected_clients"
      metricsQuery: 'avg(<<.Series>>{<<.LabelMatchers>>}) by (<<.GroupBy>>)'
    - seriesQuery: 'queue_depth'
      resources:
        template: <<.Resource>>
      name:
        matches: "^(.*)"
        as: "queue_depth"
      metricsQuery: 'avg(<<.Series>>{<<.LabelMatchers>>}) by (<<.GroupBy>>)'
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus-adapter
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      name: prometheus-adapter
  template:
    metadata:
      labels:
        name: prometheus-adapter
    spec:
      serviceAccountName: prometheus-adapter
      containers:
      - name: prometheus-adapter
        image: k8s.gcr.io/prometheus-adapter/prometheus-adapter:v0.9.1
        args:
        - --cert-dir=/var/run/serving-cert
        - --config=/etc/adapter/config.yaml
        - --metrics-relist-interval=1m
        - --prometheus-url=http://prometheus:9090
        - --secure-port=6443
        - --tls-cipher-suites=TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305,TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
        ports:
        - containerPort: 6443
        volumeMounts:
        - name: config-volume
          mountPath: /etc/adapter/
          readOnly: true
      volumes:
      - name: config-volume
        configMap:
          name: adapter-config
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus-adapter
  namespace: monitoring
  annotations:
    service.alpha.kubernetes.io/tolerate-unready-endpoints: "true"
spec:
  ports:
  - port: 443
    targetPort: 6443
  selector:
    name: prometheus-adapter
```

## Advanced Scaling Strategies

### Multi-Component Scaling
```yaml
# multi-component-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-multi-component-hpa
  namespace: crm-platform
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
        averageUtilization: 60
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: processing_rate
      target:
        type: AverageValue
        averageValue: "50"
  - type: Pods
    pods:
      metric:
        name: queue_length
      target:
        type: Value
        value: "100"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
      - type: Percent
        value: 100
        periodSeconds: 10
      - type: Pods
        value: 3
        periodSeconds: 10
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 180
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
      - type: Pods
        value: 1
        periodSeconds: 60
      selectPolicy: Max
```

### Predictive Scaling with Cron Jobs
```yaml
# predictive-scaling.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: crm-predictive-scale-up
  namespace: crm-platform
spec:
  schedule: "0 8 * * 1-5"  # Weekdays at 8 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scale-up
            image: bitnami/kubectl:latest
            command:
            - /bin/sh
            - -c
            - |
              kubectl patch deployment crm-app -n crm-platform -p '{"spec":{"replicas":10}}'
          restartPolicy: OnFailure
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: crm-predictive-scale-down
  namespace: crm-platform
spec:
  schedule: "0 19 * * 1-5"  # Weekdays at 7 PM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scale-down
            image: bitnami/kubectl:latest
            command:
            - /bin/sh
            - -c
            - |
              kubectl patch deployment crm-app -n crm-platform -p '{"spec":{"replicas":3}}'
          restartPolicy: OnFailure
```

## Scaling Based on Business Metrics

### Queue-Based Scaling
```yaml
# queue-based-scaling.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-queue-based-hpa
  namespace: crm-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-worker
  minReplicas: 1
  maxReplicas: 20
  metrics:
  - type: External
    external:
      metric:
        name: sqs_messages_visible
        selector:
          matchLabels:
            queue: crm-processing-queue
      target:
        type: Value
        value: "10"  # Scale up when 10+ messages per pod
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
      - type: Percent
        value: 200
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 120
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

### Traffic-Based Scaling
```yaml
# traffic-based-scaling.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-traffic-based-hpa
  namespace: crm-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-app
  minReplicas: 2
  maxReplicas: 30
  metrics:
  - type: External
    external:
      metric:
        name: ingress_http_requests_per_second
        selector:
          matchLabels:
            ingress: crm-app-ingress
      target:
        type: AverageValue
        averageValue: "50"  # 50 req/sec per pod
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 45
      policies:
      - type: Percent
        value: 100
        periodSeconds: 10
    scaleDown:
      stabilizationWindowSeconds: 240
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

## Scaling Policies for Different Workloads

### API Server Scaling Policy
```yaml
# api-server-scaling.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-api-server-hpa
  namespace: crm-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-api-server
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30  # Fast response to traffic spikes
      policies:
      - type: Percent
        value: 100
        periodSeconds: 10
      - type: Pods
        value: 5
        periodSeconds: 10
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 120  # Slower scale down to avoid thrashing
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

### Background Worker Scaling Policy
```yaml
# worker-scaling.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-background-worker-hpa
  namespace: crm-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-background-worker
  minReplicas: 1
  maxReplicas: 20
  metrics:
  - type: External
    external:
      metric:
        name: queue_length
        selector:
          matchLabels:
            queue: crm-task-queue
      target:
        type: Value
        value: "5"  # 5 tasks per worker
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 200
        periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 600  # Very conservative scale down
      policies:
      - type: Percent
        value: 10
        periodSeconds: 120
```

## Scaling Monitoring and Observability

### HPA Monitoring Configuration
```yaml
# hpa-monitoring.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: hpa-monitor
  namespace: crm-platform
spec:
  selector:
    matchLabels:
      app: crm-app
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
---
apiVersion: v1
kind: Service
metadata:
  name: crm-app-metrics
  namespace: crm-platform
  labels:
    app: crm-app
    metrics: enabled
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
spec:
  selector:
    app: crm-app
  ports:
  - name: metrics
    port: 8000
    targetPort: 8000
```

## Scaling Best Practices

### Resource Requests and Limits for Scaling
```yaml
# scaling-best-practices.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-app-best-practices
  namespace: crm-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crm-app-best-practices
  template:
    metadata:
      labels:
        app: crm-app-best-practices
    spec:
      containers:
      - name: app
        image: crm-app:latest
        resources:
          requests:
            memory: "256Mi"   # Set appropriate requests for HPA to work
            cpu: "100m"
          limits:
            memory: "512Mi"   # Set reasonable limits to prevent resource exhaustion
            cpu: "500m"
        # Proper health checks help with scaling decisions
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

This comprehensive auto-scaling guide provides all the strategies and configurations needed to properly scale the CRM platform components based on various metrics and requirements.