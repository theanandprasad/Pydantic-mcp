#!/bin/bash

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not found. Please install Python 3."
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "Node.js is required but not found. Please install Node.js 18+."
    exit 1
fi

# Check for Playwright MCP
if ! command -v npx &> /dev/null; then
    echo "npx is required but not found. Please install npm/npx."
    exit 1
fi

# Check if .env file exists, create it if it doesn't
if [ ! -f .env ]; then
    echo "Creating .env file..."
    echo "ANTHROPIC_API_KEY=" > .env
    echo "Please edit the .env file to add your Anthropic API key."
    exit 1
fi

# Check if ANTHROPIC_API_KEY is set in .env
if ! grep -q "ANTHROPIC_API_KEY=.*[^[:space:]]" .env; then
    echo "ANTHROPIC_API_KEY is not set in .env file."
    echo "Please edit the .env file to add your Anthropic API key."
    exit 1
fi

# Install Python dependencies if needed
echo "Checking Python dependencies..."
pip install -r requirements.txt

# Install Playwright MCP if needed
echo "Checking Playwright MCP installation..."
npm list -g @playwright/mcp || npm install -g @playwright/mcp@latest

# Run the agent
echo "Starting Real Estate Browsing Agent..."
python3 agent_realestate.py 