# Minikube Local Deployment

## Table of Contents
1. [Setup](#setup)
2. [Local Image Workflow](#local-image-workflow)
3. [Service Access](#service-access)
4. [Troubleshooting](#troubleshooting)

---

## Setup

### Start Minikube

```bash
# Start with recommended resources
minikube start --cpus=4 --memory=8192 --driver=docker

# Enable useful addons
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable dashboard
```

### Verify Cluster

```bash
kubectl cluster-info
kubectl get nodes
```

---

## Local Image Workflow

### Option 1: Use Minikube's Docker Daemon (Recommended)

```bash
# Point shell to Minikube's Docker
eval $(minikube docker-env)

# Build image (now builds directly in Minikube)
docker build -t myapp:local .

# Use in deployment with imagePullPolicy: Never
```

**deployment.yaml:**
```yaml
spec:
  containers:
    - name: myapp
      image: myapp:local
      imagePullPolicy: Never  # Critical for local images
```

### Option 2: Load Image into Minikube

```bash
# Build locally
docker build -t myapp:local .

# Load into Minikube
minikube image load myapp:local
```

### Option 3: Local Registry

```bash
# Start local registry
docker run -d -p 5000:5000 --name registry registry:2

# Tag and push
docker tag myapp:local localhost:5000/myapp:local
docker push localhost:5000/myapp:local

# Use in deployment
# image: localhost:5000/myapp:local
```

---

## Service Access

### Port Forward (Quick Access)

```bash
# Forward service port to localhost
kubectl port-forward svc/myapp 8080:80 -n default

# Access at http://localhost:8080
```

### NodePort Service

```yaml
# service.yaml
spec:
  type: NodePort
  ports:
    - port: 80
      targetPort: 8000
      nodePort: 30080  # Fixed port (30000-32767)
```

```bash
# Get Minikube IP
minikube ip

# Access at http://<minikube-ip>:30080
```

### Minikube Service Command

```bash
# Open service in browser
minikube service myapp -n default

# Get URL without opening
minikube service myapp -n default --url
```

### Ingress Access

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp
                port:
                  number: 80
```

```bash
# Add to /etc/hosts
echo "$(minikube ip) myapp.local" | sudo tee -a /etc/hosts

# Access at http://myapp.local
```

---

## Troubleshooting

### Common Issues

#### Image Pull Errors

```bash
# Check if image exists in Minikube
minikube ssh docker images | grep myapp

# Ensure imagePullPolicy: Never for local images
```

#### Pod Not Starting

```bash
# Check pod status
kubectl get pods -n default

# Describe pod for events
kubectl describe pod <pod-name> -n default

# Check logs
kubectl logs <pod-name> -n default
```

#### Service Not Accessible

```bash
# Verify service exists
kubectl get svc -n default

# Check endpoints
kubectl get endpoints myapp -n default

# Test from within cluster
kubectl run curl --rm -it --image=curlimages/curl -- curl http://myapp:80/health
```

### Useful Commands

```bash
# Dashboard
minikube dashboard

# SSH into Minikube VM
minikube ssh

# Check Minikube status
minikube status

# View logs
minikube logs

# Reset environment
minikube delete && minikube start
```

### Resource Cleanup

```bash
# Delete all resources in namespace
kubectl delete all --all -n myapp

# Delete namespace
kubectl delete namespace myapp

# Stop Minikube (preserves state)
minikube stop

# Delete Minikube cluster
minikube delete
```
