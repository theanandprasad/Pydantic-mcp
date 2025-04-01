from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
import os
import dotenv
import logfire

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Initialize LogFire
logfire.configure()

# Check for required environment variables
required_env_vars = [
    "ANTHROPIC_API_KEY",
    "SHOPIFY_STORE_URL",
    "SHOPIFY_ACCESS_TOKEN",
    "SHOPIFY_API_VERSION"
]

missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Extract domain from store URL for MYSHOPIFY_DOMAIN
store_url = os.environ.get("SHOPIFY_STORE_URL")
myshopify_domain = store_url.replace("https://", "").replace("http://", "")
if not myshopify_domain.endswith("myshopify.com"):
    myshopify_domain = f"{myshopify_domain}.myshopify.com"

fetch_server = MCPServerStdio('python', ["-m", "mcp_server_fetch"])
shopify_server = MCPServerStdio('npx', ["-y", "shopify-mcp-server"], env={
    "SHOPIFY_ACCESS_TOKEN": os.environ.get("SHOPIFY_ACCESS_TOKEN"),
    "MYSHOPIFY_DOMAIN": os.environ.get("SHOPIFY_STORE_URL")
})

# The library will automatically use the API key from environment variables
agent = Agent('anthropic:claude-3-5-sonnet-latest',
instrument=True,
mcp_servers=[fetch_server, shopify_server],
)

async def main():
    async with agent.run_mcp_servers():
        result = await agent.run("hello!")
        while True:
            # Log the agent's response
            logfire.info("Agent response", response=result.data)
            print(f"\n{result.data}")
            user_input = input("\nYou: ")
            # Log the user input
            logfire.info("User input", input=user_input)
            result = await agent.run(user_input, 
                                    message_history=result.new_messages(),
                                    )
            


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())