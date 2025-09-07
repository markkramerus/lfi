from fastmcp import FastMCP
import asyncio
from fastmcp import Client

client = Client("https://tutorial.fastmcp.app/mcp")


mcp = FastMCP("My MCP Server")

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

@mcp.tool
def shuffle_string(s: str) -> str:
    import random
    # Convert the string to a list of characters
    char_list = list(s)
    # Shuffle the list in place
    random.shuffle(char_list)
    # Join the shuffled characters back into a string
    return ''.join(char_list)

@mcp.tool
async def call_mcp_tool(tool: str, args: dict) -> str:
    async def call_tool(tool: str, args: dict) -> str:
        async with client:
           result = await client.call_tool(tool, args)
           return result
    call_tool(tool, args)


# def alphabetize_string(text: str) -> str:
#     '''Alphabetize a string'''
#     async def call_tool(text: str):
#         async with client:
#             result = await client.call_tool("alphabetize_string_inner", {"s": text})
#             return result
#     call_tool(text)

@mcp.tool
def alphabetize_string(s: str) -> str:
    return "".join(sorted(s))




if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
