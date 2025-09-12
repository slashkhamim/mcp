# 📘 Secure MCP Server Design – A Practical Guide

This document collects key security concepts and patterns for building and running **MCP (Model Context Protocol) servers**. It explains identity, authorization, secret management, and network controls across different integration scenarios.

---

## 1. Why MCP Security Matters
MCP servers often control sensitive tools (databases, Jira, GitHub, Slack, etc.). Without proper controls:
- Users could over-reach (access data they shouldn’t).  
- Secrets could leak (long-lived API keys).  
- One tenant could see another’s data in a SaaS setup.  
- Attacks like SSRF, replay, or token theft could succeed.  

**Principle:** Treat MCP servers like product APIs — enforce zero-trust, least-privilege, short-lived credentials, and full auditability.

---

## 2. Core Security Building Blocks

### Identity & Tokens
- **IdP** (Identity Provider): Users authenticate here (Okta, Azure AD, Google, Keycloak).  
- **MCP Proxy**: Trust broker. Verifies IdP tokens, maps roles → scopes, mints **short-lived JWTs** for MCP servers.  
- **MCP Servers**: Verify JWT signature via JWKS, enforce scopes, perform the requested tool action.  

### Authorization
- **RBAC (Role-Based Access Control):** Map IdP groups/roles → MCP scopes.  
- **Tenant separation (multi-tenant SaaS):** Always enforce `org_id`.  
- **Policy engine (optional):** Fine-grained checks (OPA/Rego or custom rules).  

### Secrets
- **Per-user OAuth:** Proxy stores refresh tokens encrypted; servers see only short-lived access tokens.  
- **Service account integrations:** Long-lived keys stay in vault; injected at runtime via sidecar or egress gateway.  

### JWKS lifecycle
- Proxy signs JWTs with private key.  
- Publishes JWKS (`/.well-known/jwks.json`) with public keys.  
- Servers fetch/caches keys, validate `kid`, `iss`, `aud`, `exp`.  
- Rotate keys regularly; publish old+new until old tokens expire.  

---

## 3. MCP Server Archetypes

### A) Internal Systems (own DB / APIs)
- **Use case:** Internal HR DB, project metrics.  
- **Identity:** Internal IdP.  
- **AuthZ:** RBAC only; no tenant isolation needed.  
- **Key Risk:** Over-permissive roles.  
- **Example:** Employee asks “How many vacation days do I have left?” → MCP queries HR DB.

### B) Third-party integrations (per-user OAuth)
- **Use case:** Jira, GitHub on behalf of user.  
- **Identity:** User authenticates with IdP and authorizes provider via OAuth.  
- **Secrets:** Proxy stores refresh token; server sees only short-lived access token.  
- **Key Risk:** Never expose refresh token to MCP.  
- **Example:** “File a Jira bug” → server calls Jira with user’s access token.

### C) Third-party integrations (service account)
- **Use case:** Slack bot posts to channel, Datadog metrics, Stripe billing.  
- **Identity:** System-level bot/service account.  
- **Secrets:** Long-lived API key stays in vault.  
  - **Option 1:** Sidecar injects `Authorization` header.  
  - **Option 2:** Egress gateway injects centrally.  
- **Key Risk:** Token leakage if directly given to MCP.  
- **Example:** “Announce deployment” → Slack bot posts in `#releases`.

### D) Hybrid hub (own DB + third parties + per-user OAuth)
- **Use case:** Combine internal DB with external APIs (e.g., orders + shipping tracking).  
- **Identity:** IdP for login; per-user OAuth for shipping provider.  
- **Key Risk:** Mixing trust boundaries.  
- **Example:** “Where is order 123?” → query DB + DHL API.

---

## 4. Sidecar vs. Egress Gateway

### Sidecar
- Runs next to each MCP service (e.g., Envoy/Nginx container).  
- Injects headers, enforces per-service allowlists.  
- Good for small setups; simple mental model.  
- Analogy: a personal bodyguard.

### Egress Gateway
- Centralized proxy cluster at the network edge.  
- All outbound traffic must pass through it.  
- Central place for allowlists, header injection, audit.  
- Good for multi-tenant SaaS or compliance needs.  
- Analogy: a building’s security checkpoint.

---

## 5. Secure Practices Across All Scenarios

- **Short-lived tokens:** 5–15 min TTL for JWTs and provider tokens.  
- **Replay protection:** Use `jti`, `request_id`, idempotency keys.  
- **Egress controls:** Allowlist domains, block private IP ranges, strip user headers.  
- **Audit:** Hash-chained logs; log request ID, org, scope; never secrets.  
- **Rotation:** Regular key and token rotation; overlap old+new briefly.  
- **Rate limits:** Per-user and per-tenant quotas.  
- **Runtime hardening:** Non-root users, read-only FS, minimal containers, no shell.  

---

## 6. Choosing the Right Pattern

| Use case | Pattern |
|----------|---------|
| Internal tools (1 org) | **A – Internal single-tenant** |
| SaaS app (multi-org) | **B – Multi-tenant** |
| End-user actions in Jira/GitHub | **C – Per-user OAuth** |
| System-wide bots (Slack, billing) | **D – Service account** |
| Combine internal + external | **E – Hybrid** |
| Dangerous actions (infra control) | **F – High-risk tools** |

---

## 7. Takeaways
- Keep **long-lived secrets in the proxy or vault** — never in MCP servers.  
- **JWTs and provider tokens must be short-lived**; rotate and audit.  
- Choose **sidecar vs. egress gateway** depending on scale and compliance needs.  
- **Always log and audit**: who did what, under which tenant, at what time.  
- Build playbooks for rotation, abuse spikes, and incident handling.  

---

👉 With these patterns, you can design MCP servers that are **secure, auditable, and tenant-safe**, whether they talk only to your DB or orchestrate across multiple providers.
