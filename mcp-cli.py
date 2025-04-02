import asyncio
import json
import os
import dotenv
import logfire
from pydantic_ai.mcp import MCPServerStdio
from rich.console import Console
from rich.table import Table
from rich import box

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Initialize LogFire
logfire.configure()

# Create Rich console for pretty output
console = Console()

# Check for required environment variables
required_env_vars = [
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

# Initialize the Shopify MCP server
shopify_server = MCPServerStdio('npx', ["-y", "shopify-mcp-server"], env={
    "SHOPIFY_ACCESS_TOKEN": os.environ.get("SHOPIFY_ACCESS_TOKEN"),
    "MYSHOPIFY_DOMAIN": myshopify_domain,
    "SHOPIFY_API_VERSION": os.environ.get("SHOPIFY_API_VERSION")
})

# Add debug info
console.print(f"[dim]Using Shopify domain: {myshopify_domain}[/dim]")
console.print(f"[dim]Using Shopify API version: {os.environ.get('SHOPIFY_API_VERSION')}[/dim]")

async def fetch_customers(next_cursor=None):
    """Fetch customers data from Shopify via MCP"""
    try:
        console.print("[bold blue]Fetching customer data from Shopify...[/bold blue]")
        
        params = {"limit": 50}
        if next_cursor:
            params["next"] = next_cursor
            
        async with shopify_server:
            # Call the get-customers tool
            response = await shopify_server.call_tool(
                "get-customers", params
            )
            
            # Extract data from text content
            if hasattr(response, 'content') and isinstance(response.content, list):
                # Extract text from the text content objects
                json_text = ""
                for item in response.content:
                    if hasattr(item, 'text'):
                        json_text += item.text
                
                # Parse the JSON text
                try:
                    data = json.loads(json_text)
                    customers = data.get("customers", [])
                    next_page_cursor = data.get("next")
                except (json.JSONDecodeError, TypeError) as e:
                    console.print(f"[bold red]Error parsing JSON: {str(e)}[/bold red]")
                    console.print(f"[dim]JSON text: {json_text}[/dim]")
                    customers = []
                    next_page_cursor = None
            else:
                customers = []
                next_page_cursor = None
            
            # Print some debug info about what we found
            console.print(f"[dim]Found {len(customers)} customers[/dim]")
            if next_page_cursor:
                console.print(f"[dim]Next page cursor: {next_page_cursor}[/dim]")
            
            return customers, next_page_cursor
            
    except Exception as e:
        error_message = f"Error fetching customers: {str(e)}"
        logfire.error(error_message)
        console.print(f"[bold red]{error_message}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return [], None

def display_customers(customers):
    """Display customers in a Rich table"""
    if not customers:
        console.print("[yellow]No customers found[/yellow]")
        return
        
    # Create a table
    table = Table(title="Shopify Customers", box=box.ROUNDED)
    
    # Add columns
    table.add_column("ID", style="cyan")
    table.add_column("Email", style="blue")
    table.add_column("Tags", style="green")
    
    # Add rows
    for customer in customers:
        customer_id = str(customer.get("id", ""))
        email = customer.get("email", "") or ""  # Handle None values
        tags = customer.get("tags", "")
        
        table.add_row(
            customer_id,
            email,
            tags
        )
    
    # Print the table
    console.print(table)
    console.print(f"[bold green]Loaded {len(customers)} customers[/bold green]")

async def display_menu():
    """Display the main menu and handle user input"""
    # Store pagination state
    next_cursor = None
    
    while True:
        console.print("\n[bold]Shopify MCP CLI[/bold]")
        console.print("1. Fetch and display customers")
        if next_cursor:
            console.print("2. Load more customers")
        console.print("3. List available MCP tools")
        console.print("4. View shop details")
        console.print("0. Exit")
        
        choice = input("\nEnter choice: ")
        
        if choice == "1":
            # Reset pagination and fetch first page
            customers, next_cursor = await fetch_customers()
            display_customers(customers)
        elif choice == "2" and next_cursor:
            # Fetch next page
            more_customers, next_cursor = await fetch_customers(next_cursor)
            display_customers(more_customers)
        elif choice == "3" or (choice == "2" and not next_cursor):
            await list_available_tools()
        elif choice == "4":
            await display_shop_details()
        elif choice == "0":
            console.print("[bold]Exiting...[/bold]")
            break
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")

async def list_available_tools():
    """List all available tools from the Shopify MCP server"""
    try:
        console.print("[bold blue]Listing available MCP tools...[/bold blue]")
        
        async with shopify_server:
            tools = await shopify_server.list_tools()
            
            console.print("[bold green]Available tools:[/bold green]")
            if tools:
                for tool in tools:
                    console.print(f"  [cyan]• {tool}[/cyan]")
            else:
                console.print("  [yellow]No tools available[/yellow]")
                
    except Exception as e:
        error_message = f"Error listing tools: {str(e)}"
        logfire.error(error_message)
        console.print(f"[bold red]{error_message}[/bold red]")

async def display_shop_details():
    """Display shop details to verify connection and see store data"""
    try:
        console.print("[bold blue]Fetching shop details...[/bold blue]")
        
        async with shopify_server:
            # Call the get-shop tool
            response = await shopify_server.call_tool("get-shop-details", {})
            
            # Access the content directly
            if hasattr(response, 'content'):
                if isinstance(response.content, dict):
                    data = response.content
                else:
                    try:
                        data = json.loads(response.content)
                    except (TypeError, json.JSONDecodeError):
                        data = {}
            else:
                data = {}
            
            # Pretty print the shop details
            console.print("[bold green]Shop Details:[/bold green]")
            console.print(data)
            
    except Exception as e:
        error_message = f"Error fetching shop details: {str(e)}"
        logfire.error(error_message)
        console.print(f"[bold red]{error_message}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")

async def main():
    console.print("[bold green]===============================================[/bold green]")
    console.print("[bold yellow]Welcome to the Shopify MCP Command Line Interface[/bold yellow]")
    console.print("[bold green]===============================================[/bold green]")
    
    await display_menu()

if __name__ == "__main__":
    asyncio.run(main()) 