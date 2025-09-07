import asyncio
from fastmcp import Client

client = Client("https://tutorial.fastmcp.app/mcp")

async def call_mcp_tool(text: str):
    async with client:
        result = await client.call_mcp_tool("alphabetize_string", {"s": text})
        print(result)

asyncio.run(call_mcp_tool("Mark Kramer"))