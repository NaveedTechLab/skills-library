---
name: kubernetes-deployer
description: Package and deploy applications to Kubernetes with Dockerfiles, Helm charts, and local Minikube deployment. Use when containerizing applications, creating Kubernetes manifests, setting up Helm charts, deploying to Minikube, or preparing cloud-ready configurations. Focuses on local-first deployment with stateless services.
---

# Kubernetes Deployer

Deploy applications to Kubernetes with production-ready configurations, starting locally with Minikube.

## Deployment Workflow

```
1. Dockerfile     → Containerize application
2. Helm Chart     → Package Kubernetes manifests
3. Local Deploy   → Test in Minikube
4. Cloud Ready    → Configure for production
```

## Quick Start: Local Deployment

### 1. Create Dockerfile

```dockerfile
# Python example (see references for other languages)
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

FROM python:3.11-slim
WORKDIR /app
RUN useradd -m -u 1000 appuser
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY app ./app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Copy Helm Chart Template

Copy `assets/helm-template/` to `charts/<app-name>/` and customize:

```bash
cp -r assets/helm-template charts/myapp
# Edit Chart.yaml: name, description
# Edit values.yaml: image, ports, resources
```

### 3. Deploy to Minikube

```bash
# Start Minikube
minikube start

# Build image in Minikube's Docker
eval $(minikube docker-env)
docker build -t myapp:local .

# Deploy with Helm
helm upgrade --install myapp ./charts/myapp \
  --set image.repository=myapp \
  --set image.tag=local \
  --set image.pullPolicy=Never

# Access service
kubectl port-forward svc/myapp 8080:80
```

## Core Principles

1. **Local-first** - Test everything in Minikube before cloud
2. **Stateless services** - No local state; use external databases
3. **Config via env vars** - All configuration through environment
4. **12-factor ready** - Portable between environments

## Helm Chart Structure

```
charts/<app-name>/
├── Chart.yaml        # Metadata
├── values.yaml       # Default config
└── templates/
    ├── _helpers.tpl  # Template functions
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml  # Optional
    └── hpa.yaml      # Optional
```

## Configuration Patterns

### Environment Variables

```yaml
# values.yaml
env:
  - name: DATABASE_URL
    value: "postgresql://..."
  - name: LOG_LEVEL
    value: "info"

# From secrets
envFrom:
  - secretRef:
      name: app-secrets
```

### Create Secret

```bash
kubectl create secret generic app-secrets \
  --from-literal=DATABASE_PASSWORD=secret123 \
  --from-literal=API_KEY=key456
```

### Health Checks

```yaml
# values.yaml
livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 5
```

## Common Commands

### Minikube

```bash
minikube start                    # Start cluster
minikube dashboard                # Open dashboard
eval $(minikube docker-env)       # Use Minikube Docker
minikube service myapp --url      # Get service URL
```

### Helm

```bash
helm lint ./charts/myapp                    # Validate chart
helm template myapp ./charts/myapp          # Preview manifests
helm upgrade --install myapp ./charts/myapp # Deploy
helm uninstall myapp                        # Remove
```

### Kubectl

```bash
kubectl get pods                  # List pods
kubectl logs <pod>                # View logs
kubectl describe pod <pod>        # Debug pod
kubectl port-forward svc/myapp 8080:80  # Access locally
```

## Environment-Specific Values

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
  maxReplicas: 10
```

Deploy with environment:
```bash
helm upgrade --install myapp ./charts/myapp \
  -f values.yaml \
  -f values-prod.yaml
```

## Troubleshooting

| Issue | Command |
|-------|---------|
| Pod not starting | `kubectl describe pod <name>` |
| Image not found | `minikube ssh docker images` |
| Service unreachable | `kubectl get endpoints` |
| Logs | `kubectl logs <pod> -f` |

## References

- [references/dockerfile-patterns.md](references/dockerfile-patterns.md) - Multi-stage builds, language templates, security
- [references/helm-charts.md](references/helm-charts.md) - Chart structure, templates, values configuration
- [references/minikube-local.md](references/minikube-local.md) - Local images, service access, debugging

## Assets

- [assets/helm-template/](assets/helm-template/) - Ready-to-use Helm chart template

---

## When NOT to Use This

- **Single-container hobby projects** — Use `docker run` or docker-compose; Kubernetes is overkill
- **Stateful apps without a storage plan** — Databases need PersistentVolumeClaims and backup strategy; don't deploy stateful services without planning this first
- **Teams with no K8s knowledge** — K8s adds operational complexity; ensure at least one team member understands it
- **Serverless workloads** — Use AWS Lambda / Cloud Run for event-driven, short-lived tasks
- **You just need a quick demo** — Use Render, Railway, or Fly.io for instant deploys without K8s overhead

---

## Common Mistakes

1. **No resource limits set** — Without `resources.limits`, one pod can starve others; always set CPU and memory limits
2. **Using `imagePullPolicy: Always` with local images** — In Minikube, use `Never`; `Always` will try to pull from a registry that doesn't have your local image
3. **Storing secrets in `values.yaml`** — Never commit real secrets to Git; use `kubectl create secret` or an external secrets manager
4. **No readiness probe** — Without it, K8s sends traffic to pods before they're ready, causing 502 errors during deployments
5. **Single replica in production** — Always run `replicaCount: 2+` for zero-downtime rolling updates
6. **Not setting `terminationGracePeriodSeconds`** — Abrupt pod kills cause in-flight request drops; set to 30s minimum
7. **Skipping `helm lint`** — Always lint before deploying; catches YAML errors that would fail silently

---

## Performance Tips

- **Enable Horizontal Pod Autoscaler (HPA)** — Set `autoscaling.enabled: true` with CPU target 70%; handles traffic spikes automatically
- **Use `topologySpreadConstraints`** — Spread pods across nodes to avoid single-node failure taking down your entire service
- **Set Pod Disruption Budget (PDB)** — Ensures at least 1 pod stays running during node maintenance
- **Use `preStop` hook** — Add a 5s sleep in `preStop` to let load balancers drain connections before pod termination
- **Tune `initialDelaySeconds`** — Match it to your app's actual startup time; too low = false failures, too high = slow rollouts
- **Use `startupProbe` for slow-starting apps** — Separate startup detection from liveness checks

---

## Real Production Example

**FastAPI + PostgreSQL deployed to Minikube (hackathon production system)**:

```bash
# 1. Build image
eval $(minikube docker-env)
docker build -t crm-api:v1 .

# 2. Deploy app
helm upgrade --install crm-api ./charts/crm-api \
  --set image.tag=v1 \
  --set image.pullPolicy=Never \
  --set replicaCount=2 \
  --set resources.limits.cpu=500m \
  --set resources.limits.memory=512Mi

# 3. Deploy PostgreSQL
helm repo add bitnami https://charts.bitnami.com/bitnami
helm upgrade --install crm-db bitnami/postgresql \
  --set auth.password=secret123 \
  --set primary.resources.limits.memory=256Mi

# 4. Expose & verify
kubectl port-forward svc/crm-api 8000:80
curl http://localhost:8000/health
# {"status": "ok", "db": "connected"}
```

Result: 2-replica API, auto-restarts on crash, rolling updates with zero downtime.

---

## Related Skills

- [`k8s-foundation`](../k8s-foundation/SKILL.md) — Learn Kubernetes fundamentals first
- [`fastapi-backend-builder`](../fastapi-backend-builder/SKILL.md) — Build the app before deploying it
- [`argocd-app-deployment`](../argocd-app-deployment/SKILL.md) — GitOps continuous deployment on top of this
- [`prometheus-grafana-setup`](../prometheus-grafana-setup/SKILL.md) — Monitor your deployed app
- [`postgres-k8s-setup`](../postgres-k8s-setup/SKILL.md) — Deploy PostgreSQL alongside your app
