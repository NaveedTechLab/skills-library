# Helm Charts Reference

## Table of Contents
1. [Chart Structure](#chart-structure)
2. [Values Configuration](#values-configuration)
3. [Template Patterns](#template-patterns)
4. [Common Commands](#common-commands)

---

## Chart Structure

```
charts/<app-name>/
├── Chart.yaml           # Chart metadata
├── values.yaml          # Default configuration
├── templates/
│   ├── _helpers.tpl     # Template helpers
│   ├── deployment.yaml  # Deployment manifest
│   ├── service.yaml     # Service manifest
│   ├── configmap.yaml   # ConfigMap (optional)
│   ├── secret.yaml      # Secret (optional)
│   ├── ingress.yaml     # Ingress (optional)
│   └── hpa.yaml         # HorizontalPodAutoscaler (optional)
└── .helmignore          # Files to ignore
```

### Chart.yaml

```yaml
apiVersion: v2
name: myapp
description: A Helm chart for MyApp
type: application
version: 0.1.0        # Chart version
appVersion: "1.0.0"   # Application version
```

---

## Values Configuration

### values.yaml

```yaml
# Image configuration
image:
  repository: myapp
  tag: latest
  pullPolicy: IfNotPresent

# Replica count
replicaCount: 2

# Service configuration
service:
  type: ClusterIP
  port: 80
  targetPort: 8000

# Resource limits
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

# Environment variables
env:
  - name: LOG_LEVEL
    value: "info"

# Environment from secrets/configmaps
envFrom: []
  # - secretRef:
  #     name: app-secrets
  # - configMapRef:
  #     name: app-config

# Probes
livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: http
  initialDelaySeconds: 5
  periodSeconds: 5

# Ingress
ingress:
  enabled: false
  className: nginx
  hosts:
    - host: myapp.local
      paths:
        - path: /
          pathType: Prefix

# Autoscaling
autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

# Node selector
nodeSelector: {}

# Tolerations
tolerations: []

# Affinity
affinity: {}
```

### Environment-Specific Overrides

```yaml
# values-dev.yaml
replicaCount: 1
resources:
  limits:
    cpu: 200m
    memory: 256Mi

# values-prod.yaml
replicaCount: 3
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
```

---

## Template Patterns

### _helpers.tpl

```yaml
{{/*
Expand the name of the chart.
*/}}
{{- define "myapp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "myapp.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "myapp.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "myapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "myapp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "myapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

### deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "myapp.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "myapp.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort }}
              protocol: TCP
          {{- with .Values.env }}
          env:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.envFrom }}
          envFrom:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.livenessProbe }}
          livenessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.readinessProbe }}
          readinessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

### service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
      protocol: TCP
      name: http
  selector:
    {{- include "myapp.selectorLabels" . | nindent 4 }}
```

---

## Common Commands

### Development

```bash
# Create new chart
helm create mychart

# Lint chart
helm lint ./charts/myapp

# Template locally (dry-run)
helm template myapp ./charts/myapp -f values-dev.yaml

# Install/upgrade
helm upgrade --install myapp ./charts/myapp \
  -f values.yaml \
  -f values-dev.yaml \
  --namespace myapp \
  --create-namespace

# Uninstall
helm uninstall myapp -n myapp
```

### Debugging

```bash
# Show computed values
helm get values myapp -n myapp

# Show all manifests
helm get manifest myapp -n myapp

# Debug template rendering
helm template myapp ./charts/myapp --debug

# Dry-run install
helm upgrade --install myapp ./charts/myapp --dry-run --debug
```

### Image Tag Override

```bash
# Override image tag at deploy time
helm upgrade --install myapp ./charts/myapp \
  --set image.tag=v1.2.3
```
