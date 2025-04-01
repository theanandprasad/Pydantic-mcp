from pydantic_ai import Agent
import os
import dotenv
import logfire

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Initialize LogFire
logfire.configure()

# Check if API key is available in environment variables
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

# The library will automatically use the API key from environment variables
agent = Agent('anthropic:claude-3-5-sonnet-latest')

async def main():
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