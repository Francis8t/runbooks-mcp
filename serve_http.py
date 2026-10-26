"""Run the SAME Runbooks server over remote Streamable HTTP instead of stdio.

Only the TRANSPORT changes — the tools/resources/prompts are identical (we import
the exact same `mcp` object from runbooks_server). Unlike stdio, this is a
long-lived process you start yourself; clients then connect to it by URL.

    python serve_http.py        # serves at http://127.0.0.1:8000/mcp
"""
from runbooks_server import mcp  # same server, all 3 primitives already registered

if __name__ == "__main__":
    # host / port / streamable_http_path default to 127.0.0.1 : 8000 : /mcp
    mcp.run(transport="streamable-http")
