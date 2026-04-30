---
name: nextjs-k8s-deploy
description: Containerize and deploy Next.js applications to Kubernetes. Use when Claude needs to create Dockerfiles, Kubernetes manifests, or Helm charts for Next.js applications. Dockerfile-driven builds, Kubernetes manifests or Helm only, no frontend feature design.
---

# Next.js Kubernetes Deployment

This skill containerizes and deploys Next.js applications to Kubernetes. It generates a production-optimized multi-stage Dockerfile, Kubernetes Deployment/Service/Ingress manifests, and verifies the rollout — turning a Next.js codebase into a running Kubernetes service without manual YAML authoring.

Use this skill when you need to move a Next.js app from local development to a Kubernetes cluster.

## Quick Start

```bash
# Deploy the Next.js app in the current directory
/nextjs-k8s-deploy namespace=frontend replicas=2 image_tag=v1.0.0

# Output files:
# - Dockerfile (multi-stage)
# - k8s/deployment.yaml
# - k8s/service.yaml
# - k8s/ingress.yaml
```

```bash
# Apply to cluster
kubectl apply -f k8s/
kubectl rollout status deployment/nextjs-app -n frontend
```

## Key Features

- Generates a multi-stage Dockerfile optimized for Next.js (build + slim runtime stage)
- Produces Kubernetes `Deployment` manifest with configurable replicas and resource limits
- Produces `Service` (ClusterIP/LoadBalancer) and `Ingress` manifests
- Applies manifests via `kubectl apply` and verifies pod readiness
- Supports standalone output mode (`output: 'standalone'` in `next.config.js`) for smallest image size

## Process

1. Generate a production-ready Dockerfile
2. Create Kubernetes manifests (Deployment, Service, Ingress)
3. Apply the manifests to the cluster
4. Verify deployment status before finishing

The deployment process is handled by supporting scripts that create and apply all manifests.

## When NOT to Use This Skill

- **Static export sites** — use `docusaurus-deploy` or a CDN; a running Node.js container is unnecessary for pure static output
- **Vercel / Netlify deployments** — those platforms handle containerization automatically; Kubernetes adds unneeded complexity
- **Frontend feature work** — this skill only handles infra; use `nextjs-ui-builder` for building UI components

## Common Mistakes

- Not setting `output: 'standalone'` in `next.config.js` — results in a bloated image that copies all `node_modules` instead of just required files
- Forgetting to set `NEXT_PUBLIC_*` environment variables at build time — these are baked into the bundle, not runtime-injectable
- Using `imagePullPolicy: Always` without a registry — causes `ErrImagePull` on nodes that can't reach Docker Hub

## Related Skills

- [`nextjs-ui-builder`](../nextjs-ui-builder/SKILL.md) — Build the Next.js frontend before deploying
- [`k8s-foundation`](../k8s-foundation/SKILL.md) — Kubernetes cluster setup required before deployment
- [`kubernetes-deployer`](../kubernetes-deployer/SKILL.md) — General-purpose Kubernetes deployment for any app type
