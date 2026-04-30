---
name: nextjs-k8s-deploy
description: Containerize and deploy Next.js applications to Kubernetes. Use when Claude needs to create Dockerfiles, Kubernetes manifests, or Helm charts for Next.js applications. Dockerfile-driven builds, Kubernetes manifests or Helm only, no frontend feature design.
---

# Next.js Kubernetes Deployment

This skill containerizes and deploys Next.js applications to Kubernetes.

## Usage
Use this skill when you need to deploy a Next.js application to Kubernetes. The skill will:
1. Generate a production-ready Dockerfile
2. Create Kubernetes manifests (Deployment, Service, Ingress)
3. Verify the deployment status

## Process
The deployment process is handled by the supporting scripts which:
- Create a multi-stage Dockerfile optimized for Next.js
- Generate Kubernetes Deployment manifest
- Generate Kubernetes Service manifest
- Generate Kubernetes Ingress manifest
- Apply the manifests to the cluster
- Verify deployment status before finishing