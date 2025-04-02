import asyncio
import json
import os
import dotenv
import logfire
from pydantic_ai.mcp import MCPServerStdio
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Initialize LogFire
logfire.configure()

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
    "MYSHOPIFY_DOMAIN": myshopify_domain
})

class ShopifyCustomerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Shopify Customers")
        self.root.geometry("1000x600")
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header
        header = ttk.Label(main_frame, text="Shopify Customers", font=("Helvetica", 16))
        header.pack(pady=(0, 10))
        
        # Create refresh button
        refresh_button = ttk.Button(main_frame, text="Refresh Data", command=self.refresh_data)
        refresh_button.pack(pady=(0, 10))
        
        # Create treeview for customers
        self.tree = ttk.Treeview(main_frame, columns=("id", "first_name", "last_name", "email", "orders_count", "total_spent"), show="headings")
        
        # Define column headings
        self.tree.heading("id", text="ID")
        self.tree.heading("first_name", text="First Name")
        self.tree.heading("last_name", text="Last Name")
        self.tree.heading("email", text="Email")
        self.tree.heading("orders_count", text="Orders Count")
        self.tree.heading("total_spent", text="Total Spent")
        
        # Define column widths
        self.tree.column("id", width=80)
        self.tree.column("first_name", width=150)
        self.tree.column("last_name", width=150)
        self.tree.column("email", width=250)
        self.tree.column("orders_count", width=100)
        self.tree.column("total_spent", width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        # Pack the treeview and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status label
        self.status_label = ttk.Label(root, text="Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=10, pady=5)
        
        # Store customer data
        self.customers = []
    
    def refresh_data(self):
        """Trigger async data refresh"""
        self.status_label.config(text="Fetching data...")
        self.root.after(100, self.start_async_fetch)
    
    def start_async_fetch(self):
        """Start the async data fetching process"""
        asyncio.run(self.fetch_customers())
    
    async def fetch_customers(self):
        """Fetch customers data from Shopify via MCP"""
        try:
            async with shopify_server:
                # Create a GraphQL query to fetch customers
                query = """
                {
                  customers(first: 50) {
                    edges {
                      node {
                        id
                        firstName
                        lastName
                        email
                        ordersCount
                        totalSpent
                      }
                    }
                  }
                }
                """
                
                # Call the Shopify GraphQL API via MCP
                response = await shopify_server.call(
                    method="graphql", params={"query": query}
                )
                
                # Process the response
                data = json.loads(response.result)
                
                # Extract customer data from the response
                customer_edges = data.get("data", {}).get("customers", {}).get("edges", [])
                self.customers = [edge["node"] for edge in customer_edges]
                
                # Update the UI with the customer data
                self.root.after(0, self.update_ui_with_customers)
                
        except Exception as e:
            error_message = f"Error fetching customers: {str(e)}"
            logfire.error(error_message)
            self.root.after(0, lambda: self.status_label.config(text=error_message))
    
    def update_ui_with_customers(self):
        """Update the UI with the fetched customer data"""
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add new data
        for customer in self.customers:
            self.tree.insert(
                "", 
                tk.END, 
                values=(
                    customer.get("id", "").split("/")[-1],  # Extract the ID number
                    customer.get("firstName", ""),
                    customer.get("lastName", ""),
                    customer.get("email", ""),
                    customer.get("ordersCount", 0),
                    f"${float(customer.get('totalSpent', 0)):.2f}"
                )
            )
        
        # Update status
        self.status_label.config(text=f"Loaded {len(self.customers)} customers")

async def main():
    root = tk.Tk()
    app = ShopifyCustomerUI(root)
    
    # Load initial data
    await app.fetch_customers()
    
    # Start the Tkinter event loop
    while True:
        root.update()
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except tk.TclError:
        # Handle window closing
        pass 