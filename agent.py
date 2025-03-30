from pydantic_ai import Agent
import os
import dotenv

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Check if API key is available in environment variables
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

# The library will automatically use the API key from environment variables
agent = Agent('anthropic:claude-3-5-sonnet-latest')

async def main():
    result = await agent.run("hello!")
    while True:
        print(f"\n{result.data}")
        user_input = input("\nYou: ")
        result = await agent.run(user_input, 
                                 message_history=result.new_messages(),
                                 )
        


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())