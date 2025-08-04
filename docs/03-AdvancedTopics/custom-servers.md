---
title: Building Custom Servers
sidebar_position: 1
---

# Building Custom MCP Servers

This guide covers advanced techniques for building sophisticated MCP servers that provide rich functionality to AI assistants.

## Advanced Server Architecture

### Modular Server Design

```javascript
// server/base-server.js
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

export class BaseServer {
  constructor(config) {
    this.config = config;
    this.server = new Server(
      {
        name: config.name,
        version: config.version,
      },
      {
        capabilities: {
          resources: {},
          tools: {},
          prompts: {},
        },
      }
    );
    
    this.modules = new Map();
    this.setupBaseHandlers();
  }

  // Register a module
  registerModule(name, module) {
    this.modules.set(name, module);
    module.register(this.server);
  }

  // Setup base error handling and logging
  setupBaseHandlers() {
    this.server.onerror = (error) => {
      console.error('MCP Server Error:', error);
    };
  }

  async start() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.log(`${this.config.name} server started`);
  }
}
```

### Plugin System

```javascript
// modules/database-module.js
import { ListResourcesRequestSchema, ReadResourceRequestSchema } from '@modelcontextprotocol/sdk/types.js';

export class DatabaseModule {
  constructor(connectionString) {
    this.connectionString = connectionString;
    this.db = null;
  }

  async register(server) {
    await this.connect();
    
    server.setRequestHandler(ListResourcesRequestSchema, async () => {
      const tables = await this.listTables();
      return {
        resources: tables.map(table => ({
          uri: `db://table/${table.name}`,
          name: table.name,
          description: `Database table: ${table.name}`,
          mimeType: 'application/json'
        }))
      };
    });

    server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const url = new URL(request.params.uri);
      if (url.protocol === 'db:' && url.pathname.startsWith('/table/')) {
        const tableName = url.pathname.split('/')[2];
        const data = await this.queryTable(tableName);
        return {
          contents: [{
            uri: request.params.uri,
            mimeType: 'application/json',
            text: JSON.stringify(data, null, 2)
          }]
        };
      }
      throw new Error('Invalid database resource URI');
    });
  }

  async connect() {
    // Database connection logic
    console.log('Connected to database');
  }

  async listTables() {
    // Return list of tables
    return [
      { name: 'users', rows: 1000 },
      { name: 'orders', rows: 5000 },
      { name: 'products', rows: 500 }
    ];
  }

  async queryTable(tableName, limit = 100) {
    // Query table data
    return {
      table: tableName,
      rows: [],
      metadata: { limit, total: 0 }
    };
  }
}
```

## Advanced Resource Management

### Dynamic Resource Discovery

```javascript
// modules/file-watcher.js
import { watch } from 'fs';
import { EventEmitter } from 'events';

export class FileWatcherModule extends EventEmitter {
  constructor(watchPath) {
    super();
    this.watchPath = watchPath;
    this.resources = new Map();
    this.server = null;
  }

  register(server) {
    this.server = server;
    this.startWatching();
    
    // Handle resource notifications
    this.on('resourceAdded', (resource) => {
      server.notification({
        method: 'notifications/resources/updated',
        params: { uri: resource.uri }
      });
    });

    this.on('resourceRemoved', (uri) => {
      server.notification({
        method: 'notifications/resources/updated',
        params: { uri }
      });
    });
  }

  startWatching() {
    watch(this.watchPath, { recursive: true }, (eventType, filename) => {
      if (eventType === 'rename') {
        this.handleFileChange(filename);
      }
    });
  }

  async handleFileChange(filename) {
    const fullPath = path.join(this.watchPath, filename);
    const uri = `file://${fullPath}`;
    
    try {
      await fs.access(fullPath);
      // File exists - added or modified
      const resource = {
        uri,
        name: path.basename(filename),
        description: `File: ${filename}`,
        mimeType: this.getMimeType(filename)
      };
      this.resources.set(uri, resource);
      this.emit('resourceAdded', resource);
    } catch {
      // File doesn't exist - removed
      this.resources.delete(uri);
      this.emit('resourceRemoved', uri);
    }
  }
}
```

### Resource Caching and Performance

```javascript
// utils/cache.js
export class ResourceCache {
  constructor(maxSize = 1000, ttl = 300000) { // 5 minutes TTL
    this.cache = new Map();
    this.maxSize = maxSize;
    this.ttl = ttl;
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;
    
    if (Date.now() - item.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }
    
    return item.value;
  }

  set(key, value) {
    // Implement LRU eviction
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    
    this.cache.set(key, {
      value,
      timestamp: Date.now()
    });
  }

  clear() {
    this.cache.clear();
  }
}

// Usage in server
export class CachedResourceModule {
  constructor() {
    this.cache = new ResourceCache();
  }

  async readResource(uri) {
    const cached = this.cache.get(uri);
    if (cached) {
      return cached;
    }

    const content = await this.fetchResource(uri);
    this.cache.set(uri, content);
    return content;
  }
}
```

## Advanced Tool Implementation

### Async Tool Execution

```javascript
// tools/async-tools.js
import { CallToolRequestSchema } from '@modelcontextprotocol/sdk/types.js';

export class AsyncToolModule {
  constructor() {
    this.runningTasks = new Map();
  }

  register(server) {
    server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      
      switch (name) {
        case 'start_long_task':
          return await this.startLongTask(args);
        case 'check_task_status':
          return await this.checkTaskStatus(args);
        case 'cancel_task':
          return await this.cancelTask(args);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  async startLongTask(args) {
    const taskId = this.generateTaskId();
    
    // Start async task
    const promise = this.executeLongRunningOperation(args)
      .then(result => {
        this.runningTasks.set(taskId, { status: 'completed', result });
        return result;
      })
      .catch(error => {
        this.runningTasks.set(taskId, { status: 'failed', error: error.message });
        throw error;
      });

    this.runningTasks.set(taskId, { status: 'running', promise });

    return {
      content: [{
        type: 'text',
        text: `Task started with ID: ${taskId}. Use check_task_status to monitor progress.`
      }]
    };
  }

  async checkTaskStatus(args) {
    const task = this.runningTasks.get(args.taskId);
    if (!task) {
      throw new Error('Task not found');
    }

    return {
      content: [{
        type: 'text',
        text: `Task ${args.taskId} status: ${task.status}`
      }]
    };
  }

  generateTaskId() {
    return Math.random().toString(36).substr(2, 9);
  }

  async executeLongRunningOperation(args) {
    // Simulate long-running task
    return new Promise(resolve => {
      setTimeout(() => resolve('Task completed'), 5000);
    });
  }
}
```

### Tool Composition and Workflows

```javascript
// tools/workflow-tools.js
export class WorkflowModule {
  constructor() {
    this.workflows = new Map();
  }

  register(server) {
    server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      
      if (name === 'execute_workflow') {
        return await this.executeWorkflow(args);
      }
    });
  }

  async executeWorkflow(args) {
    const workflow = this.workflows.get(args.workflowName);
    if (!workflow) {
      throw new Error(`Workflow not found: ${args.workflowName}`);
    }

    const context = { ...args.context };
    const results = [];

    for (const step of workflow.steps) {
      try {
        const result = await this.executeStep(step, context);
        results.push(result);
        
        // Update context with step results
        if (step.outputVariable) {
          context[step.outputVariable] = result;
        }
      } catch (error) {
        if (step.continueOnError) {
          results.push({ error: error.message });
        } else {
          throw error;
        }
      }
    }

    return {
      content: [{
        type: 'text',
        text: `Workflow completed. Results: ${JSON.stringify(results, null, 2)}`
      }]
    };
  }

  async executeStep(step, context) {
    // Execute individual workflow step
    switch (step.type) {
      case 'api_call':
        return await this.makeApiCall(step.config, context);
      case 'data_transform':
        return await this.transformData(step.config, context);
      case 'condition':
        return await this.evaluateCondition(step.config, context);
      default:
        throw new Error(`Unknown step type: ${step.type}`);
    }
  }
}
```

## Error Handling and Resilience

### Comprehensive Error Handling

```javascript
// utils/error-handler.js
export class ErrorHandler {
  constructor(server) {
    this.server = server;
    this.setupGlobalHandlers();
  }

  setupGlobalHandlers() {
    process.on('uncaughtException', (error) => {
      console.error('Uncaught Exception:', error);
      this.notifyError(error);
    });

    process.on('unhandledRejection', (reason, promise) => {
      console.error('Unhandled Rejection at:', promise, 'reason:', reason);
      this.notifyError(reason);
    });
  }

  wrapHandler(handler) {
    return async (request) => {
      try {
        return await handler(request);
      } catch (error) {
        return this.handleError(error, request);
      }
    };
  }

  handleError(error, request) {
    const errorResponse = {
      code: this.getErrorCode(error),
      message: error.message,
      data: {
        timestamp: new Date().toISOString(),
        request: request?.method,
        stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
      }
    };

    console.error('Request Error:', errorResponse);
    throw errorResponse;
  }

  getErrorCode(error) {
    if (error.code) return error.code;
    if (error.name === 'ValidationError') return -32602;
    if (error.name === 'NotFoundError') return -32001;
    if (error.name === 'PermissionError') return -32003;
    return -32603; // Internal error
  }

  notifyError(error) {
    // Send error notification to monitoring system
    console.error('System Error:', error);
  }
}
```

### Circuit Breaker Pattern

```javascript
// utils/circuit-breaker.js
export class CircuitBreaker {
  constructor(options = {}) {
    this.failureThreshold = options.failureThreshold || 5;
    this.resetTimeout = options.resetTimeout || 60000;
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
    this.failureCount = 0;
    this.lastFailureTime = null;
  }

  async execute(operation) {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailureTime > this.resetTimeout) {
        this.state = 'HALF_OPEN';
      } else {
        throw new Error('Circuit breaker is OPEN');
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    this.failureCount = 0;
    this.state = 'CLOSED';
  }

  onFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    
    if (this.failureCount >= this.failureThreshold) {
      this.state = 'OPEN';
    }
  }
}
```

## Performance Optimization

### Connection Pooling

```javascript
// utils/connection-pool.js
export class ConnectionPool {
  constructor(factory, options = {}) {
    this.factory = factory;
    this.maxSize = options.maxSize || 10;
    this.minSize = options.minSize || 2;
    this.acquireTimeout = options.acquireTimeout || 30000;
    
    this.pool = [];
    this.pending = [];
    this.inUse = new Set();
  }

  async acquire() {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Connection acquire timeout'));
      }, this.acquireTimeout);

      if (this.pool.length > 0) {
        const connection = this.pool.pop();
        this.inUse.add(connection);
        clearTimeout(timeout);
        resolve(connection);
        return;
      }

      if (this.inUse.size < this.maxSize) {
        this.factory.create()
          .then(connection => {
            this.inUse.add(connection);
            clearTimeout(timeout);
            resolve(connection);
          })
          .catch(reject);
        return;
      }

      this.pending.push({ resolve, reject, timeout });
    });
  }

  release(connection) {
    this.inUse.delete(connection);
    
    if (this.pending.length > 0) {
      const { resolve, timeout } = this.pending.shift();
      clearTimeout(timeout);
      this.inUse.add(connection);
      resolve(connection);
    } else if (this.pool.length < this.minSize) {
      this.pool.push(connection);
    } else {
      this.factory.destroy(connection);
    }
  }
}
```

### Streaming Responses

```javascript
// utils/streaming.js
export class StreamingModule {
  register(server) {
    server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      if (request.params.uri.includes('stream=true')) {
        return await this.streamResource(request.params.uri);
      }
      // Regular handling
    });
  }

  async streamResource(uri) {
    const stream = this.createResourceStream(uri);
    const chunks = [];

    return new Promise((resolve, reject) => {
      stream.on('data', (chunk) => {
        chunks.push({
          uri,
          mimeType: 'text/plain',
          text: chunk.toString()
        });
      });

      stream.on('end', () => {
        resolve({
          contents: chunks
        });
      });

      stream.on('error', reject);
    });
  }
}
```

## Testing Custom Servers

### Unit Testing

```javascript
// tests/server.test.js
import { describe, it, expect, beforeEach } from 'vitest';
import { TestTransport } from '@modelcontextprotocol/sdk/test/index.js';
import { MyCustomServer } from '../src/server.js';

describe('Custom MCP Server', () => {
  let server;
  let transport;

  beforeEach(async () => {
    server = new MyCustomServer();
    transport = new TestTransport();
    await server.connect(transport);
  });

  it('should list resources', async () => {
    const response = await transport.request({
      method: 'resources/list'
    });

    expect(response.resources).toBeDefined();
    expect(Array.isArray(response.resources)).toBe(true);
  });

  it('should handle tool execution', async () => {
    const response = await transport.request({
      method: 'tools/call',
      params: {
        name: 'test_tool',
        arguments: { input: 'test' }
      }
    });

    expect(response.content).toBeDefined();
  });
});
```

### Integration Testing

```javascript
// tests/integration.test.js
import { spawn } from 'child_process';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

describe('Server Integration', () => {
  it('should work with real client', async () => {
    const transport = new StdioClientTransport({
      command: 'node',
      args: ['dist/server.js']
    });

    const client = new Client({
      name: 'test-client',
      version: '1.0.0'
    }, {
      capabilities: {}
    });

    await client.connect(transport);
    
    const resources = await client.request({
      method: 'resources/list'
    });

    expect(resources.resources.length).toBeGreaterThan(0);
    
    await client.close();
  });
});
```

## Next Steps

- **[Best Practices](/docs/04-BestPractices/security)**: Learn development best practices
- **[Security](/docs/05-Security/authentication)**: Implement security measures
- **[Deployment](/docs/06-Deployment/production)**: Deploy to production
