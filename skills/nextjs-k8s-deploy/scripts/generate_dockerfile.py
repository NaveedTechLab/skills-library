#!/usr/bin/env python3
"""
Next.js Dockerfile Generator

This script creates a production-ready Dockerfile for Next.js applications.
"""

import os
import sys
import argparse
from pathlib import Path


def create_production_dockerfile(output_dir, app_path="."):
    """Create a multi-stage production-ready Dockerfile for Next.js."""
    dockerfile_content = f'''# Multi-stage build for Next.js application
# Stage 1: Build dependencies
FROM node:18-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY {app_path}/package.json {app_path}/package-lock.json ./

# Install dependencies
RUN npm ci --only=production

# Stage 2: Build the application
FROM node:18-alpine AS builder
WORKDIR /app

# Copy dependencies from previous stage
COPY --from=deps --chown=node:node /app/node_modules ./node_modules
COPY {app_path} .

# Build the application
RUN npm run build

# Stage 3: Production server
FROM node:18-alpine AS runner
WORKDIR /app

# Don't run production as root
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy dependencies from previous stage
COPY --from=deps --chown=nextjs:nodejs /app/node_modules ./node_modules

# Copy built application from builder stage
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV NODE_ENV production

# Final command to run the application
CMD ["node", "server.js"]
'''
    
    dockerfile_path = Path(output_dir) / "Dockerfile"
    with open(dockerfile_path, 'w') as f:
        f.write(dockerfile_content)
    
    print(f"Created production-ready Dockerfile: {dockerfile_path}")


def create_simple_dockerfile(output_dir, app_path="."):
    """Create a simple Dockerfile for Next.js (alternative approach)."""
    dockerfile_content = f'''# Simple Next.js Dockerfile
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY {app_path}/package.json {app_path}/package-lock.json ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY {app_path} .
RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app ./

EXPOSE 3000

ENV NODE_ENV=production

USER nextjs

CMD ["npm", "start"]
'''
    
    dockerfile_path = Path(output_dir) / "Dockerfile.simple"
    with open(dockerfile_path, 'w') as f:
        f.write(dockerfile_content)
    
    print(f"Created simple Dockerfile: {dockerfile_path}")


def main():
    parser = argparse.ArgumentParser(description='Generate production-ready Dockerfile for Next.js apps')
    parser.add_argument('--output', '-o', default='.', help='Output directory (default: current directory)')
    parser.add_argument('--app-path', '-p', default='.', help='Path to Next.js app (default: .)')
    parser.add_argument('--type', '-t', choices=['production', 'simple'], default='production', 
                       help='Type of Dockerfile to generate (default: production)')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating Dockerfile for Next.js app at '{args.app_path}' in {output_dir}")
    
    if args.type == 'production':
        create_production_dockerfile(output_dir, args.app_path)
    else:
        create_simple_dockerfile(output_dir, args.app_path)
    
    print("\\nDockerfile generated successfully!")


if __name__ == "__main__":
    main()