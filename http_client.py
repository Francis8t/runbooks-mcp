"""Connect to the Runbooks server over remote Streamable HTTP — by URL, not by
launching a subprocess. Start serve_http.py first (in another terminal), then
run this.

    python http_client.py
"""
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://127.0.0.1:8000/mcp"


async def main():
    # streamable-http returns a 3-TUPLE: (read, write, get_session_id).
    # The 3rd item is a session handle — HTTP is stateful in a way stdio isn't.
    async with streamablehttp_client(URL) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            resources = await session.list_resources()
            prompts = await session.list_prompts()
            print(f"Connected over HTTP to {URL}")
            print("TOOLS     :", [t.name for t in tools.tools])
            print("RESOURCES :", [str(x.uri) for x in resources.resources])
            print("PROMPTS   :", [p.name for p in prompts.prompts])


if __name__ == "__main__":
    asyncio.run(main())
