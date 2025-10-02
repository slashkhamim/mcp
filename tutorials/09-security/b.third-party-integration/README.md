# Third-Party Integration Authentication Tutorial

This tutorial demonstrates how to implement secure authentication for third-party systems using MCP (Model Context Protocol) with enterprise Identity Provider (IdP) integration.

## Architecture Overview

```
[Employee/Contractor] → [Company IdP] → [RBAC Proxy] → [MCP Server] → [Third-Party API]
```

### Key Components:

1. **IdP Client**: Authenticates with company IdP (Okta, Azure AD, Google Workspace, Keycloak)
2. **RBAC Proxy**: Verifies IdP tokens, applies role-based access control, mints short-lived JWTs
3. **MCP Server**: Validates JWTs via JWKS and provides secure access to third-party resources

### Security Features:

- Single-tenant trust boundary (organization-only access)
- Role-based access control (RBAC) mapping IdP groups to scopes
- Short-lived JWT tokens for enhanced security
- JWKS-based token validation
- Comprehensive audit logging

## Quick Start

1. **Install Dependencies**:
   ```bash
   uv sync
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your IdP and database settings
   ```

4. **Start RBAC Proxy**:
   ```bash
   uv run python rbac_proxy.py
   ```

5. **Start MCP Server**:
   ```bash
   uv run python mcp_server.py
   ```

6. **Start MCP Client**:
   ```bash
   uv run python mcp_client.py
   ```

## Configuration

### Environment Variables

- `IDP_TYPE`: Identity provider type (okta, azure, google, keycloak)
- `IDP_DOMAIN`: Your IdP domain
- `IDP_CLIENT_ID`: OAuth client ID
- `IDP_CLIENT_SECRET`: OAuth client secret
- `JWT_SECRET_KEY`: Secret for JWT signing
- `DATABASE_URL`: Internal database connection string

### Role Mapping

Configure role mappings in `config/role_mappings.yaml`:

```yaml
roles:
  maintainer:
    scopes: ["api:github:*"]
  developer:
    scopes: ["api:github:read", "api:github:write", "api:github:issue:read", "api:github:issue:write", "api:github:repo:read", "api:github:repo:write"]
  readonly:
    scopes: ["api:github:read", "api:github:issue:read", "api:github:repo:read"]
```

## Usage Examples

See `examples/` directory for complete usage examples with different IdP providers.

## Security Considerations

- JWT tokens have short expiration times (15 minutes default)
- RBAC policies are enforced at multiple layers

## Run the client

```bash
uv run python mcp_client.py
```

## Troubleshooting

See `docs/troubleshooting.md` for common issues and solutions.
