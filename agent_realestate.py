from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
import os
import dotenv
import logfire
import json
import sys
import time
import random
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Initialize LogFire
logfire.configure()

# Check if API key is available in environment variables
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

# Set up the MCP servers
fetch_server = MCPServerStdio('python', ["-m", "mcp_server_fetch"])

# Configure Playwright MCP server with headed mode for better debugging
# Add additional arguments based on the Playwright MCP documentation
playwright_server = MCPServerStdio(
    'npx', 
    ["@playwright/mcp@latest"],  # Default mode for normal usage
    env={
        # Set any required environment variables for Playwright
        "PLAYWRIGHT_BROWSERS_PATH": os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "0"),
    }
)

# Initialize the agent with the MCP servers and system prompt
SYSTEM_PROMPT = """
You are a real estate assistant that can browse property websites to find listings matching user criteria.
You have access to the following real estate websites:
- magicbricks.com
- 99acres.com
- housing.com
- nobroker.com

When a user asks about properties:
1. Determine their requirements (location, property type, budget, etc.)
2. Choose which website(s) to search based on their query
3. Use the browser_navigate tool to go to the appropriate website
4. Use browser_snapshot to analyze the page
5. Interact with search fields, filters, and listings using browser_click, browser_type, etc.
6. Collect information about matching properties and present it to the user

For each property, try to provide:
- Price
- Location
- Size/area
- Number of bedrooms
- Key amenities
- Link to the listing

When comparing properties, organize them clearly by price, location, or features as appropriate.
"""

agent = Agent(
    'anthropic:claude-3-5-sonnet-latest',
    instrument=True,
    mcp_servers=[fetch_server, playwright_server],
    system_prompt=SYSTEM_PROMPT
)

# Real estate websites that the agent can navigate
REAL_ESTATE_WEBSITES = {
    "magicbricks": "https://www.magicbricks.com",
    "99acres": "https://www.99acres.com",
    "housing": "https://housing.com",
    "nobroker": "https://www.nobroker.in"
}

# Property search templates for different websites
# These can be expanded/modified based on the specific website layouts
SEARCH_TEMPLATES = {
    "magicbricks": {
        "buy": "/property-for-sale/{city}/",
        "rent": "/property-for-rent/{city}/"
    },
    "99acres": {
        "buy": "/search/property/buy/{city}-all/",
        "rent": "/search/property/rent/{city}-all/"
    },
    "housing": {
        "buy": "/in/{city}/buy-property-in-{city}",
        "rent": "/in/{city}/rent-property-in-{city}"
    },
    "nobroker": {
        "buy": "/{city}/buy/",
        "rent": "/{city}/rent/"
    }
}

# City name mappings (website-specific formats)
CITY_MAPPINGS = {
    "bangalore": {
        "magicbricks": "bangalore",
        "99acres": "bangalore",
        "housing": "bangalore",
        "nobroker": "bangalore"
    },
    "mumbai": {
        "magicbricks": "mumbai",
        "99acres": "mumbai",
        "housing": "mumbai",
        "nobroker": "mumbai"
    },
    "delhi": {
        "magicbricks": "delhi-ncr",
        "99acres": "delhi-ncr",
        "housing": "delhi-ncr",
        "nobroker": "delhi"
    },
    # Add more cities as needed
}

# Define a custom exception for rate limit errors
class RateLimitException(Exception):
    pass

# Define a custom retry function for the agent
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),  # Start with 4s, exponentially increase up to 60s
    stop=stop_after_attempt(5),  # Try up to 5 times
    retry=retry_if_exception_type(RateLimitException)
)
async def run_agent_with_retry(agent, message, message_history=None):
    try:
        return await agent.run(message, message_history=message_history)
    except Exception as e:
        error_str = str(e)
        if "rate_limit_error" in error_str or "status_code: 429" in error_str:
            logfire.warning(f"Rate limit hit. Retrying with backoff: {error_str}")
            # Add jitter to avoid synchronized retries in case of multiple instances
            time.sleep(random.uniform(0.1, 1.0))
            raise RateLimitException(error_str)
        else:
            # Re-raise other exceptions
            raise

async def main():
    # Initial prompt that explains agent capabilities
    initial_prompt = """
    I'm a real estate browsing assistant. I can help you find properties on websites like:
    - magicbricks.com
    - 99acres.com
    - housing.com
    - nobroker.com
    - https://www.reddit.com/r/indianrealestate/
    
    Tell me what kind of property you're looking for (buy/rent, location, budget, size, 
    number of bedrooms, etc.) and I'll browse these sites to find matching options.
    
    You can also specify which website you prefer, or I can search across multiple sites.
    
    Type 'exit', 'quit', or 'bye' to end the session.
    """
    
    print("Starting Real Estate Browser Agent...")
    print("Initializing MCP servers...")
    
    async with agent.run_mcp_servers():
        print("MCP servers initialized")
        
        # First install the browser if needed
        try:
            print("Installing browser components if needed...")
            install_result = await run_agent_with_retry(agent, """
            Please run the browser installation command to ensure Playwright is set up correctly.
            Use the browser_install function.
            """)
            logfire.info("Browser installation", result=install_result.data)
            print("Browser setup complete")
        except Exception as e:
            error_msg = f"Browser installation failed: {str(e)}"
            logfire.error(error_msg)
            print(error_msg)
            print("Continuing anyway, but browsing might not work correctly.")
        
        # Now start the regular conversation
        print("\n" + "="*50)
        print("Real Estate Property Search Assistant")
        print("="*50 + "\n")
        
        result = await run_agent_with_retry(agent, initial_prompt)
        while True:
            # Log the agent's response
            logfire.info("Agent response", response=result.data)
            print(f"\n{result.data}")
            user_input = input("\nYou: ")
            # Exit condition
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\nThank you for using the real estate browsing assistant!")
                break
            # Log the user input
            logfire.info("User input", input=user_input)
            # Run the agent with the user input
            try:
                result = await run_agent_with_retry(agent, user_input, 
                                        message_history=result.new_messages())
            except Exception as e:
                error_msg = f"Error during agent run: {str(e)}"
                logfire.error(error_msg)
                print(f"\nAn error occurred: {error_msg}")
                print("You can try again or type 'exit' to quit.")
                
                # Try to close browser gracefully on error
                try:
                    await run_agent_with_retry(agent, "Please close the browser using browser_close")
                except:
                    pass


if __name__ == "__main__":
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1) 