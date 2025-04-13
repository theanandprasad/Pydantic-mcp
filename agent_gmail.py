from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
import os
import dotenv
import logfire
import sys
import time
import random
import subprocess
import signal
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Initialize LogFire
logfire.configure()

# Check for required environment variables
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

# Define a custom exception for rate limit errors
class RateLimitException(Exception):
    pass

# Define a custom retry function for the agent
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(RateLimitException)
)
async def run_agent_with_retry(agent, message, message_history=None):
    try:
        return await agent.run(message, message_history=message_history)
    except Exception as e:
        error_str = str(e)
        if "rate_limit_error" in error_str or "status_code: 429" in error_str:
            logfire.warning(f"Rate limit hit. Retrying with backoff: {error_str}")
            # Add jitter to avoid synchronized retries
            time.sleep(random.uniform(0.1, 1.0))
            raise RateLimitException(error_str)
        else:
            # Re-raise other exceptions
            raise

def install_gmail_mcp():
    """Install the Gmail MCP server package."""
    print("\nInstalling Gmail MCP server...")
    try:
        # First check if it's already installed
        result = subprocess.run(["npm", "list", "-g", "@gongrzhe/server-gmail-autoauth-mcp"], 
                              capture_output=True, text=True)
        if "@gongrzhe/server-gmail-autoauth-mcp" in result.stdout:
            print("Gmail MCP server is already installed")
            return True
            
        # If not installed, install it
        subprocess.run(["npm", "install", "-g", "@gongrzhe/server-gmail-autoauth-mcp"], 
                      check=True, capture_output=True, text=True)
        print("Gmail MCP server installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing Gmail MCP server: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: npm not found. Please install Node.js and npm first.")
        return False

def start_gmail_server():
    """Start the Gmail MCP server explicitly."""
    try:
        # Kill any existing process on port 3000
        if sys.platform == 'win32':
            subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", "server-gmail-autoauth-mcp"], capture_output=True)
        
        # Start the server
        print("\nStarting Gmail MCP server...")
        server_process = subprocess.Popen(
            ["npx", "@gongrzhe/server-gmail-autoauth-mcp", "auth"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if process is still running
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print("Server failed to start:")
            print("stdout:", stdout)
            print("stderr:", stderr)
            return None
            
        return server_process
    except Exception as e:
        print(f"Error starting Gmail server: {e}")
        return None

def check_server_ready(url, timeout=30):
    """Check if the server is ready by attempting to connect."""
    import socket
    import urllib.parse
    
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or 3000
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (socket.timeout, socket.error):
            time.sleep(1)
    return False

# Set up the MCP servers
fetch_server = MCPServerStdio('python', ["-m", "mcp_server_fetch"])
gmail_server = MCPServerStdio('npx', ["@gongrzhe/server-gmail-autoauth-mcp"])

# System prompt for the Gmail agent
SYSTEM_PROMPT = """
You are a Gmail management assistant that can help users manage their inbox through natural language commands.

You can perform the following actions using Gmail's API:

1. SENDING EMAILS:
   - Send emails with subject, content, and recipients
   - Include CC and BCC recipients
   - Create draft emails without sending

2. READING EMAILS:
   - Read specific emails by ID
   - Search emails using Gmail's search syntax
   - List emails from inbox, sent, or custom labels

3. EMAIL MANAGEMENT:
   - Mark emails as read/unread
   - Move emails to different labels/folders
   - Delete emails
   - Batch process multiple emails at once

4. LABEL MANAGEMENT:
   - List all available Gmail labels
   - Create new labels
   - Rename or update existing labels
   - Delete labels

When helping users, always clarify their request if needed, and confirm important actions before performing them.
Provide clear summaries of results after completing actions.
"""

# Initialize the agent with MCP servers and system prompt
agent = Agent(
    'anthropic:claude-3-5-sonnet-latest',
    instrument=True,
    mcp_servers=[fetch_server, gmail_server],  # Added Gmail server back to the list
    system_prompt=SYSTEM_PROMPT
)

async def main():
    # Initial prompt that explains agent capabilities
    initial_prompt = """
    I'm your Gmail assistant. Here are all the available tools I can use to help manage your inbox:

    🔐 AUTHENTICATION
    - To disconnect the current Gmail account, type 'logout' or 'disconnect'
    - You'll need to authenticate again with a different account after disconnecting

    📧 EMAIL SENDING
    - send_email: Send new emails with subject, content, and attachments
      • Specify recipients (To, CC, BCC)
      • Add attachments
      • Support for international characters
    
    - draft_email: Create draft emails without sending
      • Save emails to draft folder
      • Edit later before sending

    📥 EMAIL READING
    - read_email: Read specific emails by ID
      • View full email content
      • See attachment information
      • Access email headers
    
    - search_emails: Search your inbox with Gmail's powerful syntax
      • from: (sender)
      • to: (recipient)
      • subject: (text in subject)
      • has:attachment
      • after:/before: (date)
      • is:unread/read
      • label: (label name)

    📂 EMAIL ORGANIZATION
    - modify_email: Organize individual emails
      • Archive emails (remove from inbox)
      • Move to different labels/folders
      • Mark as read/unread
      • Mark as important/not important
    
    - delete_email: Permanently delete individual emails
      • Remove emails completely
      • Cannot be undone

    🏷️ LABEL MANAGEMENT
    - list_email_labels: View all your Gmail labels
    - create_label: Create new labels
    - update_label: Rename or modify existing labels
    - delete_label: Remove unwanted labels
    - get_or_create_label: Get existing or create new label

    📋 BATCH OPERATIONS
    - batch_modify_emails: Process multiple emails at once
      • Archive multiple emails
      • Mark as read/unread
      • Add/remove labels
      • Move to different folders
    
    - batch_delete_emails: Delete multiple emails efficiently
      • Permanently delete multiple emails
      • Use with caution - cannot be undone

    What would you like help with? You can ask me to:
    • "Show my unread emails"
    • "Search for emails from john@example.com with attachments"
    • "Archive all emails older than 30 days"
    • "Create a new label called 'Projects'"
    • "Send an email to sarah@example.com about the meeting tomorrow"
    • "Move all emails from bob@example.com to the Archive folder"
    • "Delete all emails in the Spam folder"
    • "Archive newsletters older than 6 months"

    Type:
    • 'logout' or 'disconnect' to switch Gmail accounts
    • 'exit', 'quit', or 'bye' to end the session
    """
    
    print("Starting Gmail Assistant...")
    
    # First, ensure Gmail MCP server is installed
    if not install_gmail_mcp():
        print("Failed to install Gmail MCP server. Please try again.")
        return
    
    # Start the Gmail server explicitly
    server_process = start_gmail_server()
    if not server_process:
        print("Failed to start Gmail server. Please try again.")
        return
        
    print("Initializing MCP servers...")
    
    try:
        async with agent.run_mcp_servers():
            print("MCP servers initialized")
            print("\n" + "="*50)
            print("Gmail Management Assistant")
            print("="*50 + "\n")
            
            while True:  # Main authentication loop
                # Check for OAuth credentials
                credentials_path = os.path.expanduser("~/.gmail-mcp/gcp-oauth.keys.json")
                if not os.path.exists(credentials_path):
                    print("\nOAuth credentials not found. Please ensure you have:")
                    print("1. Created OAuth credentials in Google Cloud Console")
                    print("2. Downloaded the credentials as JSON")
                    print("3. Placed the file at:", credentials_path)
                    print("\nWould you like to proceed with authentication anyway? (y/n)")
                    if input().lower() != 'y':
                        return
                
                # Start with the OAuth authentication process
                try:
                    print("\nStarting Gmail authentication...")
                    print("The browser will open automatically for Google authentication.")
                    print("Please make sure your browser can access localhost:3000")
                    
                    # Wait for the server to be ready
                    auth_url = "http://localhost:3000"
                    print("\nWaiting for authentication server to start...")
                    if not check_server_ready(auth_url):
                        print("Error: Authentication server failed to start")
                        print("\nServer logs:")
                        stdout, stderr = server_process.communicate()
                        print("stdout:", stdout)
                        print("stderr:", stderr)
                        return
                    
                    auth_result = await run_agent_with_retry(agent, 
                        "Please run the authentication process to connect to Gmail.")
                    logfire.info("Gmail authentication initiated", result=auth_result.data)
                    print("\nAuthentication process started. Please complete the authentication in your browser.")
                    
                    # Get the authenticated email address
                    try:
                        email_result = await run_agent_with_retry(agent, 
                            "Please show me the currently authenticated Gmail address.")
                        logfire.info("Gmail address retrieved", result=email_result.data)
                        print("\n" + "="*50)
                        print("✓ Successfully authenticated!")
                        print(f"📧 Active Gmail account: {email_result.data.strip()}")
                        print("="*50 + "\n")
                    except Exception as e:
                        print("\nAuthenticated successfully, but couldn't retrieve email address.")
                        logfire.warning("Failed to retrieve Gmail address", error=str(e))

                    # Start the conversation loop
                    result = await run_agent_with_retry(agent, initial_prompt)
                    while True:
                        # Log the agent's response
                        logfire.info("Agent response", response=result.data)
                        print(f"\n{result.data}")
                        user_input = input("\nYou: ")
                        
                        # Handle special commands
                        if user_input.lower() in ["exit", "quit", "bye"]:
                            print("\nThank you for using the Gmail assistant!")
                            return
                        elif user_input.lower() in ["logout", "disconnect"]:
                            print("\nDisconnecting current Gmail account...")
                            # Remove the token file
                            token_path = os.path.expanduser("~/.gmail-mcp/token.json")
                            if os.path.exists(token_path):
                                os.remove(token_path)
                            print("Successfully disconnected. Please authenticate with a different account.")
                            # Restart the server to clear the session
                            server_process.terminate()
                            server_process = start_gmail_server()
                            if not server_process:
                                print("Failed to restart Gmail server. Please restart the application.")
                                return
                            break  # Break inner loop to return to authentication
                        
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
                
                except Exception as e:
                    error_msg = f"Authentication setup failed: {str(e)}"
                    logfire.error(error_msg)
                    print("\n" + "="*50)
                    print("Authentication Error")
                    print("="*50)
                    print(error_msg)
                    print("\nTroubleshooting steps:")
                    print("1. Make sure you have OAuth credentials in place")
                    print("2. Check that port 3000 is available")
                    print("3. Try manually visiting http://localhost:3000")
                    print("4. Ensure your browser can access localhost")
                    print("5. Make sure Node.js and npm are installed")
                    return
    finally:
        # Clean up the server process
        if server_process:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()

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