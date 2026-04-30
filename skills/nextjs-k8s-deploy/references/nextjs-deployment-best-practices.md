# Next.js Deployment Best Practices

## Dockerfile Optimization

### Multi-stage Builds
- Use multi-stage builds to minimize image size
- Separate dependency installation, build, and runtime stages
- Copy only necessary files to each stage
- Use build cache effectively by copying package files first

### Base Image Selection
- Use official Node.js Alpine images for smaller footprint
- Pin to specific versions for reproducible builds
- Consider using Node.js LTS versions for stability

### Layer Caching
```dockerfile
# Copy package files first to leverage layer caching
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./

# Install dependencies
RUN if [ -f 'yarn.lock' ]; then yarn --frozen-lockfile; \\
    elif [ -f 'pnpm-lock.yaml' ]; then yarn global add pnpm && pnpm i --frozen-lockfile; \\
    else npm ci; \\
    fi

# Copy application code after dependencies
COPY . .
```

### Security Considerations
- Use non-root user for running the application
- Set appropriate file permissions
- Avoid installing unnecessary packages in production image
- Regularly update base images for security patches

## Next.js Specific Optimizations

### Static Export vs Server-Side Rendering
- Use `output: 'standalone'` in next.config.js for optimized server builds
- Leverage Next.js 12+ standalone output for smaller Docker images
- Consider static export for fully static sites

### Build Configuration
```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // Creates optimized standalone output
  experimental: {
    outputFileTracingRoot: path.join(__dirname, '../..'),
  },
}

module.exports = nextConfig
```

### Environment Variables
- Use NEXT_PUBLIC_ prefix for client-side accessible variables
- Inject environment variables at runtime, not build time
- Use Kubernetes ConfigMaps and Secrets for configuration

## Kubernetes Deployment Patterns

### Resource Management
- Set appropriate resource requests and limits
- Use Vertical Pod Autoscaler (VPA) for resource optimization
- Configure liveness and readiness probes appropriately

### Example Deployment Configuration
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nextjs-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nextjs-app
  template:
    metadata:
      labels:
        app: nextjs-app
    spec:
      containers:
      - name: nextjs-app
        image: nextjs-app:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Health Checks
- Implement proper health check endpoints
- Use appropriate probe timeouts and thresholds
- Consider startup probes for slower applications

### Networking
- Use Ingress controllers for external access
- Configure proper SSL/TLS termination
- Implement rate limiting at the Ingress level

## Performance Optimization

### Caching Strategies
- Implement proper HTTP caching headers
- Use CDN for static assets
- Configure proxy caching for API routes

### Auto-scaling
- Configure Horizontal Pod Autoscaler (HPA) based on CPU/memory
- Consider custom metrics for scaling decisions
- Set appropriate min/max replica counts

### Example HPA Configuration
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nextjs-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nextjs-app
  minReplicas: 3
  maxReplicas: 10
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
```

## Security Best Practices

### Image Security
- Scan images for vulnerabilities
- Use minimal base images
- Keep images updated with security patches

### Runtime Security
- Run containers as non-root user
- Drop unnecessary capabilities
- Use read-only root filesystem where possible

### Network Security
- Implement Network Policies for isolation
- Use TLS for all communications
- Configure proper RBAC permissions

## Monitoring and Observability

### Logging
- Use structured logging
- Centralize logs with tools like ELK or Loki
- Include correlation IDs for request tracing

### Metrics
- Enable application metrics
- Monitor key Next.js metrics (response times, error rates)
- Use Prometheus for metric collection

### Distributed Tracing
- Implement distributed tracing
- Use tools like Jaeger or Zipkin
- Trace requests across services

## CI/CD Pipeline Considerations

### Build Optimization
- Use build caching in CI/CD pipelines
- Implement multi-stage builds in pipeline
- Tag images with commit hashes for traceability

### Deployment Strategies
- Use blue-green or canary deployments
- Implement proper rollout strategies
- Configure automated rollbacks

### Example Deployment Pipeline
```yaml
# Example GitHub Actions workflow
name: Deploy Next.js App
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: |
        docker build -t nextjs-app:${{ github.sha }} .

    - name: Push to registry
      run: |
        docker tag nextjs-app:${{ github.sha }} registry/nextjs-app:${{ github.sha }}
        docker push registry/nextjs-app:${{ github.sha }}

    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/nextjs-app nextjs-app=registry/nextjs-app:${{ github.sha }}
```

## Common Anti-Patterns to Avoid

1. **Large Images**: Avoid installing dev dependencies in production images
2. **Root Execution**: Never run Next.js apps as root user
3. **Missing Probes**: Always configure liveness and readiness probes
4. **No Resource Limits**: Always set resource requests and limits
5. **Environment Mixing**: Don't mix build-time and runtime environment variables
6. **Insecure Defaults**: Don't use default Next.js server configurations in production
7. **Monolithic Builds**: Don't create overly large Docker images
8. **No Monitoring**: Always implement proper observability

## Troubleshooting Common Issues

### Slow Builds
- Check Docker layer caching configuration
- Optimize dependency installation order
- Consider using build caches in CI/CD

### Memory Issues
- Monitor resource usage and adjust limits
- Optimize Next.js build configuration
- Check for memory leaks in application code

### Cold Starts
- Use appropriate instance types
- Consider using container warmers
- Optimize application startup time

### Networking Problems
- Verify Ingress configuration
- Check Service and Endpoint configurations
- Validate DNS resolution

## Configuration Templates

### Production next.config.js
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    outputFileTracingRoot: path.join(__dirname, '../..'),
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ]
  },
}

module.exports = nextConfig
```

### Dockerfile for Production
```dockerfile
# Multi-stage build for Next.js application
FROM node:18-alpine AS deps
WORKDIR /app
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN if [ -f 'yarn.lock' ]; then yarn --frozen-lockfile; \\
    elif [ -f 'pnpm-lock.yaml' ]; then yarn global add pnpm && pnpm i --frozen-lockfile; \\
    else npm ci; \\
    fi

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN if [ -f 'yarn.lock' ]; then yarn build; \\
    elif [ -f 'pnpm-lock.yaml' ]; then yarn global add pnpm && pnpm build; \\
    else npm run build; \\
    fi

FROM node:18-alpine AS runner
WORKDIR /app
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
USER nextjs
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
EXPOSE 3000
ENV NODE_ENV=production
CMD ["node", "server.js"]
```

Following these best practices ensures robust, secure, and performant Next.js deployments on Kubernetes.