"""Inspect the Runbooks MCP server over stdio: list all three primitives,
then read one resource and fetch one prompt. No model/Bedrock involved —
this is pure MCP protocol, the clean way to develop a server.

Run: python inspect_client.py   (launches runbooks_server.py as a subprocess)
"""
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runbooks_server.py")


async def main():
    # sys.executable = the same interpreter running this script (pyenv/venv-safe)
    params = StdioServerParameters(command=sys.executable, args=[SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            resources = await session.list_resources()
            templates = await session.list_resource_templates()
            prompts = await session.list_prompts()

            print("TOOLS     :", [t.name for t in tools.tools])
            print("RESOURCES :", [str(x.uri) for x in resources.resources])
            print("TEMPLATES :", [x.uriTemplate for x in templates.resourceTemplates])
            print("PROMPTS   :", [p.name for p in prompts.prompts])

            rb = await session.read_resource("runbook://db-failover")
            print("\nread runbook://db-failover ->\n" + rb.contents[0].text)

            pr = await session.get_prompt("postmortem", {"incident_title": "DB outage"})
            print("\nget prompt 'postmortem' ->\n" + pr.messages[0].content.text)


if __name__ == "__main__":
    asyncio.run(main())
