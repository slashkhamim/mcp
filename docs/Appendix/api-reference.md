---
title: API Reference
sidebar_position: 1
---

# MCP API Reference

Complete reference for the Model Context Protocol JSON-RPC API.

## Protocol Overview

MCP uses JSON-RPC 2.0 for communication between clients and servers. All messages follow the JSON-RPC specification with MCP-specific method names and parameters.

### Message Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "method_name",
  "params": {
    "parameter": "value"
  }
}
```

### Response Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "data": "response_data"
  }
}
```

### Error Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "details": "Additional error information"
    }
  }
}
```

## Core Methods

### Initialize

Establishes the connection and exchanges capabilities between client and server.

**Method:** `initialize`

**Parameters:**
```typescript
interface InitializeParams {
  protocolVersion: string;
  capabilities: ClientCapabilities;
  clientInfo: {
    name: string;
    version: string;
  };
}

interface ClientCapabilities {
  roots?: {
    listChanged?: boolean;
  };
  sampling?: {};
}
```

**Response:**
```typescript
interface InitializeResult {
  protocolVersion: string;
  capabilities: ServerCapabilities;
  serverInfo: {
    name: string;
    version: string;
  };
}

interface ServerCapabilities {
  prompts?: {
    listChanged?: boolean;
  };
  resources?: {
    subscribe?: boolean;
    listChanged?: boolean;
  };
  tools?: {
    listChanged?: boolean;
  };
}
```

**Example:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "roots": {
        "listChanged": true
      }
    },
    "clientInfo": {
      "name": "ExampleClient",
      "version": "1.0.0"
    }
  }
}
```

### Ping

Health check to verify server responsiveness.

**Method:** `ping`

**Parameters:** None

**Response:**
```typescript
interface PingResult {
  // Empty object
}
```

**Example:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "ping"
}
```

## Resource Methods

### List Resources

Retrieves a list of available resources from the server.

**Method:** `resources/list`

**Parameters:**
```typescript
interface ListResourcesParams {
  cursor?: string;
}
```

**Response:**
```typescript
interface ListResourcesResult {
  resources: Resource[];
  nextCursor?: string;
}

interface Resource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
  annotations?: {
    audience?: string[];
    priority?: number;
    [key: string]: unknown;
  };
}
```

**Example:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "resources/list",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "resources": [
      {
        "uri": "file:///path/to/document.md",
        "name": "Project Documentation",
        "description": "Main project documentation",
        "mimeType": "text/markdown",
        "annotations": {
          "audience": ["developers"],
          "priority": 1
        }
      }
    ]
  }
}
```

### Read Resource

Retrieves the content of a specific resource.

**Method:** `resources/read`

**Parameters:**
```typescript
interface ReadResourceParams {
  uri: string;
}
```

**Response:**
```typescript
interface ReadResourceResult {
  contents: ResourceContents[];
}

interface ResourceContents {
  uri: string;
  mimeType?: string;
  text?: string;
  blob?: string; // Base64 encoded binary data
}
```

**Example:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "resources/read",
  "params": {
    "uri": "file:///path/to/document.md"
  }
}
```

### Subscribe to Resource

Subscribe to updates for a specific resource.

**Method:** `resources/subscribe`

**Parameters:**
```typescript
interface SubscribeParams {
  uri: string;
}
```

**Response:**
```typescript
interface SubscribeResult {
  // Empty object
}
```

### Unsubscribe from Resource

Unsubscribe from updates for a specific resource.

**Method:** `resources/unsubscribe`

**Parameters:**
```typescript
interface UnsubscribeParams {
  uri: string;
}
```

## Tool Methods

### List Tools

Retrieves a list of available tools from the server.

**Method:** `tools/list`

**Parameters:**
```typescript
interface ListToolsParams {
  cursor?: string;
}
```

**Response:**
```typescript
interface ListToolsResult {
  tools: Tool[];
  nextCursor?: string;
}

interface Tool {
  name: string;
  description?: string;
  inputSchema: JSONSchema;
}

interface JSONSchema {
  type: string;
  properties?: Record<string, JSONSchema>;
  required?: string[];
  items?: JSONSchema;
  [key: string]: unknown;
}
```

**Example:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/list"
}
```

### Call Tool

Executes a tool with the provided arguments.

**Method:** `tools/call`

**Parameters:**
```typescript
interface CallToolParams {
  name: string;
  arguments?: Record<string, unknown>;
}
```

**Response:**
```typescript
interface CallToolResult {
  content: ToolContent[];
  isError?: boolean;
}

interface ToolContent {
  type: "text" | "image" | "resource";
  text?: string;
  data?: string; // Base64 for images
  resource?: {
    uri: string;
    mimeType?: string;
  };
  annotations?: {
    audience?: string[];
    priority?: number;
    [key: string]: unknown;
  };
}
```

**Example:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "search_files",
    "arguments": {
      "query": "TODO",
      "path": "/project"
    }
  }
}
```

## Prompt Methods

### List Prompts

Retrieves a list of available prompt templates.

**Method:** `prompts/list`

**Parameters:**
```typescript
interface ListPromptsParams {
  cursor?: string;
}
```

**Response:**
```typescript
interface ListPromptsResult {
  prompts: Prompt[];
  nextCursor?: string;
}

interface Prompt {
  name: string;
  description?: string;
  arguments?: PromptArgument[];
}

interface PromptArgument {
  name: string;
  description?: string;
  required?: boolean;
}
```

### Get Prompt

Retrieves a prompt template with arguments filled in.

**Method:** `prompts/get`

**Parameters:**
```typescript
interface GetPromptParams {
  name: string;
  arguments?: Record<string, string>;
}
```

**Response:**
```typescript
interface GetPromptResult {
  description?: string;
  messages: PromptMessage[];
}

interface PromptMessage {
  role: "user" | "assistant" | "system";
  content: PromptContent;
}

interface PromptContent {
  type: "text" | "image" | "resource";
  text?: string;
  data?: string;
  resource?: {
    uri: string;
    mimeType?: string;
  };
  annotations?: Record<string, unknown>;
}
```

## Notification Methods

### Resource Updated

Notifies clients when a subscribed resource has been updated.

**Method:** `notifications/resources/updated`

**Parameters:**
```typescript
interface ResourceUpdatedParams {
  uri: string;
}
```

**Example:**
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/resources/updated",
  "params": {
    "uri": "file:///path/to/document.md"
  }
}
```

### Resource List Changed

Notifies clients when the list of available resources has changed.

**Method:** `notifications/resources/list_changed`

**Parameters:** None

### Tool List Changed

Notifies clients when the list of available tools has changed.

**Method:** `notifications/tools/list_changed`

**Parameters:** None

### Prompt List Changed

Notifies clients when the list of available prompts has changed.

**Method:** `notifications/prompts/list_changed`

**Parameters:** None

## Error Codes

MCP uses standard JSON-RPC error codes plus custom codes:

| Code | Message | Description |
|------|---------|-------------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Invalid JSON-RPC request |
| -32601 | Method not found | Method doesn't exist |
| -32602 | Invalid params | Invalid method parameters |
| -32603 | Internal error | Server internal error |
| -32000 | Server error | Generic server error |
| -32001 | Resource not found | Requested resource doesn't exist |
| -32002 | Tool not found | Requested tool doesn't exist |
| -32003 | Permission denied | Access denied |
| -32004 | Rate limited | Too many requests |
| -32005 | Timeout | Request timeout |

## Transport Protocols

### Standard I/O (stdio)

Communication over standard input/output streams.

**Client Example:**
```javascript
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const transport = new StdioClientTransport({
  command: 'node',
  args: ['server.js']
});
```

**Server Example:**
```javascript
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

const transport = new StdioServerTransport();
await server.connect(transport);
```

### WebSocket

Communication over WebSocket connections.

**Client Example:**
```javascript
import { WebSocketClientTransport } from '@modelcontextprotocol/sdk/client/websocket.js';

const transport = new WebSocketClientTransport('ws://localhost:3000/mcp');
```

**Server Example:**
```javascript
import { WebSocketServerTransport } from '@modelcontextprotocol/sdk/server/websocket.js';

const transport = new WebSocketServerTransport({
  port: 3000,
  path: '/mcp'
});
```

### HTTP/HTTPS

Communication over HTTP with long polling or Server-Sent Events.

**Client Example:**
```javascript
import { HttpClientTransport } from '@modelcontextprotocol/sdk/client/http.js';

const transport = new HttpClientTransport('https://api.example.com/mcp');
```

## SDK Reference

### Server SDK

```typescript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';

class MyServer {
  constructor() {
    this.server = new Server(
      {
        name: "my-server",
        version: "1.0.0"
      },
      {
        capabilities: {
          resources: {},
          tools: {},
          prompts: {}
        }
      }
    );
  }
}
```

### Client SDK

```typescript
import { Client } from '@modelcontextprotocol/sdk/client/index.js';

class MyClient {
  constructor() {
    this.client = new Client(
      {
        name: "my-client",
        version: "1.0.0"
      },
      {
        capabilities: {
          roots: {}
        }
      }
    );
  }
}
```

## Authentication

### Bearer Token

```http
Authorization: Bearer <token>
```

### Client Certificate

TLS client certificate authentication for secure connections.

### Custom Authentication

Servers can implement custom authentication schemes through the transport layer.

## Rate Limiting

Servers should implement rate limiting to prevent abuse:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32004,
    "message": "Rate limited",
    "data": {
      "retryAfter": 60,
      "limit": 100,
      "window": 3600
    }
  }
}
```

## Versioning

MCP uses semantic versioning for the protocol. Clients and servers should negotiate the protocol version during initialization.

**Current Version:** `2024-11-05`

## Extensions

Servers can provide custom methods by prefixing them with their domain:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "example.com/custom_method",
  "params": {
    "custom_param": "value"
  }
}
```

## Best Practices

1. **Always validate input parameters** before processing
2. **Use appropriate error codes** for different error conditions
3. **Implement proper timeout handling** for long-running operations
4. **Provide meaningful error messages** with context
5. **Use structured logging** for debugging and monitoring
6. **Implement graceful degradation** when features are unavailable
7. **Cache responses** when appropriate to improve performance
8. **Use compression** for large payloads
9. **Implement proper authentication** and authorization
10. **Follow the principle of least privilege** for resource access
