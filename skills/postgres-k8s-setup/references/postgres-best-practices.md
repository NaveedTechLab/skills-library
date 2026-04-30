# PostgreSQL on Kubernetes Best Practices

## Deployment Considerations

### Storage Requirements
- Always use persistent volumes for data persistence
- Choose appropriate storage class based on performance needs
- Configure adequate storage size with room for growth
- Consider backup and snapshot capabilities of storage class

### Resource Allocation
- Set appropriate CPU and memory limits/requests
- Account for PostgreSQL's memory requirements (shared_buffers, wal_buffers, etc.)
- Plan for connections pool sizing
- Consider background processes and autovacuum resources

## Helm Chart Configuration

### Essential Parameters
- **architecture**: Choose between standalone and replication based on requirements
- **auth**: Secure authentication settings with strong passwords
- **primary.persistence**: Proper storage configuration for primary node
- **resources**: Appropriate resource limits and requests
- **service.ports**: Correct port configuration

### Security Configuration
- Enable TLS encryption for connections
- Use strong passwords and rotate regularly
- Implement proper network policies
- Restrict access with RBAC policies
- Consider using external secret management

## Migration Strategies

### Migration File Organization
- Use sequential numbering for migration files (001_initial.sql, 002_add_users.sql)
- Separate migration files by environment if needed
- Include rollback scripts alongside migration scripts
- Use descriptive names that indicate the migration purpose

### Migration Execution
- Always backup database before running migrations
- Test migrations on non-production environments first
- Run migrations during scheduled maintenance windows
- Implement proper error handling and rollback procedures
- Log migration execution for audit trails

### Common Migration Patterns
```sql
-- Safe table alteration pattern
BEGIN;
ALTER TABLE users ADD COLUMN email VARCHAR(255);
UPDATE users SET email = '' WHERE email IS NULL;
ALTER TABLE users ALTER COLUMN email SET NOT NULL;
COMMIT;

-- Safe column addition with default
ALTER TABLE table_name ADD COLUMN new_column TEXT DEFAULT '';
-- Update existing rows if needed
UPDATE table_name SET new_column = 'default_value' WHERE new_column = '';
-- Remove default if no longer needed
ALTER TABLE table_name ALTER COLUMN new_column DROP DEFAULT;
```

## Schema Verification

### Essential Checks
- Verify all required tables exist
- Confirm table structures match expected schema
- Validate indexes are properly created
- Check foreign key relationships
- Verify constraints are in place

### Automated Verification
- Create verification scripts that can be run post-migration
- Implement health checks for database connectivity
- Monitor database performance metrics
- Set up alerts for schema inconsistencies

## Production Considerations

### High Availability
- Configure replication for production environments
- Set up proper backup and restore procedures
- Implement monitoring for replication lag
- Plan for failover procedures

### Monitoring
- Enable PostgreSQL metrics collection
- Monitor database connections and performance
- Track query performance and slow queries
- Set up alerts for disk space and performance issues

### Backup and Recovery
- Implement regular automated backups
- Test backup restoration procedures regularly
- Consider point-in-time recovery options
- Store backups in secure, separate locations

## Sample Migration Scripts

### Initial Schema (001_initial_schema.sql)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Migration with Data Transformation (002_add_country_code.sql)
```sql
-- Add new column with default
ALTER TABLE users ADD COLUMN country_code CHAR(2) DEFAULT 'US';

-- Update existing records if needed
UPDATE users SET country_code = 'CA' WHERE email LIKE '%canada%';

-- Make column non-nullable if appropriate
ALTER TABLE users ALTER COLUMN country_code SET NOT NULL;

-- Add constraint if needed
ALTER TABLE users ADD CONSTRAINT chk_country_code CHECK (country_code ~ '^[A-Z]{2}$');
```

### Rollback Script (002_add_country_code.rollback.sql)
```sql
-- Rollback the changes from migration 002
ALTER TABLE users DROP COLUMN country_code;
```

## Troubleshooting Common Issues

### Deployment Issues
- Check storage provisioner availability
- Verify resource availability in cluster
- Review security context configurations
- Check image pull secrets if using private registries

### Migration Issues
- Handle locked tables gracefully
- Address insufficient privileges
- Manage long-running transactions
- Resolve dependency conflicts between migrations

### Performance Issues
- Monitor query execution plans
- Check for missing indexes
- Review connection pooling settings
- Optimize PostgreSQL configuration parameters

## Verification Checklist

### Pre-deployment
- [ ] Persistent volume configuration verified
- [ ] Resource requirements calculated
- [ ] Security settings planned
- [ ] Backup strategy defined

### Post-deployment
- [ ] PostgreSQL pod running and ready
- [ ] Database accessible within cluster
- [ ] Persistent volume bound and mounted
- [ ] Initial database created and configured

### Migration Process
- [ ] Migration scripts organized and tested
- [ ] Backup taken before migration
- [ ] Migration executed successfully
- [ ] Schema verification passed
- [ ] Application connectivity confirmed

### Production Readiness
- [ ] Monitoring and alerting configured
- [ ] Backup procedures tested
- [ ] Security settings verified
- [ ] Performance benchmarks established
- [ ] Maintenance procedures documented