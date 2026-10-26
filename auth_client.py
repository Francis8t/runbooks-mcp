"""Connect to the AUTHED Runbooks server, presenting a Cognito bearer token.

    export TOKEN=<access token from the client_credentials flow>
    python auth_client.py
"""
import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

TOKEN = os.environ["TOKEN"]
URL = os.environ.get("SERVER_URL", "http://127.0.0.1:8000/mcp")


async def main():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with streamablehttp_client(URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Authenticated OK — tools:", [t.name for t in tools.tools])


if __name__ == "__main__":
    asyncio.run(main())
