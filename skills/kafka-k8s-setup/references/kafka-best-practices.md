# Kafka on Kubernetes Best Practices

## Namespace Isolation

### Dedicated Namespace
- Always deploy Kafka in a dedicated namespace
- Use descriptive namespace names (e.g., `kafka-prod`, `kafka-staging`)
- Apply resource quotas to prevent resource exhaustion
- Implement network policies for traffic isolation

### Resource Management
- Set appropriate CPU and memory limits/requests
- Configure persistent volumes for data durability
- Plan for adequate storage capacity and IOPS
- Consider node affinity for performance-critical deployments

## Helm Chart Configuration

### Essential Parameters
- **replicaCount**: Set based on availability requirements (minimum 3 for production)
- **persistence**: Enable and configure appropriate storage size
- **resources**: Define proper limits to ensure stability
- **zookeeper**: Decide whether to use embedded or external ZooKeeper

### Networking
- Use ClusterIP services for internal communication
- Configure load balancers only if external access is required
- Implement proper DNS names for service discovery
- Set up network policies to restrict unauthorized access

## Production Considerations

### Security
- Enable authentication and authorization
- Configure TLS encryption for data in transit
- Use secrets for sensitive configuration
- Implement proper RBAC controls

### Monitoring
- Enable JMX metrics exposure
- Set up monitoring for key Kafka metrics
- Configure alerts for critical issues
- Monitor consumer lag and partition distribution

### Scaling
- Plan for horizontal pod autoscaling if supported
- Understand the impact of scaling on partition leaders
- Configure appropriate JVM heap settings
- Plan for maintenance windows during scaling operations

## Common Configuration Values

### Minimal Production Values
```yaml
# Minimal values for production-ready Kafka
replicaCount: 3

# Persistence configuration
persistence:
  enabled: true
  size: 100Gi
  storageClass: ""  # Use default storage class or specify

# Resource configuration
resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

# ZooKeeper configuration
zookeeper:
  enabled: true
  replicaCount: 3
  resources:
    limits:
      cpu: 500m
      memory: 1Gi
    requests:
      cpu: 250m
      memory: 512Mi

# Networking
service:
  type: ClusterIP
  ports:
    client: 9092
    internal: 9093

# Security
auth:
  clientProtocol: sasl
  interBrokerProtocol: sasl
  zookeeper:
    enabled: true
```

### Storage Optimization
- Use fast storage classes (SSD) for better performance
- Configure appropriate I/O scheduler settings
- Monitor disk usage and fragmentation
- Plan for log retention and cleanup policies

## Troubleshooting Common Issues

### Pod Startup Issues
- Check resource availability in the cluster
- Verify persistent volume provisioning
- Review configuration parameters for validity
- Check for conflicting network policies

### Performance Issues
- Monitor resource utilization (CPU, memory, disk I/O)
- Check for network bottlenecks
- Review garbage collection logs
- Verify storage performance characteristics

### Connectivity Issues
- Confirm service endpoints are properly configured
- Check network policies for access restrictions
- Verify DNS resolution for service names
- Validate firewall rules if applicable

## Verification Checklist

### Pre-deployment
- [ ] Namespace created with appropriate quotas
- [ ] Storage class available and tested
- [ ] Resource requirements calculated
- [ ] Backup and recovery procedures defined

### Post-deployment
- [ ] All pods in Running state
- [ ] Services accessible within cluster
- [ ] Persistent volumes bound and mounted
- [ ] Basic topic creation and deletion functional
- [ ] Consumer/producer connectivity verified

### Production Readiness
- [ ] Monitoring and alerting configured
- [ ] Security settings applied
- [ ] Backup procedures tested
- [ ] Scaling procedures validated
- [ ] Disaster recovery plan in place