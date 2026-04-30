---
name: docusaurus-deploy
description: Deploy Docusaurus documentation site on Kubernetes. Use when Claude needs to deploy static Docusaurus sites to Kubernetes. Static site build and deploy only, no content authoring, verification via service availability.
---

# Docusaurus Deployment

This skill deploys Docusaurus documentation sites to various targets.

## Usage
Use this skill when you need to deploy a Docusaurus documentation site. The skill will:
1. Build the Docusaurus site
2. Validate the environment
3. Deploy to the specified target
4. Return a clean deployment URL

## Process
The deployment process is handled by the supporting scripts which:
- Build the Docusaurus static site
- Validate environment requirements
- Deploy to the specified target (Kubernetes, static hosting, etc.)
- Verify deployment status
- Return a clean URL to the deployed site