# Resource Optimization for Kubernetes

## Overview

This document provides comprehensive guidance on optimizing resource usage for the CRM platform deployed on Kubernetes. It covers resource allocation, efficiency strategies, cost optimization, and performance tuning.

## Resource Allocation Best Practices

### CPU and Memory Requests/Limits

#### Optimal Resource Configuration
```yaml
# resource-optimization.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-app-optimized
  namespace: crm-platform
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: crm-app-optimized
  template:
    metadata:
      labels:
        app: crm-app-optimized
    spec:
      containers:
      - name: app
        image: crm-app:latest
        # CPU-optimized configuration
        resources:
          requests:
            cpu: "250m"      # 0.25 cores minimum
            memory: "256Mi"  # 256 MB minimum
          limits:
            cpu: "500m"      # 0.5 cores maximum
            memory: "512Mi"  # 512 MB maximum
        # Additional optimization settings
        env:
        - name: GOMAXPROCS  # For Go apps
          valueFrom:
            resourceFieldRef:
              containerName: app
              resource: limits.cpu
        - name: JAVA_OPTS   # For Java apps
          value: "-XX:InitialRAMPercentage=25.0 -XX:MaxRAMPercentage=75.0"
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 5
          failureThreshold: 3
      # Pod-level resource optimization
      terminationGracePeriodSeconds: 30
      dnsPolicy: ClusterFirst
      restartPolicy: Always
      schedulerName: default-scheduler
---
# Sidecar container with minimal resources
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-app-with-sidecar
  namespace: crm-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crm-app-with-sidecar
  template:
    metadata:
      labels:
        app: crm-app-with-sidecar
    spec:
      containers:
      - name: app
        image: crm-app:latest
        resources:
          requests:
            cpu: "300m"
            memory: "384Mi"
          limits:
            cpu: "600m"
            memory: "768Mi"
        ports:
        - containerPort: 8000
      - name: sidecar-logger
        image: busybox:latest
        command: ['sh', '-c', 'tail -n+1 -f /var/log/app/*.log']
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
          limits:
            cpu: "100m"
            memory: "128Mi"
        volumeMounts:
        - name: logs
          mountPath: /var/log/app
      volumes:
      - name: logs
        emptyDir: {}
```

### Vertical Pod Autoscaler Configuration
```yaml
# vpa-configuration.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: crm-app-vpa
  namespace: crm-platform
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-app-optimized
  updatePolicy:
    updateMode: "Auto"  # Automatically apply resource recommendations
  resourcePolicy:
    containerPolicies:
    - containerName: app
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 1
        memory: 2Gi
      controlledResources: ["cpu", "memory"]
      controlledValues: RequestsAndLimits
---
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: crm-db-vpa
  namespace: crm-platform
spec:
  targetRef:
    apiVersion: apps/v1
    kind: StatefulSet
    name: crm-db
  updatePolicy:
    updateMode: "Off"  # Manual updates for stateful components
  resourcePolicy:
    containerPolicies:
    - containerName: postgres
      minAllowed:
        cpu: 500m
        memory: 1Gi
      maxAllowed:
        cpu: 2
        memory: 4Gi
      controlledResources: ["cpu", "memory"]
      controlledValues: RequestsAndLimits
```

## Cost Optimization Strategies

### Node Affinity and Anti-Affinity
```yaml
# node-optimization.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-app-cost-optimized
  namespace: crm-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crm-app-cost-optimized
  template:
    metadata:
      labels:
        app: crm-app-cost-optimized
    spec:
      # Node affinity for cost-effective scheduling
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: node.kubernetes.io/lifecycle
                operator: In
                values: ["spot", "batch"]  # Prefer spot/batch instances
          - weight: 50
            preference:
              matchExpressions:
              - key: kubernetes.azure.com/mode
                operator: In
                values: ["nodepool"]  # Azure-specific
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - crm-app-cost-optimized
              topologyKey: kubernetes.io/hostname
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 50
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - crm-cache  # Colocate with cache if possible
              topologyKey: kubernetes.io/hostname
      containers:
      - name: app
        image: crm-app:latest
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "400m"
            memory: "512Mi"
        ports:
        - containerPort: 8000
---
# Node selector for specific instance types
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-app-instance-optimized
  namespace: crm-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crm-app-instance-optimized
  template:
    metadata:
      labels:
        app: crm-app-instance-optimized
    spec:
      nodeSelector:
        # Select cost-effective instance types
        node.kubernetes.io/instance-type: "t3.medium"  # AWS
        # Or for GCP: cloud.google.com/gke-nodepool: "cost-optimized-pool"
        # Or for Azure: kubernetes.azure.com/mode: "nodepool"
        beta.kubernetes.io/os: linux
        topology.kubernetes.io/zone: us-west-2a
      tolerations:
      - key: "spot"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
      containers:
      - name: app
        image: crm-app:latest
        resources:
          requests:
            cpu: "250m"
            memory: "320Mi"
          limits:
            cpu: "500m"
            memory: "640Mi"
```

### Priority Classes for Resource Management
```yaml
# priority-classes.yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: crm-critical
value: 1000000
globalDefault: false
description: "Critical CRM platform components"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: crm-important
value: 900000
globalDefault: false
description: "Important CRM platform components"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: crm-standard
value: 800000
globalDefault: true
description: "Standard CRM platform components"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: crm-low
value: 700000
globalDefault: false
description: "Low priority batch jobs"
---
# Deployment using priority class
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-critical-app
  namespace: crm-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crm-critical-app
  template:
    metadata:
      labels:
        app: crm-critical-app
    spec:
      priorityClassName: crm-critical
      containers:
      - name: app
        image: crm-app:latest
        resources:
          requests:
            cpu: "300m"
            memory: "384Mi"
          limits:
            cpu: "600m"
            memory: "768Mi"
```

## Performance Optimization

### Resource Sizing Guidelines
```yaml
# performance-sizing.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-perf-optimized
  namespace: crm-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crm-perf-optimized
  template:
    metadata:
      labels:
        app: crm-perf-optimized
    spec:
      # Optimized for performance
      containers:
      - name: app
        image: crm-app:latest
        # Memory-intensive configuration
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"    # Higher memory for caching
          limits:
            cpu: "1"
            memory: "2Gi"
        env:
        # JVM tuning for memory-intensive apps
        - name: JAVA_OPTS
          value: >
            -XX:+UseG1GC
            -XX:MaxGCPauseMillis=200
            -XX:+UseStringDeduplication
            -XX:InitialHeapSize=512m
            -XX:MaxHeapSize=1536m
        # CPU-intensive configuration (alternative)
      - name: processor
        image: crm-processor:latest
        resources:
          requests:
            cpu: "1"
            memory: "512Mi"
          limits:
            cpu: "2"
            memory: "1Gi"
        env:
        - name: PARALLELISM
          valueFrom:
            resourceFieldRef:
              containerName: processor
              resource: limits.cpu
---
# Database optimization
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: crm-db-optimized
  namespace: crm-platform
spec:
  serviceName: crm-db-headless
  replicas: 1
  selector:
    matchLabels:
      app: crm-db-optimized
  template:
    metadata:
      labels:
        app: crm-db-optimized
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"    # Critical for database performance
          limits:
            cpu: "2"
            memory: "4Gi"
        env:
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: crm-db-secret
              key: database
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: crm-db-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: crm-db-secret
              key: password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        # PostgreSQL-specific optimizations
        - name: POSTGRES_INITDB_ARGS
          value: "--data-checksums"
        envFrom:
        - configMapRef:
            name: postgres-config
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        livenessProbe:
          exec:
            command:
            - sh
            - -c
            - exec pg_isready -U $POSTGRES_USER -d $POSTGRES_DB
          initialDelaySeconds: 60
          timeoutSeconds: 5
          periodSeconds: 10
          failureThreshold: 6
        readinessProbe:
          exec:
            command:
            - sh
            - -c
            - exec pg_isready -U $POSTGRES_USER -d $POSTGRES_DB
          initialDelaySeconds: 10
          timeoutSeconds: 5
          periodSeconds: 5
          failureThreshold: 6
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi  # Larger storage for performance
      storageClassName: fast-ssd  # High-performance storage class
```

## Horizontal Pod Autoscaler Optimization

### Custom Metrics Based Scaling
```yaml
# hpa-optimization.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-app-hpa-optimized
  namespace: crm-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-app-optimized
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
---
# Cost-optimized HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-app-hpa-cost-optimized
  namespace: crm-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-app-cost-optimized
  minReplicas: 1  # Lower minimum for cost savings
  maxReplicas: 15
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80  # Higher threshold for cost optimization
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 90  # Longer stabilization to avoid thrashing
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 600  # Much longer for cost optimization
      policies:
      - type: Percent
        value: 10
        periodSeconds: 120
```

## Storage Optimization

### Volume Optimization Strategies
```yaml
# storage-optimization.yaml
apiVersion: v1
kind: StorageClass
metadata:
  name: crm-fast-ssd
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  fsType: ext4
  iopsPerGB: "10"  # Provisioned IOPS
  allowVolumeExpansion: "true"
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: v1
kind: StorageClass
metadata:
  name: crm-standard-hdd
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp2
  fsType: ext4
  allowVolumeExpansion: "true"
volumeBindingMode: WaitForFirstConsumer
---
# Optimized PVC configuration
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: crm-app-storage
  namespace: crm-platform
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: crm-fast-ssd
---
# Application with optimized storage usage
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-app-storage-optimized
  namespace: crm-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crm-app-storage-optimized
  template:
    metadata:
      labels:
        app: crm-app-storage-optimized
    spec:
      containers:
      - name: app
        image: crm-app:latest
        resources:
          requests:
            cpu: "250m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        volumeMounts:
        - name: app-cache
          mountPath: /app/cache
          # Use memory-backed storage for cache
        - name: app-logs
          mountPath: /app/logs
          # Use persistent storage for logs
        - name: app-data
          mountPath: /app/data
          # Use high-performance storage for data
        env:
        - name: CACHE_DIR
          value: "/app/cache"
        - name: LOG_DIR
          value: "/app/logs"
      volumes:
      - name: app-cache
        emptyDir:
          medium: Memory  # In-memory cache
          sizeLimit: 128Mi
      - name: app-logs
        emptyDir:
          medium: ""
          sizeLimit: 512Mi
      - name: app-data
        persistentVolumeClaim:
          claimName: crm-app-storage
```

## Monitoring and Optimization Tools

### Resource Monitoring Configuration
```yaml
# resource-monitoring.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: crm-app-resources
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: crm-app-optimized
  endpoints:
  - port: http
    interval: 30s
    path: /metrics
    metricRelabelings:
    - sourceLabels: [__name__]
      regex: 'container_.*'
      action: keep
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: resource-analysis-script
  namespace: monitoring
data:
  analyze_resources.py: |
    #!/usr/bin/env python3
    """
    Resource analysis script for Kubernetes optimization
    """
    import requests
    import json
    from datetime import datetime, timedelta

    def get_resource_usage(namespace="crm-platform"):
        """Analyze resource usage in the namespace"""
        prometheus_url = "http://prometheus-service:9090"

        # Query for CPU usage
        cpu_query = f'avg(rate(container_cpu_usage_seconds_total{{namespace="{namespace}"}}[5m])) by (pod, container)'
        memory_query = f'avg(container_memory_working_set_bytes{{namespace="{namespace}"}}) by (pod, container)'

        cpu_response = requests.get(f"{prometheus_url}/api/v1/query", params={"query": cpu_query})
        memory_response = requests.get(f"{prometheus_url}/api/v1/query", params={"query": memory_query})

        cpu_data = cpu_response.json()
        memory_data = memory_response.json()

        analysis = {
            "timestamp": datetime.utcnow().isoformat(),
            "namespace": namespace,
            "cpu_usage": cpu_data.get("data", {}).get("result", []),
            "memory_usage": memory_data.get("data", {}).get("result", [])
        }

        return analysis

    def suggest_optimizations(analysis):
        """Suggest resource optimizations based on usage"""
        suggestions = []

        for result in analysis.get("cpu_usage", []):
            pod = result["metric"]["pod"]
            container = result["metric"]["container"]
            value = float(result["value"][1])

            # Convert to millicores for comparison
            cpu_millicores = value * 1000

            if cpu_millicores < 100:  # Using less than 100m
                suggestions.append({
                    "type": "cpu",
                    "pod": pod,
                    "container": container,
                    "current_usage": f"{cpu_millicores:.2f}m",
                    "recommendation": "Consider reducing CPU request/limit"
                })

        for result in analysis.get("memory_usage", []):
            pod = result["metric"]["pod"]
            container = result["metric"]["container"]
            value = float(result["value"][1])

            # Convert to MiB for comparison
            memory_mib = value / (1024 * 1024)

            if memory_mib < 128:  # Using less than 128Mi
                suggestions.append({
                    "type": "memory",
                    "pod": pod,
                    "container": container,
                    "current_usage": f"{memory_mib:.2f}Mi",
                    "recommendation": "Consider reducing memory request/limit"
                })

        return suggestions

    if __name__ == "__main__":
        analysis = get_resource_usage()
        suggestions = suggest_optimizations(analysis)

        print(json.dumps({
            "analysis": analysis,
            "suggestions": suggestions
        }, indent=2))
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: resource-optimizer
  namespace: monitoring
spec:
  schedule: "0 1 * * *"  # Daily at 1 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: resource-analyzer
            image: python:3.11-slim
            command:
            - /bin/sh
            - -c
            - |
              pip install requests
              python /scripts/analyze_resources.py > /tmp/results.json
              cat /tmp/results.json
          volumeMounts:
          - name: analysis-script
            mountPath: /scripts
          volumes:
          - name: analysis-script
            configMap:
              name: resource-analysis-script
          restartPolicy: OnFailure
```

## Resource Optimization Best Practices

### Configuration Best Practices
```yaml
# optimization-best-practices.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: resource-optimization-checklist
  namespace: crm-platform
data:
  checklist.md: |
    # Kubernetes Resource Optimization Checklist

    ## Resource Requests and Limits
    - [ ] Set appropriate CPU and memory requests for all containers
    - [ ] Set reasonable limits to prevent resource exhaustion
    - [ ] Monitor actual usage vs. allocated resources
    - [ ] Right-size resources based on actual usage patterns

    ## Horizontal Pod Autoscaler
    - [ ] Configure HPA based on actual load patterns
    - [ ] Use custom metrics when CPU/memory aren't sufficient
    - [ ] Set appropriate min/max replica counts
    - [ ] Configure scale-up/down behaviors to prevent thrashing

    ## Vertical Pod Autoscaler
    - [ ] Deploy VPA for automatic resource recommendation
    - [ ] Review and apply VPA recommendations regularly
    - [ ] Use VPA update modes appropriately (Auto, Initial, Off)

    ## Storage Optimization
    - [ ] Use appropriate storage classes for different use cases
    - [ ] Implement proper data lifecycle management
    - [ ] Use emptyDir for temporary storage when appropriate
    - [ ] Configure persistent volumes with adequate capacity

    ## Node Optimization
    - [ ] Use node affinity/anti-affinity for optimal placement
    - [ ] Implement pod anti-affinity for high availability
    - [ ] Use priority classes for critical components
    - [ ] Consider spot/preemptible instances for cost savings

    ## Cost Optimization
    - [ ] Monitor cluster resource utilization
    - [ ] Use reserved instances for predictable workloads
    - [ ] Implement cluster autoscaling
    - [ ] Regularly review and optimize resource allocations
```

This comprehensive resource optimization guide provides all the strategies and configurations needed to optimize resource usage and costs for the CRM platform on Kubernetes.