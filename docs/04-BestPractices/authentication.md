---
title: Authentication & Authorization
sidebar_position: 1
---

# Authentication & Authorization

This guide covers implementing robust authentication and authorization mechanisms for MCP servers to ensure secure access to resources and tools.

## Authentication Methods

### Token-Based Authentication

```javascript
// auth/token-auth.js
import jwt from 'jsonwebtoken';
import crypto from 'crypto';

export class TokenAuthenticator {
  constructor(options) {
    this.secretKey = options.secretKey || process.env.JWT_SECRET;
    this.issuer = options.issuer || 'mcp-server';
    this.audience = options.audience || 'mcp-clients';
    this.tokenExpiry = options.tokenExpiry || '24h';
    this.refreshTokenExpiry = options.refreshTokenExpiry || '7d';
  }

  // Generate access token
  generateAccessToken(clientId, permissions = [], metadata = {}) {
    const payload = {
      sub: clientId,
      iss: this.issuer,
      aud: this.audience,
      permissions,
      metadata,
      type: 'access'
    };

    return jwt.sign(payload, this.secretKey, {
      expiresIn: this.tokenExpiry,
      jwtid: crypto.randomUUID()
    });
  }

  // Generate refresh token
  generateRefreshToken(clientId) {
    const payload = {
      sub: clientId,
      iss: this.issuer,
      aud: this.audience,
      type: 'refresh'
    };

    return jwt.sign(payload, this.secretKey, {
      expiresIn: this.refreshTokenExpiry,
      jwtid: crypto.randomUUID()
    });
  }

  // Verify and decode token
  verifyToken(token) {
    try {
      return jwt.verify(token, this.secretKey, {
        issuer: this.issuer,
        audience: this.audience
      });
    } catch (error) {
      throw new Error(`Token verification failed: ${error.message}`);
    }
  }

  // Extract token from request headers
  extractToken(headers) {
    const authHeader = headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new Error('Missing or invalid authorization header');
    }
    return authHeader.substring(7);
  }
}
```

### Certificate-Based Authentication

```javascript
// auth/cert-auth.js
import crypto from 'crypto';
import fs from 'fs';

export class CertificateAuthenticator {
  constructor(options) {
    this.caCert = fs.readFileSync(options.caCertPath);
    this.trustedClients = new Map();
    this.loadTrustedClients(options.trustedClientsPath);
  }

  loadTrustedClients(path) {
    const clients = JSON.parse(fs.readFileSync(path, 'utf8'));
    for (const client of clients) {
      this.trustedClients.set(client.fingerprint, client);
    }
  }

  // Verify client certificate
  verifyCertificate(clientCert) {
    try {
      // Verify certificate chain
      const cert = crypto.X509Certificate.from(clientCert);
      
      // Check if certificate is signed by trusted CA
      if (!this.isSignedByCA(cert)) {
        throw new Error('Certificate not signed by trusted CA');
      }

      // Check certificate validity
      if (cert.validTo < new Date()) {
        throw new Error('Certificate has expired');
      }

      if (cert.validFrom > new Date()) {
        throw new Error('Certificate not yet valid');
      }

      // Get certificate fingerprint
      const fingerprint = this.getCertificateFingerprint(cert);
      
      // Check if client is trusted
      const clientInfo = this.trustedClients.get(fingerprint);
      if (!clientInfo) {
        throw new Error('Client certificate not trusted');
      }

      return {
        clientId: clientInfo.clientId,
        permissions: clientInfo.permissions,
        fingerprint
      };
    } catch (error) {
      throw new Error(`Certificate verification failed: ${error.message}`);
    }
  }

  isSignedByCA(cert) {
    // Implement CA signature verification
    return true; // Simplified for example
  }

  getCertificateFingerprint(cert) {
    return crypto
      .createHash('sha256')
      .update(cert.raw)
      .digest('hex')
      .match(/.{2}/g)
      .join(':');
  }
}
```

### OAuth 2.0 Integration

```javascript
// auth/oauth-auth.js
import axios from 'axios';

export class OAuthAuthenticator {
  constructor(options) {
    this.clientId = options.clientId;
    this.clientSecret = options.clientSecret;
    this.authorizationServer = options.authorizationServer;
    this.tokenEndpoint = options.tokenEndpoint;
    this.userInfoEndpoint = options.userInfoEndpoint;
  }

  // Verify OAuth access token
  async verifyAccessToken(accessToken) {
    try {
      // Introspect token with authorization server
      const response = await axios.post(
        `${this.authorizationServer}/introspect`,
        {
          token: accessToken,
          client_id: this.clientId,
          client_secret: this.clientSecret
        },
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        }
      );

      if (!response.data.active) {
        throw new Error('Token is not active');
      }

      // Get user information
      const userInfo = await this.getUserInfo(accessToken);

      return {
        clientId: response.data.client_id,
        userId: response.data.sub,
        scopes: response.data.scope?.split(' ') || [],
        userInfo
      };
    } catch (error) {
      throw new Error(`OAuth token verification failed: ${error.message}`);
    }
  }

  async getUserInfo(accessToken) {
    try {
      const response = await axios.get(this.userInfoEndpoint, {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      return response.data;
    } catch (error) {
      console.warn('Failed to fetch user info:', error.message);
      return null;
    }
  }
}
```

## Authorization Framework

### Role-Based Access Control (RBAC)

```javascript
// auth/rbac.js
export class RBACManager {
  constructor() {
    this.roles = new Map();
    this.userRoles = new Map();
    this.permissions = new Map();
    this.setupDefaultRoles();
  }

  setupDefaultRoles() {
    // Define default roles
    this.defineRole('admin', [
      'resources:*:*',
      'tools:*:*',
      'prompts:*:*',
      'system:*:*'
    ]);

    this.defineRole('user', [
      'resources:read:*',
      'tools:execute:safe',
      'prompts:read:*'
    ]);

    this.defineRole('readonly', [
      'resources:read:public',
      'prompts:read:public'
    ]);
  }

  // Define a role with permissions
  defineRole(roleName, permissions) {
    this.roles.set(roleName, new Set(permissions));
  }

  // Assign role to user
  assignRole(userId, roleName) {
    if (!this.roles.has(roleName)) {
      throw new Error(`Role ${roleName} does not exist`);
    }

    if (!this.userRoles.has(userId)) {
      this.userRoles.set(userId, new Set());
    }

    this.userRoles.get(userId).add(roleName);
  }

  // Check if user has permission
  hasPermission(userId, permission) {
    const userRoles = this.userRoles.get(userId);
    if (!userRoles) {
      return false;
    }

    for (const roleName of userRoles) {
      const rolePermissions = this.roles.get(roleName);
      if (rolePermissions && this.matchesPermission(permission, rolePermissions)) {
        return true;
      }
    }

    return false;
  }

  matchesPermission(required, available) {
    for (const permission of available) {
      if (this.permissionMatches(required, permission)) {
        return true;
      }
    }
    return false;
  }

  permissionMatches(required, pattern) {
    // Convert permission pattern to regex
    const regex = new RegExp(
      '^' + pattern.replace(/\*/g, '.*').replace(/:/g, ':') + '$'
    );
    return regex.test(required);
  }

  // Get user permissions
  getUserPermissions(userId) {
    const userRoles = this.userRoles.get(userId) || new Set();
    const permissions = new Set();

    for (const roleName of userRoles) {
      const rolePermissions = this.roles.get(roleName) || new Set();
      for (const permission of rolePermissions) {
        permissions.add(permission);
      }
    }

    return Array.from(permissions);
  }
}
```

### Attribute-Based Access Control (ABAC)

```javascript
// auth/abac.js
export class ABACManager {
  constructor() {
    this.policies = [];
    this.attributeProviders = new Map();
  }

  // Add access control policy
  addPolicy(policy) {
    this.policies.push({
      id: policy.id,
      name: policy.name,
      effect: policy.effect, // 'allow' or 'deny'
      conditions: policy.conditions,
      resources: policy.resources,
      actions: policy.actions
    });
  }

  // Register attribute provider
  registerAttributeProvider(name, provider) {
    this.attributeProviders.set(name, provider);
  }

  // Evaluate access request
  async evaluateAccess(request) {
    const context = await this.buildContext(request);
    
    let finalDecision = 'deny'; // Default deny
    
    for (const policy of this.policies) {
      if (await this.evaluatePolicy(policy, context)) {
        if (policy.effect === 'deny') {
          return 'deny'; // Explicit deny overrides
        }
        finalDecision = 'allow';
      }
    }

    return finalDecision;
  }

  async buildContext(request) {
    const context = {
      subject: request.subject,
      resource: request.resource,
      action: request.action,
      environment: {
        time: new Date(),
        ip: request.ip,
        userAgent: request.userAgent
      }
    };

    // Fetch additional attributes
    for (const [name, provider] of this.attributeProviders) {
      try {
        context[name] = await provider.getAttributes(request.subject);
      } catch (error) {
        console.warn(`Failed to fetch attributes from ${name}:`, error);
      }
    }

    return context;
  }

  async evaluatePolicy(policy, context) {
    // Check if policy applies to this resource and action
    if (!this.matchesResource(context.resource, policy.resources)) {
      return false;
    }

    if (!this.matchesAction(context.action, policy.actions)) {
      return false;
    }

    // Evaluate conditions
    return await this.evaluateConditions(policy.conditions, context);
  }

  async evaluateConditions(conditions, context) {
    for (const condition of conditions) {
      if (!await this.evaluateCondition(condition, context)) {
        return false;
      }
    }
    return true;
  }

  async evaluateCondition(condition, context) {
    const { attribute, operator, value } = condition;
    const contextValue = this.getContextValue(attribute, context);

    switch (operator) {
      case 'equals':
        return contextValue === value;
      case 'contains':
        return Array.isArray(contextValue) && contextValue.includes(value);
      case 'matches':
        return new RegExp(value).test(contextValue);
      case 'greater_than':
        return contextValue > value;
      case 'less_than':
        return contextValue < value;
      case 'in_range':
        return contextValue >= value.min && contextValue <= value.max;
      default:
        throw new Error(`Unknown operator: ${operator}`);
    }
  }

  getContextValue(attribute, context) {
    const parts = attribute.split('.');
    let value = context;
    
    for (const part of parts) {
      value = value?.[part];
    }
    
    return value;
  }

  matchesResource(resource, patterns) {
    return patterns.some(pattern => 
      new RegExp(pattern.replace('*', '.*')).test(resource)
    );
  }

  matchesAction(action, patterns) {
    return patterns.includes(action) || patterns.includes('*');
  }
}
```

## Authentication Middleware

### MCP Server Authentication Middleware

```javascript
// middleware/auth-middleware.js
export class AuthenticationMiddleware {
  constructor(authenticators, authorizationManager) {
    this.authenticators = authenticators;
    this.authorizationManager = authorizationManager;
  }

  // Wrap server handlers with authentication
  wrapServer(server) {
    const originalSetRequestHandler = server.setRequestHandler.bind(server);
    
    server.setRequestHandler = (schema, handler) => {
      const wrappedHandler = async (request) => {
        // Skip authentication for certain methods
        if (this.isPublicMethod(request.method)) {
          return await handler(request);
        }

        // Authenticate request
        const authContext = await this.authenticate(request);
        
        // Authorize request
        await this.authorize(authContext, request);
        
        // Add auth context to request
        request.authContext = authContext;
        
        return await handler(request);
      };
      
      originalSetRequestHandler(schema, wrappedHandler);
    };
  }

  async authenticate(request) {
    const errors = [];
    
    // Try each authenticator
    for (const authenticator of this.authenticators) {
      try {
        const authResult = await authenticator.authenticate(request);
        if (authResult) {
          return authResult;
        }
      } catch (error) {
        errors.push(error.message);
      }
    }

    throw new Error(`Authentication failed: ${errors.join(', ')}`);
  }

  async authorize(authContext, request) {
    const permission = this.buildPermission(request);
    
    const hasPermission = await this.authorizationManager.hasPermission(
      authContext.userId,
      permission
    );

    if (!hasPermission) {
      throw new Error(`Access denied: insufficient permissions for ${permission}`);
    }
  }

  buildPermission(request) {
    const method = request.method;
    
    if (method.startsWith('resources/')) {
      const action = method.split('/')[1];
      const resource = request.params?.uri || '*';
      return `resources:${action}:${resource}`;
    }
    
    if (method.startsWith('tools/')) {
      const action = method.split('/')[1];
      const tool = request.params?.name || '*';
      return `tools:${action}:${tool}`;
    }
    
    return `${method}:*:*`;
  }

  isPublicMethod(method) {
    const publicMethods = [
      'initialize',
      'ping',
      'capabilities'
    ];
    return publicMethods.includes(method);
  }
}
```

## Session Management

### Secure Session Handling

```javascript
// auth/session-manager.js
export class SessionManager {
  constructor(options = {}) {
    this.sessions = new Map();
    this.sessionTimeout = options.sessionTimeout || 30 * 60 * 1000; // 30 minutes
    this.maxSessions = options.maxSessions || 1000;
    this.cleanupInterval = options.cleanupInterval || 5 * 60 * 1000; // 5 minutes
    
    this.startCleanup();
  }

  // Create new session
  createSession(userId, metadata = {}) {
    const sessionId = this.generateSessionId();
    const session = {
      id: sessionId,
      userId,
      createdAt: new Date(),
      lastActivity: new Date(),
      metadata,
      isActive: true
    };

    // Check session limit
    if (this.sessions.size >= this.maxSessions) {
      this.evictOldestSession();
    }

    this.sessions.set(sessionId, session);
    return sessionId;
  }

  // Validate session
  validateSession(sessionId) {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error('Session not found');
    }

    if (!session.isActive) {
      throw new Error('Session is inactive');
    }

    const now = new Date();
    if (now - session.lastActivity > this.sessionTimeout) {
      this.invalidateSession(sessionId);
      throw new Error('Session has expired');
    }

    // Update last activity
    session.lastActivity = now;
    return session;
  }

  // Invalidate session
  invalidateSession(sessionId) {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.isActive = false;
    }
  }

  // Remove session
  removeSession(sessionId) {
    this.sessions.delete(sessionId);
  }

  generateSessionId() {
    return crypto.randomBytes(32).toString('hex');
  }

  evictOldestSession() {
    let oldestSession = null;
    let oldestTime = new Date();

    for (const [id, session] of this.sessions) {
      if (session.lastActivity < oldestTime) {
        oldestTime = session.lastActivity;
        oldestSession = id;
      }
    }

    if (oldestSession) {
      this.sessions.delete(oldestSession);
    }
  }

  startCleanup() {
    setInterval(() => {
      this.cleanupExpiredSessions();
    }, this.cleanupInterval);
  }

  cleanupExpiredSessions() {
    const now = new Date();
    const expiredSessions = [];

    for (const [id, session] of this.sessions) {
      if (now - session.lastActivity > this.sessionTimeout || !session.isActive) {
        expiredSessions.push(id);
      }
    }

    for (const id of expiredSessions) {
      this.sessions.delete(id);
    }

    if (expiredSessions.length > 0) {
      console.log(`Cleaned up ${expiredSessions.length} expired sessions`);
    }
  }
}
```

## Security Configuration

### Authentication Configuration Example

```javascript
// config/auth-config.js
export const authConfig = {
  // Token authentication
  token: {
    secretKey: process.env.JWT_SECRET,
    issuer: 'mcp-server',
    audience: 'mcp-clients',
    accessTokenExpiry: '1h',
    refreshTokenExpiry: '7d'
  },

  // Certificate authentication
  certificate: {
    caCertPath: './certs/ca.pem',
    trustedClientsPath: './config/trusted-clients.json',
    requireClientCert: true
  },

  // OAuth configuration
  oauth: {
    clientId: process.env.OAUTH_CLIENT_ID,
    clientSecret: process.env.OAUTH_CLIENT_SECRET,
    authorizationServer: process.env.OAUTH_AUTH_SERVER,
    tokenEndpoint: process.env.OAUTH_TOKEN_ENDPOINT,
    userInfoEndpoint: process.env.OAUTH_USERINFO_ENDPOINT
  },

  // Session management
  session: {
    timeout: 30 * 60 * 1000, // 30 minutes
    maxSessions: 1000,
    cleanupInterval: 5 * 60 * 1000 // 5 minutes
  },

  // Authorization
  authorization: {
    type: 'rbac', // 'rbac' or 'abac'
    defaultRole: 'readonly',
    adminUsers: ['admin@example.com']
  }
};
```

## Next Steps

- **[Best Practices](/docs/04-BestPractices/security)**: Learn security best practices
- **[Deployment](/docs/06-Deployment/production)**: Secure deployment strategies
- **[Monitoring](/docs/Appendix/monitoring)**: Security monitoring and alerting
