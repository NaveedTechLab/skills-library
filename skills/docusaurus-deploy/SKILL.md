---
name: docusaurus-deploy
description: Deploy Docusaurus documentation site to Kubernetes. Use when Claude needs to deploy static Docusaurus sites specifically to a Kubernetes cluster. For GitHub Pages deployment, use docusaurus-deployer instead.
---

# Docusaurus Kubernetes Deployment

> **Note:** For GitHub Pages deployment (the most common use case), see [`docusaurus-deployer`](../docusaurus-deployer/SKILL.md) which is more complete and includes CI/CD automation, local validation, and troubleshooting guides.

This skill handles Kubernetes-specific deployment of Docusaurus documentation sites — containerizing the static build and running it as a Kubernetes service.

## Quick Start

```bash
# Build the Docusaurus site locally first
npm run build

# Then invoke this skill to containerize and deploy
/docusaurus-deploy target=kubernetes namespace=docs
```

## Key Features

- Builds the Docusaurus static site using `npm run build`
- Creates a minimal nginx-based Docker image for serving the static output
- Generates Kubernetes `Deployment`, `Service`, and `Ingress` manifests
- Applies manifests to the specified namespace
- Verifies pod readiness before returning the service URL

## When NOT to Use This Skill

- **GitHub Pages deployments** — use `docusaurus-deployer` instead, which has full CI/CD and GitHub Actions support
- **Netlify / Vercel / static hosting** — use your hosting provider's CLI directly; Kubernetes adds unnecessary complexity
- **Local development previews** — use `npm run serve` directly; no containerization needed

## Common Mistakes

- Forgetting to set `baseUrl` in `docusaurus.config.ts` to match the Kubernetes Ingress path — causes broken CSS/JS links
- Using the dev server image in production (no `npm run build` step) — results in slow, hot-reload-enabled containers
- Not configuring resource requests/limits — docs pods can be evicted under cluster memory pressure

## Related Skills

- [`docusaurus-deployer`](../docusaurus-deployer/SKILL.md) — Full GitHub Pages deployment with CI/CD (preferred for most projects)
- [`k8s-foundation`](../k8s-foundation/SKILL.md) — Kubernetes cluster setup fundamentals
- [`nextjs-k8s-deploy`](../nextjs-k8s-deploy/SKILL.md) — Similar pattern for Next.js apps on Kubernetes
