---
title: Production Deployment
sidebar_position: 1
---

# Production Deployment

This guide covers deploying MCP servers to production environments with considerations for scalability, reliability, and security.

## Deployment Architectures

### Single Server Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp-server:
    image: your-registry/mcp-server:latest
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - MCP_PORT=3000
      - MCP_HOST=0.0.0.0
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./certs:/app/certs:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - mcp-server
    restart: unless-stopped
```

### Load Balanced Deployment

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  mcp-server-1:
    image: your-registry/mcp-server:latest
    environment:
      - NODE_ENV=production
      - SERVER_ID=server-1
    volumes:
      - shared-data:/app/data
    restart: unless-stopped

  mcp-server-2:
    image: your-registry/mcp-server:latest
    environment:
      - NODE_ENV=production
      - SERVER_ID=server-2
    volumes:
      - shared-data:/app/data
    restart: unless-stopped

  mcp-server-3:
    image: your-registry/mcp-server:latest
    environment:
      - NODE_ENV=production
      - SERVER_ID=server-3
    volumes:
      - shared-data:/app/data
    restart: unless-stopped

  load-balancer:
    image: haproxy:alpine
    ports:
      - "80:80"
      - "443:443"
      - "8404:8404"  # Stats page
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./certs:/etc/ssl/certs:ro
    depends_on:
      - mcp-server-1
      - mcp-server-2
      - mcp-server-3
    restart: unless-stopped

  redis:
    image: redis:alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  shared-data:
  redis-data:
```

## Container Configuration

### Production Dockerfile

```dockerfile
# Dockerfile.prod
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

COPY . .
RUN npm run build

FROM node:18-alpine AS runtime

# Create non-root user
RUN addgroup -g 1001 -S mcp && \
    adduser -S mcp -u 1001

# Install security updates
RUN apk update && apk upgrade && \
    apk add --no-cache dumb-init curl && \
    rm -rf /var/cache/apk/*

WORKDIR /app

# Copy built application
COPY --from=builder --chown=mcp:mcp /app/dist ./dist
COPY --from=builder --chown=mcp:mcp /app/node_modules ./node_modules
COPY --from=builder --chown=mcp:mcp /app/package.json ./

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/tmp && \
    chown -R mcp:mcp /app

USER mcp

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/server.js"]
```

### Environment Configuration

```bash
# .env.production
NODE_ENV=production
MCP_PORT=3000
MCP_HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://user:password@db:5432/mcp_prod
REDIS_URL=redis://:password@redis:6379

# Security
JWT_SECRET=your-super-secret-jwt-key
ENCRYPTION_KEY=your-encryption-key

# Monitoring
LOG_LEVEL=info
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true

# Rate Limiting
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX_REQUESTS=100

# SSL/TLS
SSL_CERT_PATH=/app/certs/server.crt
SSL_KEY_PATH=/app/certs/server.key
SSL_CA_PATH=/app/certs/ca.crt
```

## Kubernetes Deployment

### Kubernetes Manifests

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mcp-production
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-config
  namespace: mcp-production
data:
  NODE_ENV: "production"
  MCP_PORT: "3000"
  LOG_LEVEL: "info"
  METRICS_ENABLED: "true"
---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-secrets
  namespace: mcp-production
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:password@postgres:5432/mcp"
  JWT_SECRET: "your-jwt-secret"
  REDIS_PASSWORD: "your-redis-password"
---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: mcp-production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: your-registry/mcp-server:latest
        ports:
        - containerPort: 3000
        envFrom:
        - configMapRef:
            name: mcp-config
        - secretRef:
            name: mcp-secrets
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
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
        - name: cert-volume
          mountPath: /app/certs
          readOnly: true
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: mcp-data-pvc
      - name: cert-volume
        secret:
          secretName: mcp-tls-certs
---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-service
  namespace: mcp-production
spec:
  selector:
    app: mcp-server
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: ClusterIP
---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-ingress
  namespace: mcp-production
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - mcp.yourdomain.com
    secretName: mcp-tls
  rules:
  - host: mcp.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-service
            port:
              number: 80
```

## Cloud Platform Deployments

### AWS ECS Deployment

```json
{
  "family": "mcp-server",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "mcp-server",
      "image": "your-account.dkr.ecr.region.amazonaws.com/mcp-server:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:mcp/database-url"
        },
        {
          "name": "JWT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:mcp/jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mcp-server",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:3000/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### Google Cloud Run Deployment

```yaml
# cloud-run.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: mcp-server
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "1Gi"
        run.googleapis.com/max-scale: "10"
        run.googleapis.com/min-scale: "1"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
      containers:
      - image: gcr.io/your-project/mcp-server:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: database-url
        resources:
          limits:
            cpu: "1"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
```

## Monitoring and Observability

### Application Monitoring

```javascript
// monitoring/app-monitor.js
import prometheus from 'prom-client';
import { createLogger, format, transports } from 'winston';

export class ApplicationMonitor {
  constructor() {
    this.setupMetrics();
    this.setupLogging();
  }

  setupMetrics() {
    // Create a Registry
    this.register = new prometheus.Registry();

    // Add default metrics
    prometheus.collectDefaultMetrics({ register: this.register });

    // Custom metrics
    this.httpRequestDuration = new prometheus.Histogram({
      name: 'mcp_http_request_duration_seconds',
      help: 'Duration of HTTP requests in seconds',
      labelNames: ['method', 'route', 'status_code'],
      buckets: [0.1, 0.5, 1, 2, 5]
    });

    this.activeConnections = new prometheus.Gauge({
      name: 'mcp_active_connections',
      help: 'Number of active MCP connections'
    });

    this.resourceRequests = new prometheus.Counter({
      name: 'mcp_resource_requests_total',
      help: 'Total number of resource requests',
      labelNames: ['resource_type', 'status']
    });

    this.toolExecutions = new prometheus.Counter({
      name: 'mcp_tool_executions_total',
      help: 'Total number of tool executions',
      labelNames: ['tool_name', 'status']
    });

    // Register metrics
    this.register.registerMetric(this.httpRequestDuration);
    this.register.registerMetric(this.activeConnections);
    this.register.registerMetric(this.resourceRequests);
    this.register.registerMetric(this.toolExecutions);
  }

  setupLogging() {
    this.logger = createLogger({
      level: process.env.LOG_LEVEL || 'info',
      format: format.combine(
        format.timestamp(),
        format.errors({ stack: true }),
        format.json()
      ),
      defaultMeta: { service: 'mcp-server' },
      transports: [
        new transports.File({ filename: 'logs/error.log', level: 'error' }),
        new transports.File({ filename: 'logs/combined.log' }),
        new transports.Console({
          format: format.combine(
            format.colorize(),
            format.simple()
          )
        })
      ]
    });
  }

  // Middleware for HTTP request monitoring
  httpMetricsMiddleware() {
    return (req, res, next) => {
      const start = Date.now();
      
      res.on('finish', () => {
        const duration = (Date.now() - start) / 1000;
        this.httpRequestDuration
          .labels(req.method, req.route?.path || req.path, res.statusCode)
          .observe(duration);
      });
      
      next();
    };
  }

  // Track MCP-specific metrics
  trackResourceRequest(resourceType, status) {
    this.resourceRequests.labels(resourceType, status).inc();
  }

  trackToolExecution(toolName, status) {
    this.toolExecutions.labels(toolName, status).inc();
  }

  updateActiveConnections(count) {
    this.activeConnections.set(count);
  }

  // Get metrics for Prometheus
  async getMetrics() {
    return await this.register.metrics();
  }
}
```

### Health Checks

```javascript
// health/health-check.js
export class HealthChecker {
  constructor(dependencies = {}) {
    this.dependencies = dependencies;
    this.checks = new Map();
    this.setupDefaultChecks();
  }

  setupDefaultChecks() {
    // Database connectivity check
    this.addCheck('database', async () => {
      if (this.dependencies.database) {
        await this.dependencies.database.ping();
      }
      return { status: 'healthy' };
    });

    // Redis connectivity check
    this.addCheck('redis', async () => {
      if (this.dependencies.redis) {
        await this.dependencies.redis.ping();
      }
      return { status: 'healthy' };
    });

    // Memory usage check
    this.addCheck('memory', async () => {
      const usage = process.memoryUsage();
      const heapUsedMB = Math.round(usage.heapUsed / 1024 / 1024);
      const heapTotalMB = Math.round(usage.heapTotal / 1024 / 1024);
      
      return {
        status: heapUsedMB < 400 ? 'healthy' : 'warning',
        details: {
          heapUsed: `${heapUsedMB}MB`,
          heapTotal: `${heapTotalMB}MB`,
          usage: `${Math.round((heapUsedMB / heapTotalMB) * 100)}%`
        }
      };
    });

    // Disk space check
    this.addCheck('disk', async () => {
      // Implement disk space check
      return { status: 'healthy' };
    });
  }

  addCheck(name, checkFunction) {
    this.checks.set(name, checkFunction);
  }

  async runHealthCheck() {
    const results = {};
    let overallStatus = 'healthy';

    for (const [name, checkFunction] of this.checks) {
      try {
        const result = await Promise.race([
          checkFunction(),
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Health check timeout')), 5000)
          )
        ]);
        
        results[name] = result;
        
        if (result.status === 'unhealthy') {
          overallStatus = 'unhealthy';
        } else if (result.status === 'warning' && overallStatus === 'healthy') {
          overallStatus = 'warning';
        }
      } catch (error) {
        results[name] = {
          status: 'unhealthy',
          error: error.message
        };
        overallStatus = 'unhealthy';
      }
    }

    return {
      status: overallStatus,
      timestamp: new Date().toISOString(),
      checks: results
    };
  }

  async runReadinessCheck() {
    // Simplified readiness check
    const criticalChecks = ['database'];
    
    for (const checkName of criticalChecks) {
      const checkFunction = this.checks.get(checkName);
      if (checkFunction) {
        try {
          const result = await checkFunction();
          if (result.status === 'unhealthy') {
            return { ready: false, reason: `${checkName} is unhealthy` };
          }
        } catch (error) {
          return { ready: false, reason: `${checkName} check failed: ${error.message}` };
        }
      }
    }

    return { ready: true };
  }
}
```

## Scaling Strategies

### Horizontal Scaling

```javascript
// scaling/horizontal-scaler.js
export class HorizontalScaler {
  constructor(options) {
    this.minReplicas = options.minReplicas || 2;
    this.maxReplicas = options.maxReplicas || 10;
    this.targetCpuUtilization = options.targetCpuUtilization || 70;
    this.targetMemoryUtilization = options.targetMemoryUtilization || 80;
    this.scaleUpCooldown = options.scaleUpCooldown || 300000; // 5 minutes
    this.scaleDownCooldown = options.scaleDownCooldown || 600000; // 10 minutes
    
    this.lastScaleAction = null;
    this.currentReplicas = this.minReplicas;
  }

  async evaluateScaling(metrics) {
    const now = Date.now();
    
    // Check cooldown period
    if (this.lastScaleAction && 
        now - this.lastScaleAction.timestamp < this.getActiveCooldown()) {
      return null;
    }

    const recommendation = this.calculateScalingRecommendation(metrics);
    
    if (recommendation && this.shouldScale(recommendation)) {
      this.lastScaleAction = {
        action: recommendation.action,
        timestamp: now,
        reason: recommendation.reason
      };
      
      return recommendation;
    }

    return null;
  }

  calculateScalingRecommendation(metrics) {
    const { cpuUtilization, memoryUtilization, activeConnections } = metrics;
    
    // Scale up conditions
    if (cpuUtilization > this.targetCpuUtilization || 
        memoryUtilization > this.targetMemoryUtilization) {
      
      if (this.currentReplicas < this.maxReplicas) {
        return {
          action: 'scale_up',
          targetReplicas: Math.min(this.currentReplicas + 1, this.maxReplicas),
          reason: `High resource utilization: CPU ${cpuUtilization}%, Memory ${memoryUtilization}%`
        };
      }
    }
    
    // Scale down conditions
    if (cpuUtilization < this.targetCpuUtilization * 0.5 && 
        memoryUtilization < this.targetMemoryUtilization * 0.5) {
      
      if (this.currentReplicas > this.minReplicas) {
        return {
          action: 'scale_down',
          targetReplicas: Math.max(this.currentReplicas - 1, this.minReplicas),
          reason: `Low resource utilization: CPU ${cpuUtilization}%, Memory ${memoryUtilization}%`
        };
      }
    }

    return null;
  }

  shouldScale(recommendation) {
    // Additional validation logic
    return true;
  }

  getActiveCooldown() {
    if (!this.lastScaleAction) return 0;
    
    return this.lastScaleAction.action === 'scale_up' 
      ? this.scaleUpCooldown 
      : this.scaleDownCooldown;
  }
}
```

## Backup and Recovery

### Automated Backup Strategy

```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Database backup
echo "Starting database backup..."
pg_dump $DATABASE_URL > "$BACKUP_DIR/database_$DATE.sql"
gzip "$BACKUP_DIR/database_$DATE.sql"

# Application data backup
echo "Starting application data backup..."
tar -czf "$BACKUP_DIR/app_data_$DATE.tar.gz" /app/data

# Configuration backup
echo "Starting configuration backup..."
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" /app/config

# Upload to cloud storage
echo "Uploading backups to cloud storage..."
aws s3 cp "$BACKUP_DIR/database_$DATE.sql.gz" s3://your-backup-bucket/database/
aws s3 cp "$BACKUP_DIR/app_data_$DATE.tar.gz" s3://your-backup-bucket/data/
aws s3 cp "$BACKUP_DIR/config_$DATE.tar.gz" s3://your-backup-bucket/config/

# Cleanup old backups
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully"
```

## Security Hardening

### Production Security Checklist

- [ ] **TLS/SSL enabled** with strong ciphers
- [ ] **Authentication required** for all endpoints
- [ ] **Rate limiting** implemented
- [ ] **Input validation** on all inputs
- [ ] **Security headers** configured
- [ ] **Secrets management** using secure storage
- [ ] **Network segmentation** implemented
- [ ] **Regular security updates** automated
- [ ] **Vulnerability scanning** enabled
- [ ] **Audit logging** configured

### Security Configuration

```javascript
// security/production-security.js
export const productionSecurityConfig = {
  // TLS Configuration
  tls: {
    minVersion: 'TLSv1.2',
    ciphers: [
      'ECDHE-RSA-AES128-GCM-SHA256',
      'ECDHE-RSA-AES256-GCM-SHA384',
      'ECDHE-RSA-AES128-SHA256',
      'ECDHE-RSA-AES256-SHA384'
    ].join(':'),
    honorCipherOrder: true
  },

  // Security Headers
  headers: {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Content-Security-Policy': "default-src 'self'",
    'Referrer-Policy': 'strict-origin-when-cross-origin'
  },

  // Rate Limiting
  rateLimiting: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // limit each IP to 100 requests per windowMs
    message: 'Too many requests from this IP'
  }
};
```

## Next Steps

- **[Monitoring](/docs/Appendix/monitoring)**: Set up comprehensive monitoring
- **[API Reference](/docs/Appendix/api-reference)**: Complete API documentation
- **[Troubleshooting](/docs/Appendix/troubleshooting)**: Common issues and solutions
