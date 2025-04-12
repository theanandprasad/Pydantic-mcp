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

4. Create a `.env` file in the project root with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

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
