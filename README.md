# Real Estate Browsing Agent

This agent uses Pydantic AI and Microsoft's Playwright MCP to browse real estate websites and find properties that match user queries.

## Supported Websites

- magicbricks.com
- 99acres.com
- housing.com
- nobroker.com

## Features

- Search for properties to buy or rent
- Filter by location, price range, number of bedrooms, and other criteria
- Browse multiple real estate websites
- View property details including prices, features, and amenities
- Compare properties across different platforms

## Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher (for Playwright MCP)
- Anthropic API key for Claude

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/real-estate-agent.git
   cd real-estate-agent
   ```

2. Install required Python packages:
   ```
   pip install pydantic-ai logfire python-dotenv
   ```

3. Install the Playwright MCP package:
   ```
   npm install -g @playwright/mcp@latest
   ```

4. Create a `.env` file in the project root by copying the example:
   ```
   cp .env.example .env
   ```
   Then add your actual API keys to the `.env` file. Never commit your actual API keys to version control.

## Running the Agent

Run the agent using Python:

```
python agent_realestate.py
```

On first run, the agent will install necessary browser components. Follow the on-screen prompts to interact with the agent.

## Example Queries

Here are some example queries you can try:

- "Find 2BHK apartments for rent in Bangalore within 25,000 rupees per month"
- "Show me houses for sale in Mumbai with 3 bedrooms under 1.5 crores"
- "Look for rental properties in Delhi near metro stations"
- "Find newly constructed apartments in Pune with swimming pool"
- "Search for 1BHK flats in Hyderabad on nobroker.com"

## Troubleshooting

If you encounter any issues:

1. Make sure you have the latest versions of the dependencies
2. Check that your Anthropic API key is valid
3. Try running with the `--headless` flag if you're on a system without a display
4. Verify that you have proper internet connectivity to browse websites

## Architecture Notes

- The agent uses Playwright MCP for browser automation
- Pydantic AI provides the Agent framework with MCP support
- LogFire is used for logging all interactions
- Property search templates are configured for each website

## License

[MIT License](LICENSE)

## Gmail Management Agent

The `agent_gmail.py` script provides an AI assistant that can help manage your Gmail inbox using natural language commands.

### Features

- Send emails with subject, content, and recipients (including CC and BCC)
- Create draft emails without sending
- Read specific emails by ID
- Search emails using Gmail's search syntax
- List emails from inbox, sent, or custom labels
- Mark emails as read/unread
- Move emails to different labels/folders
- Delete emails
- Batch process multiple emails at once
- List all available Gmail labels
- Create, rename, and delete labels

### Setup

1. Ensure you have the required dependencies:
```
pip install -r requirements.txt
```

2. Create an OAuth client ID in Google Cloud Platform:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API
   - Create OAuth 2.0 credentials (Web or Desktop application)
   - Download the credentials as JSON

3. Place your credentials file (named `gcp-oauth.keys.json`) in either:
   - Your current working directory, or
   - `~/.gmail-mcp/` directory

4. Set your Anthropic API key in the `.env` file:
```
ANTHROPIC_API_KEY=your_api_key_here
```

### Usage

Run the Gmail agent:

```
python agent_gmail.py
```

The first time you run the agent, it will guide you through the OAuth authentication process to connect to your Gmail account.

After authentication, you can interact with your Gmail inbox using natural language commands like:
- "Show me my unread emails"
- "Search for emails from john@example.com with attachments"
- "Send an email to sarah@example.com with subject Meeting Tomorrow"
- "Create a new label called Projects"
- "Move emails from john@example.com to the Projects label"

Type 'exit', 'quit', or 'bye' to end the session.

## Shopify Management Agent

The `agent_shopify.py` script provides an AI assistant that can help manage your Shopify store using natural language commands.

### Features

- View and search customers in your Shopify store
- Get customer details and order history
- Create and manage products
- Check inventory levels
- View and process orders
- Manage collections and discounts
- Get store analytics and sales data

### Setup

1. Ensure you have the required dependencies:
```
pip install -r requirements.txt
```

2. Set up your Shopify credentials in the `.env` file:
```
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your_access_token
SHOPIFY_API_VERSION=2024-04
ANTHROPIC_API_KEY=your_anthropic_api_key
```

3. To get your Shopify Access Token:
   - Log in to your Shopify Admin
   - Go to Apps > Develop apps
   - Create a custom app with the necessary scopes
   - Generate an admin API access token

### Usage

Run the Shopify agent:

```
python agent_shopify.py
```

You can interact with your Shopify store using natural language commands like:
- "Show me a list of customers"
- "Search for customers who purchased in the last month"
- "Show me inventory for product X"
- "List all orders with status 'unfulfilled'"
- "Show me sales data for last week"

Type 'exit', 'quit', or 'bye' to end the session.

## Security Best Practices

When using this repository:

1. Never commit sensitive information like API keys or tokens to git
2. Use environment variables for all secrets as shown in `.env.example`
3. Regenerate any tokens or API keys if they are accidentally exposed
4. Make sure `.env` is in your `.gitignore` file (already set up)
5. For the Gmail agent, store OAuth credentials outside the repository
