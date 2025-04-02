# Pydantic AI Chat Agent

A simple command-line chat interface powered by Anthropic's Claude 3.5 Sonnet using the pydantic_ai library.

## Setup

1. Install dependencies:
   ```
   pip install pydantic_ai python-dotenv
   ```

2. Get an API key from Anthropic:
   - Sign up or log in at [Anthropic's website](https://www.anthropic.com/)
   - Navigate to the API section to get your API key

3. Create a `.env` file in the project directory:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```
   Replace `your_api_key_here` with your actual Anthropic API key.

## Usage

Run the chat application:
```
python agent.py
```

- The application starts a conversation with "hello!"
- Claude's response will be displayed
- You can then enter your messages to continue the conversation
- The conversation history is maintained throughout the session

## Requirements

- Python 3.7+
- pydantic_ai
- python-dotenv
- An Anthropic API key

## Features

- Maintains conversation history
- Pretty-printed markdown responses
- Error handling
- Uses Claude 3 Sonnet model (can be configured to use other models)
- Conversational memory limited to last 5 messages for context 

## Shopify MCP UI

A simple UI application to display Shopify customer data using MCP (Multi-Component Protocol) without AI agents.

### Setup

1. Make sure your `.env` file includes the following Shopify credentials:
   ```
   SHOPIFY_STORE_URL=your_store_url
   SHOPIFY_ACCESS_TOKEN=your_access_token
   SHOPIFY_API_VERSION=your_api_version
   ```

2. Install additional dependencies:
   ```
   npm install -g shopify-mcp-server
   ```

### Usage

Run the Shopify customer UI application:
```
python mcp-ui.py
```

- The application displays a table of Shopify customers
- You can refresh the data using the "Refresh Data" button
- The UI shows customer ID, name, email, order count, and total spent

### Shopify MCP CLI Alternative

If you encounter issues with tkinter or prefer a command-line interface, use the CLI version instead:

```
python mcp-cli.py
```

The CLI version offers these features:
- Display Shopify customers in a table format
- Pagination support to view more customers
- List available MCP tools
- View shop details

### How It Works

1. The application uses the Shopify MCP server to fetch customer data
2. It can display the data in either a Tkinter UI or a CLI using Rich
3. No AI agents are involved - this is a direct MCP implementation

This demonstrates how MCP can be used to build applications that leverage external APIs without requiring an AI agent as an intermediary. 
