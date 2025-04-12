@echo off
SETLOCAL

:: Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is required but not found. Please install Python 3.
    exit /b 1
)

:: Check for Node.js
node --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Node.js is required but not found. Please install Node.js 18+.
    exit /b 1
)

:: Check for npx
npx --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo npx is required but not found. Please install npm/npx.
    exit /b 1
)

:: Check if .env file exists, create it if it doesn't
IF NOT EXIST .env (
    echo Creating .env file...
    echo ANTHROPIC_API_KEY= > .env
    echo Please edit the .env file to add your Anthropic API key.
    exit /b 1
)

:: Install Python dependencies if needed
echo Checking Python dependencies...
pip install -r requirements.txt

:: Install Playwright MCP if needed
echo Checking Playwright MCP installation...
call npm list -g @playwright/mcp >nul 2>&1 || call npm install -g @playwright/mcp@latest

:: Run the agent
echo Starting Real Estate Browsing Agent...
python agent_realestate.py

ENDLOCAL 