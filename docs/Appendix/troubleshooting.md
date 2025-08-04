---
title: Troubleshooting
sidebar_position: 3
---

# Troubleshooting Guide

This guide helps you diagnose and resolve common issues when working with MCP servers and clients.

## Connection Issues

### Server Won't Start

**Symptoms:**
- Server process exits immediately
- "Command not found" errors
- Permission denied errors

**Solutions:**

1. **Check Node.js/Python Installation:**
```bash
# Verify Node.js version
node --version  # Should be 18+

# Verify Python version
python3 --version  # Should be 3.8+

# Check npm/pip installation
npm --version
pip --version
```

2. **Verify File Permissions:**
```bash
# Make server script executable
chmod +x server.js

# Check directory permissions
ls -la /path/to/server/
```

3. **Check Dependencies:**
```bash
# Install missing dependencies
npm install
# or
pip install -r requirements.txt

# Verify MCP SDK installation
npm list @modelcontextprotocol/sdk
```

4. **Enable Debug Logging:**
```bash
# Set debug environment variable
DEBUG=mcp:* node server.js

# Or use verbose logging
LOG_LEVEL=debug node server.js
```

### Client Can't Connect to Server

**Symptoms:**
- Connection timeout errors
- "Server not responding" messages
- JSON-RPC errors

**Solutions:**

1. **Verify Server is Running:**
```bash
# Check if server process is active
ps aux | grep server.js

# Test server manually
echo '{"jsonrpc":"2.0","id":1,"method":"ping"}' | node server.js
```

2. **Check Transport Configuration:**
```javascript
// Verify transport settings
const transport = new StdioClientTransport({
  command: 'node',
  args: ['path/to/server.js'],
  // Add timeout
  timeout: 30000
});
```

3. **Validate JSON-RPC Messages:**
```javascript
// Enable message logging
const client = new Client(clientInfo, capabilities);
client.onRequest = (request) => {
  console.log('Outgoing request:', JSON.stringify(request, null, 2));
};
client.onResponse = (response) => {
  console.log('Incoming response:', JSON.stringify(response, null, 2));
};
```

### WebSocket Connection Issues

**Symptoms:**
- WebSocket connection refused
- SSL/TLS handshake failures
- CORS errors in browser

**Solutions:**

1. **Check WebSocket Server Configuration:**
```javascript
// Verify WebSocket server setup
const wss = new WebSocketServer({
  port: 3000,
  host: '0.0.0.0',  // Allow external connections
  path: '/mcp'
});

// Add connection logging
wss.on('connection', (ws, request) => {
  console.log('WebSocket connection from:', request.socket.remoteAddress);
});
```

2. **SSL/TLS Configuration:**
```javascript
// For HTTPS/WSS connections
const server = https.createServer({
  cert: fs.readFileSync('path/to/cert.pem'),
  key: fs.readFileSync('path/to/key.pem')
});

const wss = new WebSocketServer({ server });
```

3. **CORS Configuration:**
```javascript
// Add CORS headers for browser clients
wss.on('headers', (headers, request) => {
  headers.push('Access-Control-Allow-Origin: *');
  headers.push('Access-Control-Allow-Methods: GET, POST, OPTIONS');
});
```

## Authentication Issues

### Token Authentication Failures

**Symptoms:**
- "Invalid token" errors
- "Token expired" messages
- Authentication required errors

**Solutions:**

1. **Verify Token Format:**
```javascript
// Check JWT token structure
const jwt = require('jsonwebtoken');
try {
  const decoded = jwt.decode(token, { complete: true });
  console.log('Token header:', decoded.header);
  console.log('Token payload:', decoded.payload);
} catch (error) {
  console.error('Invalid token format:', error.message);
}
```

2. **Check Token Expiration:**
```javascript
// Verify token expiration
const decoded = jwt.verify(token, secretKey);
const now = Math.floor(Date.now() / 1000);
if (decoded.exp < now) {
  console.error('Token has expired');
}
```

3. **Validate Secret Key:**
```bash
# Ensure secret key is set
echo $JWT_SECRET

# Generate new secret if needed
node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
```

### Certificate Authentication Issues

**Symptoms:**
- Certificate verification failures
- "Untrusted certificate" errors
- SSL handshake errors

**Solutions:**

1. **Check Certificate Validity:**
```bash
# Verify certificate
openssl x509 -in cert.pem -text -noout

# Check certificate expiration
openssl x509 -in cert.pem -enddate -noout

# Verify certificate chain
openssl verify -CAfile ca.pem cert.pem
```

2. **Update Certificate Store:**
```bash
# Update system certificate store
sudo apt-get update && sudo apt-get install ca-certificates

# Or add custom CA
sudo cp ca.pem /usr/local/share/ca-certificates/mcp-ca.crt
sudo update-ca-certificates
```

## Resource Access Issues

### Resource Not Found

**Symptoms:**
- "Resource not found" errors
- Empty resource lists
- Permission denied errors

**Solutions:**

1. **Verify Resource Paths:**
```javascript
// Check if resource exists
import fs from 'fs/promises';

async function checkResource(path) {
  try {
    await fs.access(path);
    console.log('Resource exists:', path);
  } catch (error) {
    console.error('Resource not accessible:', path, error.message);
  }
}
```

2. **Check Path Resolution:**
```javascript
// Debug path resolution
import path from 'path';

const resourcePath = path.resolve('./data/file.txt');
console.log('Resolved path:', resourcePath);
console.log('Path exists:', fs.existsSync(resourcePath));
```

3. **Validate Permissions:**
```bash
# Check file permissions
ls -la /path/to/resource

# Fix permissions if needed
chmod 644 /path/to/file
chmod 755 /path/to/directory
```

### Large Resource Handling

**Symptoms:**
- Memory errors with large files
- Timeout errors
- Performance issues

**Solutions:**

1. **Implement Streaming:**
```javascript
// Stream large files instead of loading into memory
import { createReadStream } from 'fs';

async function streamResource(filePath) {
  const stream = createReadStream(filePath, { encoding: 'utf8' });
  const chunks = [];
  
  for await (const chunk of stream) {
    chunks.push(chunk);
    // Process chunk by chunk
  }
  
  return chunks.join('');
}
```

2. **Add Size Limits:**
```javascript
// Check file size before reading
const stats = await fs.stat(filePath);
const maxSize = 10 * 1024 * 1024; // 10MB

if (stats.size > maxSize) {
  throw new Error(`File too large: ${stats.size} bytes`);
}
```

3. **Implement Pagination:**
```javascript
// Paginate large resource lists
async function listResourcesPaginated(cursor, limit = 100) {
  const offset = cursor ? parseInt(cursor) : 0;
  const resources = await getAllResources();
  
  return {
    resources: resources.slice(offset, offset + limit),
    nextCursor: offset + limit < resources.length ? 
      (offset + limit).toString() : undefined
  };
}
```

## Tool Execution Issues

### Tool Not Found

**Symptoms:**
- "Tool not found" errors
- Tool not appearing in lists
- Method not implemented errors

**Solutions:**

1. **Verify Tool Registration:**
```javascript
// Check tool registration
this.server.setRequestHandler(ListToolsRequestSchema, async () => {
  console.log('Listing tools...');
  return {
    tools: [
      {
        name: "my_tool",
        description: "My custom tool",
        inputSchema: { /* schema */ }
      }
    ]
  };
});
```

2. **Debug Tool Handler:**
```javascript
// Add logging to tool handler
this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
  console.log('Tool call request:', request);
  const { name, arguments: args } = request.params;
  
  console.log(`Executing tool: ${name} with args:`, args);
  
  switch (name) {
    case "my_tool":
      return await this.executeMyTool(args);
    default:
      console.error(`Unknown tool: ${name}`);
      throw new Error(`Unknown tool: ${name}`);
  }
});
```

### Tool Execution Failures

**Symptoms:**
- Tool execution timeouts
- Unexpected tool errors
- Invalid argument errors

**Solutions:**

1. **Add Input Validation:**
```javascript
// Validate tool arguments
function validateToolArgs(schema, args) {
  const Joi = require('joi');
  const joiSchema = convertToJoi(schema);
  
  const { error, value } = joiSchema.validate(args);
  if (error) {
    throw new Error(`Invalid arguments: ${error.details[0].message}`);
  }
  
  return value;
}
```

2. **Implement Timeout Handling:**
```javascript
// Add timeout to tool execution
async function executeToolWithTimeout(toolFunction, args, timeout = 30000) {
  return Promise.race([
    toolFunction(args),
    new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Tool execution timeout')), timeout)
    )
  ]);
}
```

3. **Add Error Recovery:**
```javascript
// Implement retry logic
async function executeToolWithRetry(toolFunction, args, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await toolFunction(args);
    } catch (error) {
      console.warn(`Tool execution attempt ${attempt} failed:`, error.message);
      
      if (attempt === maxRetries) {
        throw error;
      }
      
      // Wait before retry
      await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
    }
  }
}
```

## Performance Issues

### Slow Response Times

**Symptoms:**
- Long delays in responses
- Client timeouts
- High CPU/memory usage

**Solutions:**

1. **Add Performance Monitoring:**
```javascript
// Monitor request performance
const performanceMonitor = {
  startTime: new Map(),
  
  start(requestId) {
    this.startTime.set(requestId, Date.now());
  },
  
  end(requestId) {
    const duration = Date.now() - this.startTime.get(requestId);
    console.log(`Request ${requestId} took ${duration}ms`);
    this.startTime.delete(requestId);
    
    if (duration > 5000) {
      console.warn(`Slow request detected: ${requestId} (${duration}ms)`);
    }
  }
};
```

2. **Implement Caching:**
```javascript
// Simple in-memory cache
class SimpleCache {
  constructor(ttl = 300000) { // 5 minutes
    this.cache = new Map();
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
    this.cache.set(key, {
      value,
      timestamp: Date.now()
    });
  }
}
```

3. **Optimize Database Queries:**
```javascript
// Add query optimization
async function optimizedQuery(query, params) {
  // Add query caching
  const cacheKey = `${query}:${JSON.stringify(params)}`;
  const cached = cache.get(cacheKey);
  if (cached) return cached;
  
  // Add query timeout
  const result = await Promise.race([
    db.query(query, params),
    new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Query timeout')), 10000)
    )
  ]);
  
  cache.set(cacheKey, result);
  return result;
}
```

### Memory Leaks

**Symptoms:**
- Gradually increasing memory usage
- Out of memory errors
- Process crashes

**Solutions:**

1. **Monitor Memory Usage:**
```javascript
// Memory monitoring
setInterval(() => {
  const usage = process.memoryUsage();
  console.log('Memory usage:', {
    rss: Math.round(usage.rss / 1024 / 1024) + 'MB',
    heapUsed: Math.round(usage.heapUsed / 1024 / 1024) + 'MB',
    heapTotal: Math.round(usage.heapTotal / 1024 / 1024) + 'MB'
  });
  
  // Alert on high memory usage
  if (usage.heapUsed > 500 * 1024 * 1024) { // 500MB
    console.warn('High memory usage detected!');
  }
}, 30000);
```

2. **Fix Common Memory Leaks:**
```javascript
// Properly clean up event listeners
class ResourceWatcher extends EventEmitter {
  constructor() {
    super();
    this.watchers = new Map();
  }
  
  watch(path) {
    const watcher = fs.watch(path, (event) => {
      this.emit('change', { path, event });
    });
    
    this.watchers.set(path, watcher);
  }
  
  unwatch(path) {
    const watcher = this.watchers.get(path);
    if (watcher) {
      watcher.close();
      this.watchers.delete(path);
    }
  }
  
  destroy() {
    for (const watcher of this.watchers.values()) {
      watcher.close();
    }
    this.watchers.clear();
    this.removeAllListeners();
  }
}
```

## Debugging Tools

### Enable Debug Logging

```bash
# Environment variables for debugging
export DEBUG=mcp:*
export LOG_LEVEL=debug
export NODE_ENV=development

# Run server with debugging
node --inspect server.js
```

### JSON-RPC Message Tracing

```javascript
// Message tracing utility
class MessageTracer {
  constructor() {
    this.messages = [];
  }
  
  trace(direction, message) {
    const entry = {
      timestamp: new Date().toISOString(),
      direction, // 'in' or 'out'
      message: JSON.parse(JSON.stringify(message))
    };
    
    this.messages.push(entry);
    console.log(`${direction.toUpperCase()}: ${JSON.stringify(message)}`);
    
    // Keep only last 100 messages
    if (this.messages.length > 100) {
      this.messages.shift();
    }
  }
  
  getTrace() {
    return this.messages;
  }
  
  saveTrace(filename) {
    fs.writeFileSync(filename, JSON.stringify(this.messages, null, 2));
  }
}
```

### Health Check Endpoint

```javascript
// Add health check for debugging
app.get('/health', (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    connections: getActiveConnections(),
    version: packageJson.version
  };
  
  res.json(health);
});
```

## Common Error Messages

### "Protocol version mismatch"

**Cause:** Client and server using different MCP protocol versions.

**Solution:**
```javascript
// Check protocol versions
console.log('Client protocol version:', clientProtocolVersion);
console.log('Server protocol version:', serverProtocolVersion);

// Update to compatible versions
npm update @modelcontextprotocol/sdk
```

### "Method not implemented"

**Cause:** Server doesn't implement requested method.

**Solution:**
```javascript
// Add missing method handler
this.server.setRequestHandler(schema, async (request) => {
  // Implementation here
});
```

### "Invalid JSON-RPC request"

**Cause:** Malformed JSON-RPC message.

**Solution:**
```javascript
// Validate message format
function validateJsonRpc(message) {
  if (!message.jsonrpc || message.jsonrpc !== '2.0') {
    throw new Error('Invalid JSON-RPC version');
  }
  
  if (!message.method) {
    throw new Error('Missing method');
  }
  
  if (message.id === undefined && message.method.startsWith('notifications/')) {
    // Notification - no ID required
  } else if (message.id === undefined) {
    throw new Error('Missing request ID');
  }
}
```

## Getting Help

When troubleshooting issues:

1. **Check the logs** for error messages and stack traces
2. **Enable debug mode** to see detailed operation logs
3. **Test with minimal examples** to isolate the problem
4. **Check GitHub issues** for similar problems and solutions
5. **Join the community Discord** for real-time help
6. **Create a minimal reproduction** when reporting bugs

### Reporting Issues

When reporting issues, include:

- MCP SDK version
- Node.js/Python version
- Operating system
- Complete error messages
- Minimal code to reproduce the issue
- Steps to reproduce the problem

### Useful Resources

- **GitHub Issues**: [MCP Repository Issues](https://github.com/modelcontextprotocol/mcp/issues)
- **Discord Community**: [MCP Discord Server](https://discord.gg/mcp)
- **Documentation**: [Official MCP Docs](https://modelcontextprotocol.io)
- **Examples**: [MCP Examples Repository](https://github.com/modelcontextprotocol/examples)
