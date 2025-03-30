from typing import List
import os
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from rich.console import Console
from rich.markdown import Markdown

class ChatMessage(BaseModel):
    """Represents a single message in the chat history."""
    role: str
    content: str

class ChatHistory(BaseModel):
    """Maintains the conversation history."""
    messages: List[ChatMessage] = []

class ChatResult(BaseModel):
    """The structured response from the agent."""
    response: str

# Initialize the console for pretty printing
console = Console()

def get_api_key() -> str:
    """Get API key from environment variable."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Please set it with your Anthropic API key."
        )
    return api_key

# Create the agent with a friendly personality
chat_agent = Agent(
    "anthropic:claude-3-sonnet",  # You can change this to any supported model
    result_type=ChatResult,
    system_prompt=(
        "You are a friendly and helpful AI assistant. "
        "Maintain a conversational tone while being informative and concise. "
        "If you don't know something, be honest about it."
    ),
    api_key=get_api_key()  # Add API key here
)

async def chat():
    """Main chat loop."""
    history = ChatHistory()
    console.print(Markdown("# Welcome to the Chat Agent!\n"))
    console.print("Type 'exit' to end the conversation.\n")

    while True:
        # Get user input
        user_input = input("You: ").strip()
        if user_input.lower() == 'exit':
            break

        # Add user message to history
        history.messages.append(ChatMessage(role="user", content=user_input))

        try:
            # Format conversation history
            conversation_context = "\n".join(
                f"{msg.role}: {msg.content}" 
                for msg in history.messages[-5:]
            )
            
            # Get response from agent
            prompt = f"{conversation_context}\nuser: {user_input}"
            result = await chat_agent.run(prompt)

            # Add assistant's response to history
            history.messages.append(
                ChatMessage(role="assistant", content=result.data.response)
            )

            # Display the response
            console.print("\n[bold blue]Assistant:[/bold blue]", style="bold")
            console.print(Markdown(result.data.response))
            console.print()

        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {str(e)}\n")

if __name__ == "__main__":
    import asyncio
    asyncio.run(chat()) 