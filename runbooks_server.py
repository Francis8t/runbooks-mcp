"""Runbooks MCP server — all three primitives, now via a build_server() factory
so the SAME definition can run stdio, plain HTTP, or authed HTTP.

Primitives, by WHO controls each:
  RESOURCES (app) · TOOLS (model) · PROMPTS (user)
"""
from mcp.server.fastmcp import FastMCP

RUNBOOKS = {
    "db-failover": {"title": "Database Failover",
                    "steps": ["Confirm primary is down", "Promote standby replica",
                              "Repoint the writer endpoint", "Verify writes", "Post status update"]},
    "cache-flush": {"title": "Cache Flush",
                    "steps": ["Drain traffic", "Flush the cache cluster", "Warm critical keys",
                              "Restore traffic"]},
    "cert-renewal": {"title": "TLS Certificate Renewal",
                     "steps": ["Issue new cert via ACM", "Attach to the load balancer",
                               "Verify chain", "Remove the old cert"]},
}
INCIDENTS = []


def build_server(auth=None, token_verifier=None) -> FastMCP:
    """Construct the Runbooks server. Pass auth + token_verifier to require JWTs."""
    kwargs = {}
    if auth is not None:
        kwargs["auth"] = auth
    if token_verifier is not None:
        kwargs["token_verifier"] = token_verifier
    mcp = FastMCP("Runbooks", **kwargs)

    # RESOURCES — app-controlled, URI-addressed
    @mcp.resource("runbooks://catalog")
    def catalog() -> str:
        return "\n".join(f"- {s}: {rb['title']}" for s, rb in RUNBOOKS.items())

    @mcp.resource("runbook://{slug}")
    def runbook(slug: str) -> str:
        rb = RUNBOOKS.get(slug)
        if not rb:
            return f"No runbook found for '{slug}'."
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(rb["steps"], 1))
        return f"# {rb['title']}\n\n{steps}"

    # TOOLS — model-controlled actions
    @mcp.tool()
    def search_runbooks(query: str) -> dict:
        """Search runbooks by keyword in title or steps."""
        q = query.lower()
        hits = [{"slug": s, "title": rb["title"]} for s, rb in RUNBOOKS.items()
                if q in rb["title"].lower() or any(q in st.lower() for st in rb["steps"])]
        return {"count": len(hits), "matches": hits}

    @mcp.tool()
    def log_incident(title: str, severity: str = "sev3") -> dict:
        """Record an incident in the on-call log (side-effecting)."""
        entry = {"id": len(INCIDENTS) + 1, "title": title, "severity": severity}
        INCIDENTS.append(entry)
        return {"status": "logged", **entry}

    # PROMPTS — user-controlled templates
    @mcp.prompt()
    def postmortem(incident_title: str) -> str:
        """Draft a blameless postmortem for an incident."""
        return (f"Write a blameless postmortem for '{incident_title}': timeline, impact, "
                f"root cause, what went well/badly, and action items with owners.")

    @mcp.prompt()
    def summarize_runbook(slug: str) -> str:
        """Summarize a runbook into an on-call checklist."""
        return (f"Summarize the runbook at runbook://{slug} into a tight numbered "
                f"checklist, one line per step.")

    return mcp


mcp = build_server()  # default no-auth instance (stdio + plain HTTP entrypoints use this)

if __name__ == "__main__":
    mcp.run()  # stdio