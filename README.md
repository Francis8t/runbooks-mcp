# Runbooks MCP Server — all three primitives, local → remote → OAuth-secured

A **Model Context Protocol (MCP)** server for on-call engineering runbooks, built as a ground-up study of MCP: it implements **all three MCP primitives** (tools, resources, prompts), runs over **both transports** (stdio and remote Streamable HTTP), and is secured as a proper **OAuth 2.1 resource server** that validates Amazon Cognito JWTs against the issuer's public keys.

The goal wasn't "use an MCP tool" — it was to *author, serve, secure, and understand* an MCP server end-to-end, including the server side of OAuth that most tutorials skip.

---

## Why this exists

Most MCP examples only ever expose **tools**. This server deliberately implements the two primitives people skip, because the real insight of MCP is **who controls each primitive**:

| Primitive | Controlled by | In this server |
|---|---|---|
| **Tools** | the **model** (chosen mid-reasoning) | `search_runbooks`, `log_incident` (side-effecting) |
| **Resources** | the **application** (loaded by URI) | `runbooks://catalog`, `runbook://{slug}` (templated) |
| **Prompts** | the **user** (explicitly selected) | `postmortem`, `summarize_runbook` |

That model/app/user distinction — not "what they do" but "who triggers them" — is the conceptual core.

---

## Architecture

```
                         ┌─────────────────────────── Runbooks MCP server ───────────┐
  client                 │  resources: runbooks://catalog, runbook://{slug}  (app)   │
  (stdio OR HTTPS) ─────▶ │  tools:     search_runbooks, log_incident         (model) │
                         │  prompts:   postmortem, summarize_runbook         (user)  │
                         └────────────────────────────────────────────────────────────┘

  Transport A — stdio          : client launches the server as a subprocess (local, 1:1)
  Transport B — Streamable HTTP: long-lived server, clients connect by URL (remote, multi-client)

  Auth (Transport B):
    client ──Bearer JWT──▶ [ CognitoVerifier ] ──verify sig via JWKS, iss, exp, scope──▶ tools
                                   ▲
                            Amazon Cognito (M2M client-credentials, scope: runbooks-mcp/invoke)
    no / invalid token  ──▶ 401 Unauthorized  (rejected before any tool code runs)
```

The same server definition (`build_server()`) powers all three run modes — **transport and auth are layered on without touching the primitive code**, which is the point: what a server *offers* is orthogonal to *how* it's reached and secured.

---

## Project layout

```
.
├── runbooks_server.py   # the server: build_server() factory + all 3 primitives; stdio entrypoint
├── inspect_client.py    # stdio client — lists tools/resources/prompts, reads one of each
├── serve_http.py        # same server over plain Streamable HTTP
├── http_client.py       # HTTP client (connects by URL)
├── serve_http_auth.py   # HTTP server + CognitoVerifier (OAuth resource server)
├── auth_client.py       # HTTP client that presents a Cognito bearer token
├── cognito-mcp.yaml     # CloudFormation: minimal Cognito (user pool + resource server + M2M client)
└── requirements.txt
```

---

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # mcp<2, pyjwt[crypto]
```

**1 · Local (stdio)** — the client launches the server:
```bash
python inspect_client.py
# → TOOLS / RESOURCES / TEMPLATES / PROMPTS all listed, one read + one prompt exercised
```

**2 · Remote (Streamable HTTP)** — two terminals:
```bash
python serve_http.py          # terminal 1: http://127.0.0.1:8000/mcp
python http_client.py         # terminal 2: connects by URL
```

**3 · Secured (OAuth)** — deploy Cognito, then require a token:
```bash
aws cloudformation deploy --template-file cognito-mcp.yaml \
  --stack-name runbooks-cognito --region us-east-1
# export ISSUER_URL / JWKS_URL / REQUIRED_SCOPE / SERVER_URL from the stack outputs
python serve_http_auth.py     # terminal 1: now requires a valid JWT
python http_client.py         # → 401 (no token)
export TOKEN=<client_credentials access token>
python auth_client.py         # → authenticated, tools listed
```

---

## Security model

The authed server is an **OAuth 2.1 resource server**, not a shared-secret check:

- A custom `TokenVerifier` fetches Cognito's **JWKS** and validates each bearer token's **signature (RS256), issuer, expiry, `token_use`, and scope** — returning `401` (with a spec-compliant `WWW-Authenticate` header and `/.well-known/oauth-protected-resource` metadata) for anything invalid.
- Rejection happens in middleware **before any tool/resource/prompt code runs** — defence-in-depth at the authentication layer.
- Tokens come from Cognito's **machine-to-machine (client-credentials)** flow, carrying the scope `runbooks-mcp/invoke`.

This is the *server* side of OAuth — verifying tokens rather than presenting them.

---

## Integration note (AgentCore Gateway)

This server is designed to drop into an **Amazon Bedrock AgentCore Gateway** as an `mcp-server` target (`--type mcp-server --outbound-auth oauth`), so its tools surface through a governed, observable Gateway alongside other targets — Gateway authenticating *outbound* to this server's verifier, the mirror image of the inbound auth above.

---

## Cost & teardown

Everything runs locally except the optional Cognito pool. Cognito is free at this volume (M2M token requests are fractions of a cent). Tear down with:
```bash
aws cloudformation delete-stack --stack-name runbooks-cognito --region us-east-1
```

---

## What this demonstrates

- MCP authored from scratch: **all three primitives**, with a clear grasp of the model/app/user control model.
- **Transport independence** — stdio vs Streamable HTTP as a deployment choice, not a rewrite (one `build_server()`, three entrypoints).
- A real **OAuth resource server**: JWKS-based JWT verification, issuer/scope/expiry checks, spec-compliant `401`s.
- Current-spec awareness (2026): Streamable HTTP over the deprecated SSE transport; stateless, OAuth-aligned MCP.

---

## Acknowledgments

A self-directed capstone for the *Become a Solutions Architect — Agentic AI on AWS* track (Week 5, MCP), built on the open **Model Context Protocol** specification and the Python `mcp` SDK (FastMCP).