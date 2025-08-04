---
title: Security Best Practices
sidebar_position: 1
---

# Security Best Practices

Security is paramount when building MCP servers that handle sensitive data and provide access to external systems. This guide covers essential security practices and implementation patterns.

## Authentication and Authorization

### Server Authentication

```javascript
// auth/server-auth.js
import crypto from 'crypto';
import jwt from 'jsonwebtoken';

export class ServerAuthenticator {
  constructor(options) {
    this.secretKey = options.secretKey || process.env.MCP_SECRET_KEY;
    this.tokenExpiry = options.tokenExpiry || '1h';
    this.allowedClients = new Set(options.allowedClients || []);
  }

  // Generate server certificate
  generateServerCert() {
    const keyPair = crypto.generateKeyPairSync('rsa', {
      modulusLength: 2048,
      publicKeyEncoding: { type: 'spki', format: 'pem' },
      privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
    });

    return {
      publicKey: keyPair.publicKey,
      privateKey: keyPair.privateKey,
      fingerprint: this.generateFingerprint(keyPair.publicKey)
    };
  }

  // Validate client credentials
  async validateClient(clientId, credentials) {
    if (!this.allowedClients.has(clientId)) {
      throw new Error('Client not authorized');
    }

    // Verify client certificate or token
    try {
      const decoded = jwt.verify(credentials.token, this.secretKey);
      return decoded.clientId === clientId;
    } catch (error) {
      throw new Error('Invalid client credentials');
    }
  }

  // Generate access token
  generateAccessToken(clientId, permissions = []) {
    return jwt.sign(
      { 
        clientId, 
        permissions,
        iat: Math.floor(Date.now() / 1000)
      },
      this.secretKey,
      { expiresIn: this.tokenExpiry }
    );
  }

  generateFingerprint(publicKey) {
    return crypto
      .createHash('sha256')
      .update(publicKey)
      .digest('hex')
      .match(/.{2}/g)
      .join(':');
  }
}
```

### Permission-Based Access Control

```javascript
// auth/permissions.js
export class PermissionManager {
  constructor() {
    this.permissions = new Map();
    this.resourcePolicies = new Map();
  }

  // Define resource access policies
  defineResourcePolicy(resourcePattern, policy) {
    this.resourcePolicies.set(resourcePattern, policy);
  }

  // Check if client has permission for resource
  async checkResourceAccess(clientId, resourceUri, action = 'read') {
    const clientPermissions = this.permissions.get(clientId) || [];
    
    // Check direct permissions
    if (clientPermissions.includes(`${action}:${resourceUri}`)) {
      return true;
    }

    // Check pattern-based permissions
    for (const [pattern, policy] of this.resourcePolicies) {
      if (this.matchesPattern(resourceUri, pattern)) {
        return this.evaluatePolicy(policy, clientId, action);
      }
    }

    return false;
  }

  // Check tool execution permissions
  async checkToolAccess(clientId, toolName, args) {
    const clientPermissions = this.permissions.get(clientId) || [];
    
    // Check if client can execute this tool
    if (!clientPermissions.includes(`execute:${toolName}`)) {
      return false;
    }

    // Additional argument validation
    return this.validateToolArguments(toolName, args);
  }

  matchesPattern(uri, pattern) {
    const regex = new RegExp(pattern.replace('*', '.*'));
    return regex.test(uri);
  }

  evaluatePolicy(policy, clientId, action) {
    // Implement policy evaluation logic
    return policy.actions.includes(action) && 
           policy.principals.includes(clientId);
  }

  validateToolArguments(toolName, args) {
    // Implement argument validation
    // Check for dangerous patterns, SQL injection, etc.
    return true;
  }
}
```

## Input Validation and Sanitization

### Request Validation

```javascript
// validation/request-validator.js
import Joi from 'joi';

export class RequestValidator {
  constructor() {
    this.schemas = new Map();
    this.setupSchemas();
  }

  setupSchemas() {
    // Resource URI validation
    this.schemas.set('resourceUri', Joi.string()
      .uri({ scheme: ['file', 'http', 'https', 'db'] })
      .max(2048)
      .required()
    );

    // Tool arguments validation
    this.schemas.set('toolArgs', Joi.object()
      .pattern(Joi.string(), Joi.alternatives().try(
        Joi.string().max(10000),
        Joi.number(),
        Joi.boolean(),
        Joi.array(),
        Joi.object()
      ))
      .max(100) // Max 100 properties
    );

    // File path validation
    this.schemas.set('filePath', Joi.string()
      .pattern(/^[a-zA-Z0-9._\-\/\\]+$/)
      .max(1024)
      .custom((value, helpers) => {
        // Prevent path traversal
        if (value.includes('..') || value.includes('~')) {
          return helpers.error('any.invalid');
        }
        return value;
      })
    );
  }

  validateRequest(type, data) {
    const schema = this.schemas.get(type);
    if (!schema) {
      throw new Error(`Unknown validation type: ${type}`);
    }

    const { error, value } = schema.validate(data);
    if (error) {
      throw new Error(`Validation error: ${error.details[0].message}`);
    }

    return value;
  }

  // Sanitize user input
  sanitizeInput(input) {
    if (typeof input === 'string') {
      return input
        .replace(/[<>]/g, '') // Remove potential HTML
        .replace(/['"]/g, '') // Remove quotes
        .trim()
        .slice(0, 10000); // Limit length
    }
    return input;
  }

  // Validate SQL queries (for database tools)
  validateSqlQuery(query) {
    const dangerousPatterns = [
      /DROP\s+TABLE/i,
      /DELETE\s+FROM/i,
      /UPDATE\s+.*\s+SET/i,
      /INSERT\s+INTO/i,
      /CREATE\s+TABLE/i,
      /ALTER\s+TABLE/i,
      /EXEC\s*\(/i,
      /EXECUTE\s*\(/i
    ];

    for (const pattern of dangerousPatterns) {
      if (pattern.test(query)) {
        throw new Error('Dangerous SQL operation detected');
      }
    }

    return query;
  }
}
```

### Content Security

```javascript
// security/content-security.js
export class ContentSecurityManager {
  constructor() {
    this.maxFileSize = 50 * 1024 * 1024; // 50MB
    this.allowedMimeTypes = new Set([
      'text/plain',
      'text/markdown',
      'application/json',
      'text/csv',
      'application/pdf'
    ]);
    this.blockedExtensions = new Set([
      '.exe', '.bat', '.cmd', '.scr', '.pif',
      '.com', '.dll', '.jar', '.sh', '.ps1'
    ]);
  }

  // Validate file content
  async validateFileContent(filePath, content) {
    // Check file size
    if (content.length > this.maxFileSize) {
      throw new Error('File size exceeds maximum allowed');
    }

    // Check file extension
    const ext = path.extname(filePath).toLowerCase();
    if (this.blockedExtensions.has(ext)) {
      throw new Error('File type not allowed');
    }

    // Check MIME type
    const mimeType = this.detectMimeType(content);
    if (!this.allowedMimeTypes.has(mimeType)) {
      throw new Error('MIME type not allowed');
    }

    // Scan for malicious content
    await this.scanForMalware(content);

    return true;
  }

  detectMimeType(content) {
    // Simple MIME type detection
    if (content.startsWith('{"') || content.startsWith('[')) {
      return 'application/json';
    }
    if (content.startsWith('%PDF')) {
      return 'application/pdf';
    }
    return 'text/plain';
  }

  async scanForMalware(content) {
    // Implement malware scanning
    // Check for suspicious patterns, embedded scripts, etc.
    const suspiciousPatterns = [
      /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
      /javascript:/gi,
      /vbscript:/gi,
      /onload\s*=/gi,
      /onerror\s*=/gi
    ];

    for (const pattern of suspiciousPatterns) {
      if (pattern.test(content)) {
        throw new Error('Suspicious content detected');
      }
    }
  }
}
```

## Secure Communication

### TLS Configuration

```javascript
// transport/secure-transport.js
import https from 'https';
import fs from 'fs';
import { WebSocketServer } from 'ws';

export class SecureTransport {
  constructor(options) {
    this.tlsOptions = {
      key: fs.readFileSync(options.keyPath),
      cert: fs.readFileSync(options.certPath),
      ca: options.caPath ? fs.readFileSync(options.caPath) : undefined,
      requestCert: true,
      rejectUnauthorized: true,
      ciphers: [
        'ECDHE-RSA-AES128-GCM-SHA256',
        'ECDHE-RSA-AES256-GCM-SHA384',
        'ECDHE-RSA-AES128-SHA256',
        'ECDHE-RSA-AES256-SHA384'
      ].join(':'),
      honorCipherOrder: true,
      secureProtocol: 'TLSv1_2_method'
    };
  }

  createSecureServer(port) {
    const server = https.createServer(this.tlsOptions);
    
    const wss = new WebSocketServer({
      server,
      verifyClient: (info) => {
        return this.verifyClient(info);
      }
    });

    wss.on('connection', (ws, request) => {
      this.handleSecureConnection(ws, request);
    });

    server.listen(port, () => {
      console.log(`Secure MCP server listening on port ${port}`);
    });

    return { server, wss };
  }

  verifyClient(info) {
    // Verify client certificate
    const cert = info.req.connection.getPeerCertificate();
    if (!cert || !cert.subject) {
      return false;
    }

    // Additional client verification logic
    return this.isAuthorizedClient(cert);
  }

  isAuthorizedClient(cert) {
    // Implement client authorization logic
    return true;
  }

  handleSecureConnection(ws, request) {
    // Set up secure message handling
    ws.on('message', (data) => {
      try {
        const message = this.decryptMessage(data);
        this.handleMessage(ws, message);
      } catch (error) {
        console.error('Message decryption failed:', error);
        ws.close(1008, 'Invalid message format');
      }
    });
  }

  decryptMessage(data) {
    // Implement message decryption if needed
    return JSON.parse(data.toString());
  }
}
```

## Rate Limiting and DoS Protection

### Request Rate Limiting

```javascript
// security/rate-limiter.js
export class RateLimiter {
  constructor(options = {}) {
    this.windowMs = options.windowMs || 60000; // 1 minute
    this.maxRequests = options.maxRequests || 100;
    this.clients = new Map();
    this.cleanup();
  }

  // Check if request is allowed
  isAllowed(clientId) {
    const now = Date.now();
    const client = this.clients.get(clientId) || { requests: [], blocked: false };

    // Remove old requests outside the window
    client.requests = client.requests.filter(
      timestamp => now - timestamp < this.windowMs
    );

    // Check if client is blocked
    if (client.blocked && now - client.blockedAt < this.windowMs * 5) {
      return false;
    }

    // Check request count
    if (client.requests.length >= this.maxRequests) {
      client.blocked = true;
      client.blockedAt = now;
      this.clients.set(clientId, client);
      return false;
    }

    // Add current request
    client.requests.push(now);
    client.blocked = false;
    this.clients.set(clientId, client);

    return true;
  }

  // Clean up old entries
  cleanup() {
    setInterval(() => {
      const now = Date.now();
      for (const [clientId, client] of this.clients) {
        client.requests = client.requests.filter(
          timestamp => now - timestamp < this.windowMs
        );
        
        if (client.requests.length === 0 && 
            (!client.blocked || now - client.blockedAt > this.windowMs * 5)) {
          this.clients.delete(clientId);
        }
      }
    }, this.windowMs);
  }
}
```

### Resource Usage Monitoring

```javascript
// monitoring/resource-monitor.js
export class ResourceMonitor {
  constructor(options = {}) {
    this.maxMemoryUsage = options.maxMemoryUsage || 512 * 1024 * 1024; // 512MB
    this.maxCpuUsage = options.maxCpuUsage || 80; // 80%
    this.checkInterval = options.checkInterval || 5000; // 5 seconds
    this.alerts = [];
    this.startMonitoring();
  }

  startMonitoring() {
    setInterval(() => {
      this.checkResourceUsage();
    }, this.checkInterval);
  }

  checkResourceUsage() {
    const memUsage = process.memoryUsage();
    const cpuUsage = process.cpuUsage();

    // Check memory usage
    if (memUsage.heapUsed > this.maxMemoryUsage) {
      this.handleAlert('HIGH_MEMORY_USAGE', {
        current: memUsage.heapUsed,
        limit: this.maxMemoryUsage
      });
    }

    // Check for memory leaks
    if (memUsage.heapUsed > memUsage.heapTotal * 0.9) {
      this.handleAlert('POTENTIAL_MEMORY_LEAK', memUsage);
    }

    // Log resource usage
    console.log('Resource Usage:', {
      memory: `${Math.round(memUsage.heapUsed / 1024 / 1024)}MB`,
      heap: `${Math.round(memUsage.heapTotal / 1024 / 1024)}MB`
    });
  }

  handleAlert(type, data) {
    const alert = {
      type,
      data,
      timestamp: new Date().toISOString()
    };

    this.alerts.push(alert);
    console.warn('Resource Alert:', alert);

    // Implement alerting mechanism (email, webhook, etc.)
    this.sendAlert(alert);
  }

  sendAlert(alert) {
    // Implement alert notification
    // Could send to monitoring service, email, Slack, etc.
  }
}
```

## Secure Configuration Management

### Environment Configuration

```javascript
// config/secure-config.js
import crypto from 'crypto';

export class SecureConfig {
  constructor() {
    this.config = new Map();
    this.encryptionKey = this.getEncryptionKey();
    this.loadConfig();
  }

  getEncryptionKey() {
    const key = process.env.CONFIG_ENCRYPTION_KEY;
    if (!key) {
      throw new Error('CONFIG_ENCRYPTION_KEY environment variable required');
    }
    return crypto.scryptSync(key, 'salt', 32);
  }

  // Encrypt sensitive configuration values
  encrypt(value) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher('aes-256-cbc', this.encryptionKey);
    
    let encrypted = cipher.update(value, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    return iv.toString('hex') + ':' + encrypted;
  }

  // Decrypt configuration values
  decrypt(encryptedValue) {
    const [ivHex, encrypted] = encryptedValue.split(':');
    const iv = Buffer.from(ivHex, 'hex');
    const decipher = crypto.createDecipher('aes-256-cbc', this.encryptionKey);
    
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  }

  loadConfig() {
    // Load configuration from environment variables
    this.config.set('database_url', this.getSecureValue('DATABASE_URL'));
    this.config.set('api_key', this.getSecureValue('API_KEY'));
    this.config.set('secret_key', this.getSecureValue('SECRET_KEY'));
  }

  getSecureValue(key) {
    const value = process.env[key];
    if (!value) {
      throw new Error(`Required environment variable ${key} not found`);
    }

    // Check if value is encrypted
    if (value.includes(':')) {
      return this.decrypt(value);
    }

    return value;
  }

  get(key) {
    return this.config.get(key);
  }
}
```

## Security Auditing and Logging

### Security Event Logging

```javascript
// logging/security-logger.js
export class SecurityLogger {
  constructor(options = {}) {
    this.logLevel = options.logLevel || 'info';
    this.logFile = options.logFile || './security.log';
    this.maxLogSize = options.maxLogSize || 10 * 1024 * 1024; // 10MB
  }

  logSecurityEvent(event, details = {}) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      event,
      details,
      severity: this.getSeverity(event),
      source: 'mcp-server'
    };

    this.writeLog(logEntry);

    // Send to SIEM if high severity
    if (logEntry.severity === 'high') {
      this.sendToSIEM(logEntry);
    }
  }

  getSeverity(event) {
    const highSeverityEvents = [
      'AUTHENTICATION_FAILURE',
      'AUTHORIZATION_FAILURE',
      'SUSPICIOUS_ACTIVITY',
      'MALWARE_DETECTED',
      'RATE_LIMIT_EXCEEDED'
    ];

    return highSeverityEvents.includes(event) ? 'high' : 'medium';
  }

  writeLog(entry) {
    const logLine = JSON.stringify(entry) + '\n';
    
    // Implement log rotation
    this.checkLogRotation();
    
    // Write to file (implement proper file handling)
    console.log('Security Log:', entry);
  }

  checkLogRotation() {
    // Implement log rotation logic
  }

  sendToSIEM(entry) {
    // Send to Security Information and Event Management system
    console.warn('High Severity Security Event:', entry);
  }
}
```

## Security Checklist

### Pre-deployment Security Checklist

- [ ] **Authentication implemented** for all client connections
- [ ] **Authorization checks** for all resource and tool access
- [ ] **Input validation** for all user-provided data
- [ ] **TLS encryption** for all network communication
- [ ] **Rate limiting** to prevent DoS attacks
- [ ] **Security logging** for audit trails
- [ ] **Error handling** that doesn't leak sensitive information
- [ ] **Configuration security** with encrypted secrets
- [ ] **Resource limits** to prevent resource exhaustion
- [ ] **Regular security updates** for all dependencies

### Runtime Security Monitoring

- [ ] **Monitor authentication failures** and suspicious patterns
- [ ] **Track resource usage** and detect anomalies
- [ ] **Log all security events** with appropriate detail
- [ ] **Monitor for malware** in uploaded content
- [ ] **Check for unauthorized access** attempts
- [ ] **Validate all certificates** and tokens regularly

## Next Steps

- **[Deployment](/docs/06-Deployment/production)**: Learn about secure deployment practices
- **[Security Reference](/docs/05-Security/authentication)**: Detailed security implementation guide
- **[Monitoring](/docs/Appendix/monitoring)**: Set up comprehensive monitoring
