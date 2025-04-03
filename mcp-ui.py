import asyncio
import json
import os
import sys
import dotenv
import logfire
import time
from pydantic_ai.mcp import MCPServerStdio
from flask import Flask, render_template, jsonify, redirect, url_for, Response
import threading
import webbrowser

# Configure logging
logfire.configure()
print("Starting Shopify MCP Web UI...")

# Load environment variables from .env file if it exists
dotenv.load_dotenv()
print("Environment variables loaded")

# Check for required environment variables
required_env_vars = [
    "SHOPIFY_STORE_URL",
    "SHOPIFY_ACCESS_TOKEN",
    "SHOPIFY_API_VERSION"
]

missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    print(f"ERROR: {error_msg}")
    raise ValueError(error_msg)

# Extract domain from store URL for MYSHOPIFY_DOMAIN
store_url = os.environ.get("SHOPIFY_STORE_URL")
myshopify_domain = store_url.replace("https://", "").replace("http://", "")
if not myshopify_domain.endswith("myshopify.com"):
    myshopify_domain = f"{myshopify_domain}.myshopify.com"

print(f"Shopify Domain: {myshopify_domain}")
print(f"Shopify API Version: {os.environ.get('SHOPIFY_API_VERSION')}")

# Initialize the Shopify MCP server
print("Initializing MCP server...")
shopify_server = MCPServerStdio('npx', ["-y", "shopify-mcp-server"], env={
    "SHOPIFY_ACCESS_TOKEN": os.environ.get("SHOPIFY_ACCESS_TOKEN"),
    "MYSHOPIFY_DOMAIN": myshopify_domain,
    "SHOPIFY_API_VERSION": os.environ.get("SHOPIFY_API_VERSION")
})
print("MCP server initialized")

# Create Flask app
app = Flask(__name__)

# Store for customer data
customers_data = []
next_cursor = None
loading = False
error_message = None
last_response = None

# Create templates directory if it doesn't exist
templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
os.makedirs(templates_dir, exist_ok=True)
print(f"Templates directory created at {templates_dir}")

# Create the HTML template file
with open(os.path.join(templates_dir, 'index.html'), 'w') as f:
    f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shopify Customer Data</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .loading { display: none; }
        .spinner-border { width: 1rem; height: 1rem; }
        pre.debug { background: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 300px; overflow: auto; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">Shopify Customer Data</h1>
        
        <div class="row mb-4">
            <div class="col">
                <button id="refreshBtn" class="btn btn-primary">
                    <span class="spinner-border spinner-border-sm loading" role="status" aria-hidden="true"></span>
                    Refresh Data
                </button>
                <button id="loadMoreBtn" class="btn btn-secondary ms-2" style="display: none;">
                    <span class="spinner-border spinner-border-sm loading" role="status" aria-hidden="true"></span>
                    Load More
                </button>
                <button id="testConnBtn" class="btn btn-outline-info ms-2">
                    Test Connection
                </button>
            </div>
        </div>
        
        <div id="error-container" class="alert alert-danger" style="display: none;"></div>
        <div id="success-container" class="alert alert-success" style="display: none;"></div>
        
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Email</th>
                        <th>First Name</th>
                        <th>Last Name</th>
                        <th>Phone</th>
                        <th>Orders Count</th>
                        <th>Tags</th>
                    </tr>
                </thead>
                <tbody id="customerTableBody">
                    <!-- Customer data will be inserted here -->
                </tbody>
            </table>
        </div>
        
        <div id="statusMessage" class="mt-3 text-muted"></div>
        
        <div class="mt-4">
            <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" 
                   data-bs-target="#debugSection" aria-expanded="false">
                Show Debug Info
            </button>
            <div class="collapse mt-2" id="debugSection">
                <div class="card card-body">
                    <h5>Debug Information</h5>
                    <pre id="debugInfo" class="debug">No debug information available yet.</pre>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const refreshBtn = document.getElementById('refreshBtn');
            const loadMoreBtn = document.getElementById('loadMoreBtn');
            const testConnBtn = document.getElementById('testConnBtn');
            const customerTableBody = document.getElementById('customerTableBody');
            const statusMessage = document.getElementById('statusMessage');
            const errorContainer = document.getElementById('error-container');
            const successContainer = document.getElementById('success-container');
            const debugInfo = document.getElementById('debugInfo');
            
            // Initial data load
            fetchCustomers();
            
            // Refresh button click handler
            refreshBtn.addEventListener('click', function() {
                fetchCustomers(true);
            });
            
            // Load more button click handler
            loadMoreBtn.addEventListener('click', function() {
                fetchCustomers(false);
            });
            
            // Test connection button
            testConnBtn.addEventListener('click', function() {
                testConnection();
            });
            
            function testConnection() {
                setLoading(true);
                errorContainer.style.display = 'none';
                successContainer.style.display = 'none';
                statusMessage.textContent = 'Testing connection to Shopify...';
                
                fetch('/api/test-connection')
                    .then(response => response.json())
                    .then(data => {
                        setLoading(false);
                        
                        if (data.error) {
                            showError(data.error);
                            updateDebugInfo(data.debug || 'No debug info available');
                            return;
                        }
                        
                        successContainer.textContent = 'Connection to Shopify successful!';
                        successContainer.style.display = 'block';
                        statusMessage.textContent = 'Connection test completed successfully.';
                        updateDebugInfo(data.debug || JSON.stringify(data, null, 2));
                    })
                    .catch(error => {
                        setLoading(false);
                        showError('Failed to test connection: ' + error.message);
                    });
            }
            
            function fetchCustomers(refresh = false) {
                setLoading(true);
                errorContainer.style.display = 'none';
                successContainer.style.display = 'none';
                
                const url = refresh ? '/api/customers' : '/api/customers/more';
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            showError(data.error);
                            updateDebugInfo(data.debug || 'No debug info available');
                            setLoading(false);
                            return;
                        }
                        
                        if (refresh) {
                            customerTableBody.innerHTML = '';
                        }
                        
                        // Update debug info
                        updateDebugInfo(data.debug || JSON.stringify(data, null, 2));
                        
                        if (data.loading) {
                            // Data is still loading, poll the status endpoint
                            pollStatus();
                        } else {
                            // Data is already available
                            renderCustomers(data.customers);
                            statusMessage.textContent = `Displaying ${customerTableBody.children.length} customers`;
                            loadMoreBtn.style.display = data.has_more ? 'inline-block' : 'none';
                            setLoading(false);
                        }
                    })
                    .catch(error => {
                        showError('Failed to fetch customers: ' + error.message);
                        setLoading(false);
                    });
            }
            
            function pollStatus() {
                statusMessage.textContent = 'Polling for results...';
                let pollCount = 0;
                const maxPolls = 10; // Maximum number of polls before giving up
                
                const pollInterval = setInterval(() => {
                    pollCount++;
                    statusMessage.textContent = `Polling for results (attempt ${pollCount})...`;
                    
                    if (pollCount > maxPolls) {
                        clearInterval(pollInterval);
                        showError('Data loading timeout. Please try again.');
                        setLoading(false);
                        return;
                    }
                    
                    fetch('/api/customers/status')
                        .then(response => response.json())
                        .then(data => {
                            updateDebugInfo(data.debug || JSON.stringify(data, null, 2));
                            
                            if (data.error) {
                                showError(data.error);
                                clearInterval(pollInterval);
                                setLoading(false);
                                return;
                            }
                            
                            if (!data.loading) {
                                // Loading complete, render the data
                                renderCustomers(data.customers);
                                statusMessage.textContent = `Displaying ${customerTableBody.children.length} customers`;
                                loadMoreBtn.style.display = data.has_more ? 'inline-block' : 'none';
                                clearInterval(pollInterval);
                                setLoading(false);
                            }
                        })
                        .catch(error => {
                            showError('Failed to check status: ' + error.message);
                            clearInterval(pollInterval);
                            setLoading(false);
                        });
                }, 2000); // Poll every 2 seconds
            }
            
            function renderCustomers(customers) {
                if (!customers || customers.length === 0) {
                    statusMessage.textContent = 'No customers found';
                    return;
                }
                
                customers.forEach(customer => {
                    const row = document.createElement('tr');
                    
                    row.innerHTML = `
                        <td>${customer.id || ''}</td>
                        <td>${customer.email || ''}</td>
                        <td>${customer.firstName || customer.first_name || ''}</td>
                        <td>${customer.lastName || customer.last_name || ''}</td>
                        <td>${customer.phone || ''}</td>
                        <td>${customer.ordersCount || customer.orders_count || 0}</td>
                        <td>${customer.tags || ''}</td>
                    `;
                    
                    customerTableBody.appendChild(row);
                });
                
                // Log sample data for debugging
                if (customers && customers.length > 0) {
                    console.log("Sample customer object:", customers[0]);
                }
            }
            
            function updateDebugInfo(info) {
                if (typeof info === 'object') {
                    debugInfo.textContent = JSON.stringify(info, null, 2);
                } else {
                    debugInfo.textContent = info;
                }
            }
            
            function setLoading(isLoading) {
                const loadingElements = document.querySelectorAll('.loading');
                
                if (isLoading) {
                    refreshBtn.disabled = true;
                    loadMoreBtn.disabled = true;
                    testConnBtn.disabled = true;
                    loadingElements.forEach(el => el.style.display = 'inline-block');
                } else {
                    refreshBtn.disabled = false;
                    loadMoreBtn.disabled = false;
                    testConnBtn.disabled = false;
                    loadingElements.forEach(el => el.style.display = 'none');
                }
            }
            
            function showError(message) {
                errorContainer.textContent = message;
                errorContainer.style.display = 'block';
                statusMessage.textContent = 'Error occurred. See details above.';
            }
        });
    </script>
</body>
</html>
''')
print("HTML template created")

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/test-connection')
def test_connection():
    """Test connection to Shopify via MCP"""
    global error_message, last_response
    
    # Start the test in a background thread
    thread = threading.Thread(target=lambda: asyncio.run(test_shopify_connection()))
    thread.daemon = True
    thread.start()
    
    # Wait for the test to complete
    time.sleep(3)
    
    # Return the results
    if error_message:
        return jsonify({
            "error": error_message,
            "debug": f"Last response: {last_response}"
        })
    
    return jsonify({
        "success": True,
        "message": "Connection to Shopify successful",
        "debug": f"Last response: {last_response}"
    })

async def test_shopify_connection():
    """Test the connection to Shopify"""
    global error_message, last_response
    
    error_message = None
    last_response = None
    
    try:
        print("Testing connection to Shopify...")
        
        async with shopify_server:
            # Call the get-shop-details tool as a simple test
            response = await shopify_server.call_tool("get-shop-details", {})
            
            # Save the response for debugging
            if hasattr(response, 'content') and isinstance(response.content, list):
                json_text = ""
                for item in response.content:
                    if hasattr(item, 'text'):
                        json_text += item.text
                last_response = json_text
            else:
                last_response = str(response)
            
            print(f"Connection test result: {last_response}")
            
    except Exception as e:
        error_message = f"Connection test failed: {str(e)}"
        import traceback
        print(f"ERROR: {error_message}")
        print(traceback.format_exc())

@app.route('/api/customers')
def get_customers():
    """API endpoint to get customers (first page)"""
    global customers_data, next_cursor, loading, error_message
    
    if loading:
        return jsonify({
            "error": "A request is already in progress",
            "loading": True
        })
    
    # Reset the store
    customers_data = []
    next_cursor = None
    error_message = None
    
    # Start async fetch in background
    thread = threading.Thread(target=lambda: asyncio.run(fetch_customers()))
    thread.daemon = True
    thread.start()
    
    # Wait a bit to see if we get immediate results
    time.sleep(1.5)
    
    # Return current data
    debug_info = {
        "request_status": "in_progress" if loading else "completed",
        "customers_count": len(customers_data),
        "has_next_cursor": next_cursor is not None,
        "error": error_message
    }
    
    return jsonify({
        "customers": customers_data,
        "has_more": next_cursor is not None,
        "loading": loading,
        "error": error_message,
        "debug": debug_info
    })

@app.route('/api/direct-fetch')
def direct_fetch():
    """Direct synchronous API fetch for testing"""
    try:
        print("Starting direct fetch...")
        # Create event loop in this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the fetch function directly
        result = loop.run_until_complete(direct_fetch_customers())
        
        # Close the loop
        loop.close()
        
        if isinstance(result, dict) and result.get("error"):
            return jsonify({
                "error": result["error"],
                "debug": result.get("debug", {})
            })
        
        # Return success response
        return jsonify({
            "success": True, 
            "customers": result,
            "count": len(result),
            "debug": {"raw_response": str(result)[:200] + "..."}
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Direct fetch error: {str(e)}")
        print(error_trace)
        
        return jsonify({
            "error": f"Direct fetch failed: {str(e)}",
            "debug": {"traceback": error_trace}
        })

async def direct_fetch_customers():
    """Direct fetch of customer data for testing"""
    try:
        print("Executing direct fetch customer function...")
        
        params = {"limit": 10}
        
        async with shopify_server:
            print("MCP server opened, calling get-customers tool...")
            # Call the get-customers tool
            response = await shopify_server.call_tool(
                "get-customers", params
            )
            
            print(f"Got response: {type(response)}")
            
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
                    print(f"Successfully parsed JSON, found {len(customers)} customers")
                    return customers
                except (json.JSONDecodeError, TypeError) as e:
                    error_message = f"Error parsing JSON: {str(e)}"
                    print(f"ERROR: {error_message}")
                    print(f"JSON text: {json_text[:200]}...")
                    return {"error": error_message, "debug": {"json_snippet": json_text[:200]}}
            else:
                error_message = "Invalid response format from MCP"
                print(f"ERROR: {error_message}")
                return {"error": error_message, "debug": {"response_type": str(type(response))}}
        
    except Exception as e:
        error_message = f"Error in direct fetch: {str(e)}"
        print(f"ERROR: {error_message}")
        import traceback
        trace = traceback.format_exc()
        print(trace)
        return {"error": error_message, "debug": {"traceback": trace}}

@app.route('/api/customers/more')
def get_more_customers():
    """API endpoint to get more customers (pagination)"""
    global customers_data, next_cursor, loading, error_message
    
    if loading:
        return jsonify({"error": "A request is already in progress"})
    
    if not next_cursor:
        return jsonify({"error": "No more customers to load"})
    
    # Store current customers
    current_count = len(customers_data)
    
    # Start async fetch in background
    thread = threading.Thread(target=lambda: asyncio.run(fetch_customers(next_cursor)))
    thread.daemon = True
    thread.start()
    
    # Wait a bit to see if we get immediate results
    time.sleep(1.5)
    
    # Get new customers only
    new_customers = customers_data[current_count:] if len(customers_data) > current_count else []
    
    # Debug info
    debug_info = {
        "request_status": "in_progress" if loading else "completed",
        "total_customers": len(customers_data),
        "new_customers": len(new_customers),
        "has_next_cursor": next_cursor is not None,
        "error": error_message
    }
    
    # Return current data
    return jsonify({
        "customers": new_customers,
        "has_more": next_cursor is not None,
        "loading": loading,
        "error": error_message,
        "debug": debug_info
    })

@app.route('/api/customers/status')
def get_customers_status():
    """API endpoint to check the status of customer data loading"""
    global customers_data, next_cursor, loading, error_message, last_response
    
    debug_info = {
        "request_status": "in_progress" if loading else "completed",
        "customers_count": len(customers_data),
        "has_next_cursor": next_cursor is not None,
        "error": error_message,
        "last_response": str(last_response)[:200] + "..." if last_response else None
    }
    
    return jsonify({
        "customers": customers_data,
        "has_more": next_cursor is not None,
        "loading": loading,
        "error": error_message,
        "debug": debug_info
    })

async def fetch_customers(cursor=None):
    """Fetch customers data from Shopify via MCP"""
    global customers_data, next_cursor, loading, error_message, last_response
    
    loading = True
    error_message = None
    
    try:
        print(f"Fetching customer data from Shopify{' with cursor' if cursor else ''}")
        
        params = {"limit": 50}
        if cursor:
            params["next"] = cursor
            
        print(f"Opening MCP server connection for customer fetch...")
        async with shopify_server:
            print("MCP server opened, calling get-customers tool...")
            # Call the get-customers tool
            response = await shopify_server.call_tool(
                "get-customers", params
            )
            
            print(f"Got response of type: {type(response)}")
            last_response = response
            
            # Extract data from text content
            if hasattr(response, 'content') and isinstance(response.content, list):
                # Extract text from the text content objects
                json_text = ""
                for item in response.content:
                    if hasattr(item, 'text'):
                        json_text += item.text
                
                # Parse the JSON text
                try:
                    print(f"Parsing JSON response, length: {len(json_text)}")
                    data = json.loads(json_text)
                    new_customers = data.get("customers", [])
                    print(f"Received {len(new_customers)} customers from Shopify")
                    
                    # Print the first customer for debugging
                    if new_customers and len(new_customers) > 0:
                        print(f"Sample customer data: {json.dumps(new_customers[0], indent=2)[:500]}...")
                    
                    # Normalize the data to ensure consistent field names
                    normalized_customers = []
                    for customer in new_customers:
                        # Create a copy with standardized field names
                        normalized_customer = {
                            "id": customer.get("id", ""),
                            "email": customer.get("email", ""),
                            "first_name": customer.get("first_name", ""),
                            "last_name": customer.get("last_name", ""),
                            "phone": customer.get("phone", ""),
                            "orders_count": customer.get("orders_count", 0),
                            "tags": customer.get("tags", "")
                        }
                        normalized_customers.append(normalized_customer)
                    
                    if cursor and customers_data:
                        customers_data.extend(normalized_customers)
                    else:
                        customers_data = normalized_customers
                        
                    next_cursor = data.get("next")
                    if next_cursor:
                        print(f"Next cursor available: {next_cursor[:20]}...")
                    
                except (json.JSONDecodeError, TypeError) as e:
                    error_message = f"Error parsing JSON: {str(e)}"
                    print(f"ERROR: {error_message}")
                    print(f"JSON text: {json_text[:200]}...")
            else:
                error_message = "Invalid response format from MCP"
                print(f"ERROR: {error_message}")
                print(f"Response: {response}")
        
    except Exception as e:
        error_message = f"Error fetching customers: {str(e)}"
        print(f"ERROR: {error_message}")
        import traceback
        trace = traceback.format_exc()
        print(trace)
    finally:
        loading = False
        print(f"Fetch complete. Found {len(customers_data)} customers.")

def open_browser():
    """Open web browser after a delay"""
    try:
        webbrowser.open('http://127.0.0.1:5000')
        print("Browser opened to http://127.0.0.1:5000")
    except Exception as e:
        print(f"Failed to open browser: {str(e)}")

if __name__ == "__main__":
    # Print some debug info
    print(f"Using Shopify domain: {myshopify_domain}")
    print(f"Using Shopify API version: {os.environ.get('SHOPIFY_API_VERSION')}")
    
    # Open browser in a separate thread
    threading.Timer(1.5, open_browser).start()
    
    # Run the Flask app
    print("Starting Flask app...")
    app.run(debug=True) 