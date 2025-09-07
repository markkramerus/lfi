from fastmcp import FastMCP

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

if __name__ == "__main__":
    mcp.run(transport="http", port=8000)

