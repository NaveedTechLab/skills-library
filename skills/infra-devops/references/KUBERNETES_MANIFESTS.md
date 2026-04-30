# Kubernetes Manifests for CRM Platform

## Overview

This document provides comprehensive Kubernetes manifests for deploying the CRM platform components. It covers deployments, services, ingresses, and other Kubernetes resources needed for a production-grade setup.

## Core Application Deployment

### Main Application Deployment
```yaml
# crm-app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-app
  namespace: crm-platform
  labels:
    app: crm-app
    tier: backend
    version: v1.0.0
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
        tier: backend
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: crm-app-sa
      automountServiceAccountToken: true
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
      containers:
      - name: app
        image: crm-platform/crm-app:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
          protocol: TCP
        env:
        - name: PORT
          value: "8000"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: crm-db-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: crm-app-config
              key: redis_url
        - name: KAFKA_BOOTSTRAP_SERVERS
          valueFrom:
            configMapKeyRef:
              name: crm-app-config
              key: kafka_servers
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: crm-app-config
              key: log_level
        envFrom:
        - configMapRef:
            name: crm-app-env
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
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
        startupProbe:
          httpGet:
            path: /startup
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 30
        volumeMounts:
        - name: app-logs
          mountPath: /app/logs
        - name: temp-storage
          mountPath: /tmp
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          capabilities:
            drop:
            - ALL
            add:
            - NET_BIND_SERVICE
      initContainers:
      - name: wait-for-db
        image: busybox:1.35
        command: ['sh', '-c', 'until nc -z crm-db-service 5432; do echo waiting for database; sleep 2; done;']
        securityContext:
          runAsNonRoot: true
          runAsUser: 65534
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
      volumes:
      - name: app-logs
        emptyDir:
          medium: Memory
          sizeLimit: 100Mi
      - name: temp-storage
        emptyDir: {}
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - crm-app
              topologyKey: kubernetes.io/hostname
---
apiVersion: v1
kind: Service
metadata:
  name: crm-app-service
  namespace: crm-platform
  labels:
    app: crm-app
spec:
  selector:
    app: crm-app
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: crm-app-sa
  namespace: crm-platform
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: crm-app-role
  namespace: crm-platform
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
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
```

## Database Components

### PostgreSQL Deployment
```yaml
# crm-db-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: crm-db
  namespace: crm-platform
  labels:
    app: crm-db
    tier: database
spec:
  serviceName: crm-db-headless
  replicas: 1
  selector:
    matchLabels:
      app: crm-db
  template:
    metadata:
      labels:
        app: crm-db
        tier: database
    spec:
      securityContext:
        fsGroup: 26
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres
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
        resources:
          requests:
            memory: "1Gi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "500m"
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
        securityContext:
          runAsUser: 999
          runAsGroup: 999
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          capabilities:
            drop:
            - ALL
      securityContext:
        runAsNonRoot: true
        fsGroup: 999
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi
      storageClassName: fast-ssd
---
apiVersion: v1
kind: Service
metadata:
  name: crm-db-service
  namespace: crm-platform
  labels:
    app: crm-db
spec:
  clusterIP: None  # Headless service for StatefulSet
  selector:
    app: crm-db
  ports:
  - port: 5432
    targetPort: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: crm-db-loadbalancer
  namespace: crm-platform
  labels:
    app: crm-db
spec:
  type: LoadBalancer
  selector:
    app: crm-db
  ports:
  - port: 5432
    targetPort: 5432
```

### Redis Deployment
```yaml
# crm-redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-redis
  namespace: crm-platform
  labels:
    app: crm-redis
    tier: cache
spec:
  replicas: 2
  selector:
    matchLabels:
      app: crm-redis
  template:
    metadata:
      labels:
        app: crm-redis
        tier: cache
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        fsGroup: 999
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
          name: redis
        command:
        - redis-server
        - /etc/redis/redis.conf
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
        volumeMounts:
        - name: redis-config
          mountPath: /etc/redis
        - name: redis-data
          mountPath: /data
        livenessProbe:
          exec:
            command:
            - sh
            - -c
            - "redis-cli ping"
          initialDelaySeconds: 30
          timeoutSeconds: 5
          periodSeconds: 10
          failureThreshold: 3
        readinessProbe:
          exec:
            command:
            - sh
            - -c
            - "redis-cli ping"
          initialDelaySeconds: 5
          timeoutSeconds: 3
          periodSeconds: 5
          failureThreshold: 3
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          capabilities:
            drop:
            - ALL
      volumes:
      - name: redis-config
        configMap:
          name: crm-redis-config
      - name: redis-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: crm-redis-service
  namespace: crm-platform
  labels:
    app: crm-redis
spec:
  selector:
    app: crm-redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: crm-redis-config
  namespace: crm-platform
data:
  redis.conf: |
    maxmemory 256mb
    maxmemory-policy allkeys-lru
    save 900 1
    save 300 10
    save 60 10000
    appendonly yes
    appendfsync everysec
```

## Messaging System (Kafka)

### Kafka Deployment
```yaml
# crm-kafka-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: crm-kafka
  namespace: crm-platform
  labels:
    app: crm-kafka
    tier: messaging
spec:
  serviceName: crm-kafka-headless
  replicas: 3
  selector:
    matchLabels:
      app: crm-kafka
  template:
    metadata:
      labels:
        app: crm-kafka
        tier: messaging
    spec:
      securityContext:
        fsGroup: 1001
      initContainers:
      - name: wait-for-zookeeper
        image: busybox:1.35
        command: ['sh', '-c', 'until nc -z crm-zookeeper-service 2181; do echo waiting for zookeeper; sleep 2; done;']
      containers:
      - name: kafka
        image: confluentinc/cp-kafka:latest
        ports:
        - containerPort: 9092
          name: kafka
        env:
        - name: KAFKA_BROKER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: KAFKA_ZOOKEEPER_CONNECT
          value: "crm-zookeeper-service:2181"
        - name: KAFKA_ADVERTISED_LISTENERS
          value: "PLAINTEXT://$(HOSTNAME).crm-kafka-headless.crm-platform.svc.cluster.local:9092"
        - name: KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR
          value: "3"
        - name: KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR
          value: "3"
        - name: KAFKA_TRANSACTION_STATE_LOG_MIN_ISR
          value: "2"
        - name: KAFKA_DEFAULT_REPLICATION_FACTOR
          value: "3"
        - name: KAFKA_MIN_INSYNC_REPLICAS
          value: "2"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        volumeMounts:
        - name: kafka-storage
          mountPath: /var/lib/kafka/data
        livenessProbe:
          exec:
            command:
            - sh
            - -c
            - "kafka-broker-api-versions --bootstrap-server localhost:9092"
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
        readinessProbe:
          exec:
            command:
            - sh
            - -c
            - "kafka-broker-api-versions --bootstrap-server localhost:9092"
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        securityContext:
          runAsUser: 1001
          runAsGroup: 1001
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          capabilities:
            drop:
            - ALL
      securityContext:
        runAsNonRoot: true
        fsGroup: 1001
  volumeClaimTemplates:
  - metadata:
      name: kafka-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
      storageClassName: fast-ssd
---
apiVersion: v1
kind: Service
metadata:
  name: crm-kafka-headless
  namespace: crm-platform
  labels:
    app: crm-kafka
spec:
  clusterIP: None  # Headless service for StatefulSet
  selector:
    app: crm-kafka
  ports:
  - port: 9092
    targetPort: 9092
---
apiVersion: v1
kind: Service
metadata:
  name: crm-kafka-service
  namespace: crm-platform
  labels:
    app: crm-kafka
spec:
  type: ClusterIP
  selector:
    app: crm-kafka
  ports:
  - port: 9092
    targetPort: 9092
```

### Zookeeper Deployment
```yaml
# crm-zookeeper-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: crm-zookeeper
  namespace: crm-platform
  labels:
    app: crm-zookeeper
    tier: coordination
spec:
  serviceName: crm-zookeeper-headless
  replicas: 3
  selector:
    matchLabels:
      app: crm-zookeeper
  template:
    metadata:
      labels:
        app: crm-zookeeper
        tier: coordination
    spec:
      securityContext:
        fsGroup: 1000
      containers:
      - name: zookeeper
        image: confluentinc/cp-zookeeper:latest
        ports:
        - containerPort: 2181
          name: client
        - containerPort: 2888
          name: server
        - containerPort: 3888
          name: election
        env:
        - name: ZOOKEEPER_SERVER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: ZOOKEEPER_CLIENT_PORT
          value: "2181"
        - name: ZOOKEEPER_TICK_TIME
          value: "2000"
        - name: ZOOKEEPER_INIT_LIMIT
          value: "5"
        - name: ZOOKEEPER_SYNC_LIMIT
          value: "2"
        - name: ZOOKEEPER_SERVERS
          value: "crm-zookeeper-0.crm-zookeeper-headless.crm-platform.svc.cluster.local:2888:3888;crm-zookeeper-1.crm-zookeeper-headless.crm-platform.svc.cluster.local:2888:3888;crm-zookeeper-2.crm-zookeeper-headless.crm-platform.svc.cluster.local:2888:3888"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: zookeeper-storage
          mountPath: /var/lib/zookeeper/data
        - name: zookeeper-log
          mountPath: /var/lib/zookeeper/log
        livenessProbe:
          exec:
            command:
            - sh
            - -c
            - "echo ruok | nc localhost 2181 | grep -q imok"
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          exec:
            command:
            - sh
            - -c
            - "echo ruok | nc localhost 2181 | grep -q imok"
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
        securityContext:
          runAsUser: 1000
          runAsGroup: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          capabilities:
            drop:
            - ALL
      securityContext:
        runAsNonRoot: true
        fsGroup: 1000
  volumeClaimTemplates:
  - metadata:
      name: zookeeper-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 5Gi
      storageClassName: fast-ssd
  - metadata:
      name: zookeeper-log
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 5Gi
      storageClassName: fast-ssd
---
apiVersion: v1
kind: Service
metadata:
  name: crm-zookeeper-service
  namespace: crm-platform
  labels:
    app: crm-zookeeper
spec:
  clusterIP: None  # Headless service for StatefulSet
  selector:
    app: crm-zookeeper
  ports:
  - name: client
    port: 2181
    targetPort: 2181
  - name: server
    port: 2888
    targetPort: 2888
  - name: election
    port: 3888
    targetPort: 3888
```

## Ingress and Load Balancing

### Ingress Controller
```yaml
# crm-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: crm-app-ingress
  namespace: crm-platform
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTP"
    nginx.ingress.kubernetes.io/configuration-snippet: |
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
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
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: crm-cert
  namespace: crm-platform
spec:
  secretName: crm-tls-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - crm.example.com
```

## Auto-Scaling Configuration

### Horizontal Pod Autoscaler
```yaml
# crm-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-app-hpa
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
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-redis-hpa
  namespace: crm-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-redis
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
  - type: Pods
    pods:
      metric:
        name: redis_connected_clients
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 180
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

## Configuration Management

### ConfigMaps and Secrets
```yaml
# crm-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: crm-app-config
  namespace: crm-platform
data:
  environment: "production"
  log_level: "info"
  redis_url: "redis://crm-redis-service:6379"
  kafka_servers: "crm-kafka-service:9092"
  feature_flags: |
    {
      "enable_new_ui": true,
      "beta_features": false,
      "debug_mode": false
    }
  database_options: |
    {
      "pool_size": 20,
      "max_overflow": 30,
      "pool_timeout": 30
    }
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: crm-app-env
  namespace: crm-platform
data:
  DJANGO_SETTINGS_MODULE: "crm.settings.production"
  PYTHONPATH: "/app"
  TZ: "UTC"
---
apiVersion: v1
kind: Secret
metadata:
  name: crm-db-secret
  namespace: crm-platform
type: Opaque
data:
  username: <base64-encoded-username>
  password: <base64-encoded-password>
  database: <base64-encoded-database-name>
  url: <base64-encoded-database-url>
---
apiVersion: v1
kind: Secret
metadata:
  name: crm-api-keys
  namespace: crm-platform
type: Opaque
data:
  twilio_sid: <base64-encoded-twilio-sid>
  twilio_token: <base64-encoded-twilio-token>
  gmail_oauth_token: <base64-encoded-gmail-token>
```

## Monitoring and Observability

### Service Monitor
```yaml
# crm-monitoring.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: crm-app-monitor
  namespace: crm-platform
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
    relabelings:
    - sourceLabels: [__meta_kubernetes_pod_name]
      targetLabel: pod
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

## Network Policies

### Network Security
```yaml
# crm-network-policies.yaml
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
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: crm-db
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: crm-redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app: crm-kafka
    ports:
    - protocol: TCP
      port: 9092
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53  # DNS
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
```

## Resource Management

### Resource Quotas and Limits
```yaml
# crm-resource-management.yaml
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
    secrets: "50"
    configmaps: "100"
    services: "20"
    pods: "50"
    replicationcontrollers: "20"
    resourcequotas: "1"
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
  - max:
      cpu: "2"
      memory: "4Gi"
    min:
      cpu: "50m"
      memory: "64Mi"
    type: Container
  - max:
      storage: "10Gi"
    min:
      storage: "1Gi"
    type: PersistentVolumeClaim
```

This comprehensive Kubernetes manifest guide provides all the necessary configurations for deploying and managing the CRM platform on Kubernetes.