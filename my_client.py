import asyncio
from fastmcp import Client

client = Client("https://tutorial.fastmcp.app/mcp")

async def call_tool(text: str):
    async with client:
        result = await client.call_tool("alphabetize_string", {"text": text})
        print(result)

asyncio.run(call_tool("Mark Kramer"))