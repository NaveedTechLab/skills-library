# Monitoring Stack for Kubernetes

## Overview

This document provides comprehensive guidance on setting up a monitoring stack for the CRM platform deployed on Kubernetes. It covers Prometheus, Grafana, Loki, and other observability tools.

## Prometheus Setup

### Prometheus Configuration
```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
      scrape_timeout: 10s

    rule_files:
      - "/etc/prometheus/rules/*.rules"

    alerting:
      alertmanagers:
      - static_configs:
        - targets:
          - alertmanager:9093

    scrape_configs:
    - job_name: 'kubernetes-apiservers'
      kubernetes_sd_configs:
      - role: endpoints
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        insecure_skip_verify: true
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: default;kubernetes;https

    - job_name: 'kubernetes-nodes'
      kubernetes_sd_configs:
      - role: node
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        insecure_skip_verify: true
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
      - target_label: __address__
        replacement: kubernetes.default.svc:443
      - source_labels: [__meta_kubernetes_node_name]
        regex: (.+)
        target_label: __metrics_path__
        replacement: /api/v1/nodes/${1}/proxy/metrics

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
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: kubernetes_pod_name

    - job_name: 'kubernetes-cadvisor'
      kubernetes_sd_configs:
      - role: node
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        insecure_skip_verify: true
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
      - target_label: __address__
        replacement: kubernetes.default.svc:443
      - source_labels: [__meta_kubernetes_node_name]
        regex: (.+)
        target_label: __metrics_path__
        replacement: /api/v1/nodes/${1}/proxy/metrics/cadvisor

    - job_name: 'kubernetes-service-endpoints'
      kubernetes_sd_configs:
      - role: endpoints
      relabel_configs:
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scheme]
        action: replace
        target_label: __scheme__
        regex: (https?)
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_service_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
      - action: labelmap
        regex: __meta_kubernetes_service_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_service_name]
        action: replace
        target_label: kubernetes_name

    - job_name: 'kubernetes-ingresses'
      kubernetes_sd_configs:
      - role: ingress
      relabel_configs:
      - source_labels: [__meta_kubernetes_ingress_annotation_prometheus_io_probe]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_ingress_scheme,__address__,__meta_kubernetes_ingress_name,__meta_kubernetes_namespace]
        regex: (.+);(.+);(.+);(.+)
        replacement: ${1}://${2}{3}
        target_label: __param_target
      - target_label: __address__
        replacement: blackbox-exporter:9115
      - source_labels: [__param_target]
        target_label: instance
      - action: labelmap
        regex: __meta_kubernetes_ingress_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_ingress_name]
        target_label: kubernetes_name
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: monitoring
data:
  crm-alerts.rules: |
    groups:
    - name: crm-alerts
      rules:
      - alert: CRMPodDown
        expr: up{job="kubernetes-pods", app="crm-app"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "CRM Pod is down"
          description: "CRM pod {{ $labels.pod }} in namespace {{ $labels.namespace }} has been down for more than 5 minutes."

      - alert: CRMCPUHigh
        expr: 100 * (avg by(container, pod) (rate(container_cpu_usage_seconds_total{container="app", pod=~"crm-app.*"}[5m]))) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CRM CPU usage is high"
          description: "CRM pod {{ $labels.pod }} CPU usage is above 80% for more than 5 minutes."

      - alert: CRMMemoryHigh
        expr: (container_memory_working_set_bytes{container="app", pod=~"crm-app.*"} / container_spec_memory_limit_bytes{container="app", pod=~"crm-app.*"}) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CRM Memory usage is high"
          description: "CRM pod {{ $labels.pod }} memory usage is above 85% for more than 5 minutes."

      - alert: CRMRequestDurationHigh
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{app="crm-app"}[5m])) by (le)) > 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "CRM Request Duration is high"
          description: "95th percentile of CRM request duration is above 1 second for more than 2 minutes."

      - alert: CRMTrafficDrop
        expr: (sum(rate(http_requests_total{app="crm-app"}[5m])) / sum(rate(http_requests_total{app="crm-app"}[1h]))) < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "CRM Traffic Drop"
          description: "CRM traffic has dropped by more than 50% compared to the last hour."

      - alert: CRMDatabaseConnectionFailed
        expr: rate(crm_database_connection_failures_total[5m]) > 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "CRM Database Connection Failed"
          description: "CRM database connection failures detected in the last 5 minutes."

      - alert: CRMQueueDepthHigh
        expr: crm_task_queue_depth > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CRM Task Queue Depth is high"
          description: "CRM task queue depth is above 100 for more than 5 minutes."
```

### Prometheus Deployment
```yaml
# prometheus-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
  labels:
    app: prometheus
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      serviceAccountName: prometheus
      containers:
      - name: prometheus
        image: prom/prometheus:v2.40.0
        args:
        - '--config.file=/etc/prometheus/prometheus.yml'
        - '--storage.tsdb.path=/prometheus/'
        - '--web.console.libraries=/etc/prometheus/console_libraries'
        - '--web.console.templates=/etc/prometheus/consoles'
        - '--storage.tsdb.retention.time=200h'
        - '--web.enable-lifecycle'
        ports:
        - containerPort: 9090
        resources:
          requests:
            cpu: 200m
            memory: 1Gi
          limits:
            cpu: 500m
            memory: 2Gi
        volumeMounts:
        - name: prometheus-config-volume
          mountPath: /etc/prometheus/
        - name: prometheus-storage-volume
          mountPath: /prometheus/
      volumes:
      - name: prometheus-config-volume
        configMap:
          defaultMode: 420
          name: prometheus-config
      - name: prometheus-storage-volume
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus-service
  namespace: monitoring
  labels:
    app: prometheus
spec:
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
    nodePort: 30090
  type: NodePort
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus
rules:
- apiGroups: [""]
  resources:
  - nodes
  - nodes/proxy
  - services
  - endpoints
  - pods
  verbs: ["get", "list", "watch"]
- apiGroups:
  - extensions
  resources:
  - ingresses
  verbs: ["get", "list", "watch"]
- nonResourceURLs: ["/metrics"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:
- kind: ServiceAccount
  name: prometheus
  namespace: monitoring
```

## Grafana Setup

### Grafana Configuration
```yaml
# grafana-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-config
  namespace: monitoring
data:
  grafana.ini: |
    [analytics]
    check_for_updates = true

    [grafana_net]
    url = https://grafana.net

    [log]
    mode = console

    [paths]
    data = /var/lib/grafana/
    logs = /var/log/grafana
    plugins = /var/lib/grafana/plugins
    provisioning = /etc/grafana/provisioning

    [server]
    enable_gzip = true

    [users]
    default_theme = dark
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-service:9090
      access: proxy
      isDefault: true
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
  namespace: monitoring
data:
  dashboards.yaml: |
    apiVersion: 1
    providers:
    - name: 'default'
      orgId: 1
      folder: ''
      type: file
      disableDeletion: false
      editable: true
      options:
        path: /var/lib/grafana/dashboards
```

### Grafana Deployment
```yaml
# grafana-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
  labels:
    app: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:9.2.0
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: grafana-admin-credentials
              key: admin-password
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
          limits:
            cpu: 200m
            memory: 200Mi
        volumeMounts:
        - name: grafana-storage
          mountPath: /var/lib/grafana
        - name: grafana-config
          mountPath: /etc/grafana/grafana.ini
          subPath: grafana.ini
        - name: grafana-datasources
          mountPath: /etc/grafana/provisioning/datasources/datasources.yaml
          subPath: datasources.yaml
        - name: grafana-dashboards
          mountPath: /etc/grafana/provisioning/dashboards/dashboards.yaml
          subPath: dashboards.yaml
        - name: crm-dashboards
          mountPath: /var/lib/grafana/dashboards
      volumes:
      - name: grafana-storage
        emptyDir: {}
      - name: grafana-config
        configMap:
          name: grafana-config
      - name: grafana-datasources
        configMap:
          name: grafana-datasources
      - name: grafana-dashboards
        configMap:
          name: grafana-dashboards
      - name: crm-dashboards
        configMap:
          name: crm-dashboard-definition
---
apiVersion: v1
kind: Service
metadata:
  name: grafana-service
  namespace: monitoring
  labels:
    app: grafana
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000
    nodePort: 30030
  type: NodePort
---
apiVersion: v1
kind: Secret
metadata:
  name: grafana-admin-credentials
  namespace: monitoring
type: Opaque
data:
  admin-password: <base64-encoded-admin-password>
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: crm-dashboard-definition
  namespace: monitoring
data:
  crm-overview.json: |
    {
      "dashboard": {
        "id": null,
        "title": "CRM Platform Overview",
        "tags": ["crm", "platform", "kubernetes"],
        "timezone": "browser",
        "panels": [
          {
            "id": 1,
            "title": "CRM App Health",
            "type": "stat",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
            "targets": [
              {
                "expr": "sum(up{app=\"crm-app\"})",
                "legendFormat": "Healthy Pods"
              }
            ],
            "fieldConfig": {
              "defaults": {
                "unit": "none",
                "color": {
                  "mode": "thresholds"
                },
                "thresholds": {
                  "steps": [
                    {"color": "red", "value": 0},
                    {"color": "yellow", "value": 1},
                    {"color": "green", "value": 2}
                  ]
                }
              }
            }
          },
          {
            "id": 2,
            "title": "CRM CPU Usage",
            "type": "graph",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
            "targets": [
              {
                "expr": "100 * (avg by(container, pod) (rate(container_cpu_usage_seconds_total{container=\"app\", pod=~\"crm-app.*\"}[5m])))",
                "legendFormat": "{{pod}}"
              }
            ]
          },
          {
            "id": 3,
            "title": "CRM Memory Usage",
            "type": "graph",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
            "targets": [
              {
                "expr": "container_memory_working_set_bytes{container=\"app\", pod=~\"crm-app.*\"}",
                "legendFormat": "{{pod}}"
              }
            ]
          },
          {
            "id": 4,
            "title": "CRM Request Rate",
            "type": "graph",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
            "targets": [
              {
                "expr": "sum(rate(http_requests_total{app=\"crm-app\"}[5m])) by (method, handler)",
                "legendFormat": "{{method}} {{handler}}"
              }
            ]
          }
        ],
        "time": {"from": "now-6h", "to": "now"},
        "refresh": "30s"
      }
    }
```

## Loki and Promtail for Logging

### Loki Configuration
```yaml
# loki-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-config
  namespace: monitoring
data:
  loki.yaml: |
    auth_enabled: false

    server:
      http_listen_port: 3100

    common:
      path_prefix: /tmp/loki
      storage:
        filesystem:
          chunks_directory: /tmp/loki/chunks
          rules_directory: /tmp/loki/rules
      replication_factor: 1
      ring:
        instance_addr: 127.0.0.1
        kvstore:
          store: inmemory

    schema_config:
      configs:
      - from: 2020-10-24
        store: boltdb-shipper
        object_store: filesystem
        schema: v11
        index:
          prefix: index_
          period: 24h

    ruler:
      alertmanager_url: http://localhost:9093
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: loki
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: loki
  template:
    metadata:
      labels:
        app: loki
    spec:
      containers:
      - name: loki
        image: grafana/loki:2.6.1
        args: ["-config.file=/etc/loki/loki.yaml"]
        ports:
        - name: http-metrics
          containerPort: 3100
        volumeMounts:
        - name: loki-config
          mountPath: /etc/loki
        - name: loki-storage
          mountPath: /tmp/loki
        resources:
          limits:
            cpu: 1000m
            memory: 1024Mi
          requests:
            cpu: 100m
            memory: 128Mi
      volumes:
      - name: loki-config
        configMap:
          name: loki-config
      - name: loki-storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: loki-service
  namespace: monitoring
  labels:
    app: loki
spec:
  selector:
    app: loki
  ports:
  - port: 3100
    targetPort: 3100
    name: http-metrics
```

### Promtail Configuration
```yaml
# promtail-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: promtail-config
  namespace: monitoring
data:
  promtail.yaml: |
    server:
      http_listen_port: 9080
      grpc_listen_port: 0

    clients:
      - url: http://loki-service:3100/loki/api/v1/push

    scrape_configs:
    - job_name: kubernetes-pods
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels:
        - __meta_kubernetes_pod_annotation_promtail_io_scrape
        output_label: __scrape__
        action: replace
        regex: "true"
      - source_labels:
        - __meta_kubernetes_pod_annotation_promtail_io_path
        output_label: __path__
        action: replace
        regex: "(.+)"
      - source_labels:
        - __meta_kubernetes_pod_annotation_promtail_io_pipeline_stages
        output_label: __pipeline_stages__
        action: replace
        regex: "(.+)"
      - source_labels:
        - __meta_kubernetes_pod_name
        target_label: pod
      - source_labels:
        - __meta_kubernetes_namespace
        target_label: namespace
      - source_labels:
        - __meta_kubernetes_pod_container_name
        target_label: container
      - replacement: /var/log/pods/*/*/*.log
        target_label: __path__
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: promtail-daemonset
  namespace: monitoring
spec:
  selector:
    matchLabels:
      name: promtail
  template:
    metadata:
      labels:
        name: promtail
    spec:
      serviceAccount: promtail
      containers:
      - name: promtail
        image: grafana/promtail:2.6.1
        args:
        - "-config.file=/etc/promtail/promtail.yaml"
        - "-client.url=http://loki-service:3100/loki/api/v1/push"
        volumeMounts:
        - name: logs
          mountPath: /var/log
        - name: promtail-config
          mountPath: /etc/promtail
        - name: run
          mountPath: /run/promtail
        resources:
          limits:
            memory: 128Mi
            cpu: 500m
          requests:
            memory: 128Mi
            cpu: 500m
      volumes:
      - name: logs
        hostPath:
          path: /var/log
      - name: promtail-config
        configMap:
          name: promtail-config
      - name: run
        hostPath:
          path: /run/promtail
      tolerations:
      - effect: NoSchedule
        operator: Exists
      - effect: NoExecute
        operator: Exists
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: promtail
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: promtail
rules:
- apiGroups: [""]
  resources:
  - nodes
  - services
  - pods
  verbs:
  - get
  - watch
  - list
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: promtail
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: promtail
subjects:
- kind: ServiceAccount
  name: promtail
  namespace: monitoring
```

## Alertmanager Configuration

### Alertmanager Setup
```yaml
# alertmanager-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yaml: |
    global:
      smtp_smarthost: 'smtp.gmail.com:587'
      smtp_from: 'alerts@crm-platform.com'
      smtp_auth_username: 'alerts@crm-platform.com'
      smtp_auth_password: 'your-app-password'

    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 12h
      receiver: 'default-receiver'
      routes:
      - match:
          severity: critical
        receiver: 'critical-receiver'
        group_wait: 10s
        group_interval: 1m
        repeat_interval: 1h

    receivers:
    - name: 'default-receiver'
      email_configs:
      - to: 'admin@crm-platform.com'
        send_resolved: true
      slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        send_resolved: true
        title: '{{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'

    - name: 'critical-receiver'
      email_configs:
      - to: 'admin@crm-platform.com,ops@crm-platform.com'
        send_resolved: true
      slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/CRITICAL/WEBHOOK'
        channel: '#critical-alerts'
        send_resolved: true
        title: '{{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alertmanager
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alertmanager
  template:
    metadata:
      labels:
        app: alertmanager
    spec:
      containers:
      - name: alertmanager
        image: prom/alertmanager:v0.25.0
        args:
        - '--config.file=/etc/alertmanager/alertmanager.yaml'
        - '--storage.path=/alertmanager'
        ports:
        - containerPort: 9093
        volumeMounts:
        - name: config-volume
          mountPath: /etc/alertmanager/
        - name: storage-volume
          mountPath: /alertmanager/
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      volumes:
      - name: config-volume
        configMap:
          name: alertmanager-config
      - name: storage-volume
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: alertmanager-service
  namespace: monitoring
  labels:
    app: alertmanager
spec:
  selector:
    app: alertmanager
  ports:
  - port: 9093
    targetPort: 9093
    name: http
  type: ClusterIP
```

## Service Monitor Configuration

### Custom Service Monitor for CRM
```yaml
# crm-service-monitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: crm-app-monitor
  namespace: monitoring
  labels:
    app: crm-app
    team: monitoring
spec:
  selector:
    matchLabels:
      app: crm-app
  namespaceSelector:
    matchNames:
    - crm-platform
  endpoints:
  - port: http
    interval: 30s
    path: /metrics
    relabelings:
    - sourceLabels: [__meta_kubernetes_pod_name]
      targetLabel: pod
    - sourceLabels: [__meta_kubernetes_namespace]
      targetLabel: namespace
    - sourceLabels: [__meta_kubernetes_pod_label_app]
      targetLabel: app
    metricRelabelings:
    - sourceLabels: [__name__]
      regex: 'http_.*'
      action: keep
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: crm-db-monitor
  namespace: monitoring
  labels:
    app: crm-db
    team: monitoring
spec:
  selector:
    matchLabels:
      app: crm-db
  namespaceSelector:
    matchNames:
    - crm-platform
  endpoints:
  - port: postgres
    interval: 60s
    path: /metrics
    scheme: http
    params:
      collect[]:
        - "postgres_database"
        - "postgres_bgwriter"
        - "postgres_locks"
    relabelings:
    - sourceLabels: [__meta_kubernetes_pod_name]
      targetLabel: pod
    - sourceLabels: [__meta_kubernetes_namespace]
      targetLabel: namespace
    - sourceLabels: [__meta_kubernetes_pod_label_app]
      targetLabel: app
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: crm-kafka-monitor
  namespace: monitoring
  labels:
    app: crm-kafka
    team: monitoring
spec:
  selector:
    matchLabels:
      app: crm-kafka
  namespaceSelector:
    matchNames:
    - crm-platform
  endpoints:
  - port: kafka
    interval: 30s
    path: /metrics
    scheme: http
    relabelings:
    - sourceLabels: [__meta_kubernetes_pod_name]
      targetLabel: pod
    - sourceLabels: [__meta_kubernetes_namespace]
      targetLabel: namespace
    - sourceLabels: [__meta_kubernetes_pod_label_app]
      targetLabel: app
```

## Node Exporter for Infrastructure Metrics

### Node Exporter Setup
```yaml
# node-exporter.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostPID: true
      hostIPC: true
      hostNetwork: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.4.0
        ports:
        - containerPort: 9100
          protocol: TCP
          name: http-metrics
        args:
        - --path.procfs
        - /host/proc
        - --path.sysfs
        - /host/sys
        - --collector.filesystem.ignored-mount-points
        - '"^/(sys|proc|dev|host|etc)($|/)"'
        resources:
          requests:
            cpu: 0.15
            memory: 512Mi
          limits:
            cpu: 0.15
            memory: 512Mi
        volumeMounts:
        - name: dev
          mountPath: /host/dev
        - name: proc
          mountPath: /host/proc
        - name: sys
          mountPath: /host/sys
        - name: rootfs
          mountPath: /rootfs
        securityContext:
          privileged: true
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: dev
        hostPath:
          path: /dev
      - name: sys
        hostPath:
          path: /sys
      - name: rootfs
        hostPath:
          path: /
      tolerations:
      - effect: NoSchedule
        operator: Exists
      - effect: NoExecute
        operator: Exists
---
apiVersion: v1
kind: Service
metadata:
  annotations:
    prometheus.io/scrape: 'true'
    prometheus.io/port: '9100'
  name: node-exporter-service
  namespace: monitoring
spec:
  clusterIP: None
  ports:
  - port: 9100
    protocol: TCP
    targetPort: 9100
  selector:
    app: node-exporter
```

## Monitoring Best Practices

### Health Check Endpoints
```python
# health_check.py
from flask import Flask, jsonify
import requests
import os
import time

app = Flask(__name__)

@app.route('/health')
def health():
    """Liveness probe - check if the app is running"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "version": os.environ.get("VERSION", "unknown")
    }), 200

@app.route('/ready')
def ready():
    """Readiness probe - check if the app is ready to serve traffic"""
    checks = {
        "database": check_database_connection(),
        "redis": check_redis_connection(),
        "external_api": check_external_api(),
    }

    if all(checks.values()):
        return jsonify({
            "status": "ready",
            "checks": checks,
            "timestamp": time.time()
        }), 200
    else:
        return jsonify({
            "status": "not_ready",
            "checks": checks,
            "timestamp": time.time()
        }), 503

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    # This would typically be handled by a metrics library
    # For example, using prometheus-client in Python
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    # Generate metrics
    # ... metric collection code ...

    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

def check_database_connection():
    """Check database connectivity"""
    try:
        # Replace with your actual database check
        # For example, with SQLAlchemy:
        # db.session.execute(text('SELECT 1')).fetchone()
        return True
    except Exception:
        return False

def check_redis_connection():
    """Check Redis connectivity"""
    try:
        # Replace with your actual Redis check
        # For example, with redis-py:
        # redis_client.ping()
        return True
    except Exception:
        return False

def check_external_api():
    """Check external API connectivity"""
    try:
        # Replace with your actual external API check
        response = requests.get('https://api.example.com/health', timeout=5)
        return response.status_code == 200
    except Exception:
        return False

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

This comprehensive monitoring stack provides all the necessary components for monitoring the CRM platform on Kubernetes, including metrics collection, visualization, alerting, and logging.