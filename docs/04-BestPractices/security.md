---
title: Authentication & Authorization
sidebar_position: 1
---

# MCP Security Scenarios

This document explains the security concepts shown in the diagram. It outlines different ways to secure an MCP (Model Context Protocol) server depending on whether it interacts with **internal systems** or **third-party APIs**.

---

## 📊 Overview

The diagram illustrates **four common security scenarios**:

1. Internal systems (own DB / APIs)  
2. Third-party integrations (per-user OAuth)  
3. Third-party integrations (service account)  
4. Hybrid hub (internal DB + third parties + per-user OAuth)  

Each scenario defines how **identity, authorization, and secrets** are handled.

---

## 1. Internal Systems (own DB / APIs)

- **Use case:** Employees or contractors accessing internal data (e.g., HR DB).  
- **Identity:** Users authenticate via company IdP (Okta, Azure AD, Google Workspace, Keycloak).  
- **Authorization:** RBAC maps IdP groups → scopes (e.g., HR role → `db:read:employee`).  
- **Flow:**
  1. Client/agent authenticates with IdP.  
  2. Proxy verifies token, applies RBAC, mints a short-lived JWT.  
  3. MCP server validates JWT (via JWKS) and queries internal DB/APIs.  

🔑 **Key point:** Single-tenant trust boundary (your org only). No tenant separation needed.

---

## 2. Third-party Integrations (Per-user OAuth)

- **Use case:** MCP needs to act as the end user in a third-party system (e.g., Jira, GitHub).  
- **Identity:** Login with IdP + per-user OAuth with the provider.  
- **Authorization:** Proxy holds encrypted refresh tokens, mints short-lived access tokens per call.  
- **Flow:**
  1. Client/agent authenticates with IdP.  
  2. Proxy manages OAuth consent & token exchange with provider.  
  3. MCP server receives only **short-lived access tokens**.  
  4. Server calls provider API as the logged-in user.  

🔑 **Key point:** Actions reflect the end user’s actual permissions in the third-party system.

---

## 3. Third-party Integrations (Service Account)

- **Use case:** MCP performs system-wide actions (e.g., Slack bot posting announcements).  
- **Identity:** Service account credential managed centrally.  
- **Secret management:**  
  - Long-lived secrets stored in proxy vault (Secrets Manager, Vault, KMS).  
  - MCP server never sees them directly.  
- **Flow:**
  1. MCP server builds outbound request.  
  2. Request goes through a **sidecar or egress gateway**.  
  3. Gateway injects the `Authorization` header using the stored secret.  
  4. Request reaches third-party API with proper service account credentials.  

🔑 **Key point:** Suitable when actions are **system-wide** and not tied to a specific user. Scope the service account narrowly.

---

## 4. Hybrid Hub (Internal DB + Third-party APIs)

- **Use case:** MCP combines internal data with third-party APIs (e.g., order DB + DHL tracking).  
- **Identity:** Login with IdP + per-user OAuth for external systems.  
- **Authorization:** Proxy enforces both internal scopes and external OAuth grants.  
- **Flow:**
  1. Client/agent authenticates with IdP.  
  2. Proxy issues JWT with user + org claims.  
  3. If external call needed, proxy refreshes access token just-in-time.  
  4. MCP server queries both internal DB and external API.  

🔑 **Key point:** Most complex pattern — spans multiple trust boundaries.

---

## 🔒 Security Principles Across All Scenarios

- **Short-lived tokens**: Always use tokens with 5–15 min TTL.  
- **JWKS verification**: MCP servers fetch proxy public keys and verify JWT signatures.  
- **IdP + RBAC**: Centralize authentication and map roles → tool scopes.  
- **Tenant isolation**: In multi-tenant SaaS, every JWT must carry an `org_id`.  
- **Audit logs**: Always log `request_id`, user, tenant, and scopes (never raw secrets).  
- **Network allowlists**: Only permit traffic to approved domains.  
- **Secret isolation**: Long-lived refresh tokens and API keys live only in the proxy vault.  

---

## ✅ Choosing the Right Scenario

| Use case | Recommended pattern |
|----------|----------------------|
| Internal-only tools (HR DB, company metrics) | **Internal systems (A)** |
| User-specific actions in third-party tools | **Per-user OAuth (B)** |
| System-wide integrations (Slack bot, billing, monitoring) | **Service account (C)** |
| Combining internal + external APIs | **Hybrid hub (D)** |

---

## 📌 Summary

- **A – Internal:** IdP + RBAC, single org.  
- **B – Per-user OAuth:** Reflects end-user permissions in external APIs.  
- **C – Service account:** Scoped system-level bots with secrets isolated at proxy.  
- **D – Hybrid:** Combines both, needs strongest controls.  

All scenarios share the same baseline: **short-lived JWTs, strict scopes, tenant isolation, and auditability.**
