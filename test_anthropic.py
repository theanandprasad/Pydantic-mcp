import os
import asyncio
import dotenv
import requests
import json

# Load environment variables
dotenv.load_dotenv()

# Get API key from environment
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

print(f"API key found: {api_key}")
print(f"API key length: {len(api_key)}")

def test_with_requests():
    print("\nTesting with direct HTTP request:")
    headers = {
        "x-api-key": api_key,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "Hello, how are you?"}]
    }
    
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=data
    )
    
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
    
    return response.status_code == 200

if __name__ == "__main__":
    test_with_requests() 