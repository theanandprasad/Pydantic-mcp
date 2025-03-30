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
