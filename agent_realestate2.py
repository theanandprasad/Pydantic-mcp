from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
import os
import dotenv
import logfire
import json
import sys
import time
import random
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Initialize LogFire
logfire.configure()

# Check if API key is available in environment variables
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

print(f"Using API key: {api_key[:8]}...")

# Set up the MCP servers
fetch_server = MCPServerStdio('python', ["-m", "mcp_server_fetch"])

# Configure Playwright MCP server in headless mode (no visible browser window)
playwright_server = MCPServerStdio(
    'npx', 
    ["@playwright/mcp@latest", "--headless"],  # Just use headless flag, we'll handle permissions with JavaScript
    env={
        "PLAYWRIGHT_BROWSERS_PATH": os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "0"),
        "PLAYWRIGHT_HEADLESS": "true"
    }
)

# Configure Anthropic Claude Research MCP server
claude_research_server = MCPServerStdio(
    'npx',
    ["-y", "supergateway", "--sse", "https://mcp.pipedream.net/8e0f55fb-1f70-40af-a952-14614f7e3342/anthropic"]
)

# Initialize the agent with the MCP servers and system prompt
SYSTEM_PROMPT = """
You are a real estate assistant that can browse property websites to find listings matching user criteria and perform in-depth research about real estate markets.

You have access to the following real estate websites:
- magicbricks.com
- 99acres.com
- housing.com
- nobroker.com

When a user asks about properties:
1. Determine their requirements (location, property type, budget, etc.)
2. Choose which website(s) to search based on their query
3. Use the browser_navigate tool to go to the appropriate website
4. Use browser_snapshot to analyze the page
5. Interact with search fields, filters, and listings using browser_click, browser_type, etc.
6. Collect information about matching properties and present it to the user

For each property, try to provide:
- Price
- Location
- Size/area
- Number of bedrooms
- Key amenities
- Link to the listing

When the user asks for research about real estate markets, trends, or advice:
1. Use the claude_research tool to gather up-to-date information
2. Provide well-researched, factual information about:
   - Market trends in specific neighborhoods or cities
   - Price comparisons between areas
   - Investment potential
   - Rental yield expectations
   - Regulatory considerations
   - Legal aspects of property transactions in India

When comparing properties, organize them clearly by price, location, or features as appropriate.
Combine your browsing capabilities and research tools to provide comprehensive assistance.
"""

agent = Agent(
    model='claude-3-5-sonnet-latest',
    api_key=api_key,
    instrument=True,
    mcp_servers=[fetch_server, playwright_server, claude_research_server],
    system_prompt=SYSTEM_PROMPT
)

# Real estate websites that the agent can navigate
REAL_ESTATE_WEBSITES = {
    "magicbricks": "https://www.magicbricks.com",
    "99acres": "https://www.99acres.com",
    "housing": "https://housing.com",
    "nobroker": "https://www.nobroker.in"
}

# Property search templates for different websites
# These can be expanded/modified based on the specific website layouts
SEARCH_TEMPLATES = {
    "magicbricks": {
        "buy": "/property-for-sale/{city}/",
        "rent": "/property-for-rent/{city}/"
    },
    "99acres": {
        "buy": "/search/property/buy/{city}-all/",
        "rent": "/search/property/rent/{city}-all/"
    },
    "housing": {
        "buy": "/in/{city}/buy-property-in-{city}",
        "rent": "/in/{city}/rent-property-in-{city}"
    },
    "nobroker": {
        "buy": "/{city}/buy/",
        "rent": "/{city}/rent/"
    }
}

# City name mappings (website-specific formats)
CITY_MAPPINGS = {
    "bangalore": {
        "magicbricks": "bangalore",
        "99acres": "bangalore",
        "housing": "bangalore",
        "nobroker": "bangalore"
    },
    "mumbai": {
        "magicbricks": "mumbai",
        "99acres": "mumbai",
        "housing": "mumbai",
        "nobroker": "mumbai"
    },
    "delhi": {
        "magicbricks": "delhi-ncr",
        "99acres": "delhi-ncr",
        "housing": "delhi-ncr",
        "nobroker": "delhi"
    },
    # Add more cities as needed
}

# Custom user agents to appear more like real browsers
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
]

# Set realistic geolocation coordinates for Indian cities
CITY_GEOLOCATION = {
    "bangalore": {"latitude": 12.9716, "longitude": 77.5946},
    "mumbai": {"latitude": 19.0760, "longitude": 72.8777},
    "delhi": {"latitude": 28.7041, "longitude": 77.1025},
    "hyderabad": {"latitude": 17.3850, "longitude": 78.4867},
    "chennai": {"latitude": 13.0827, "longitude": 80.2707},
    "pune": {"latitude": 18.5204, "longitude": 73.8567},
    "hsr": {"latitude": 12.9116, "longitude": 77.6521},  # HSR Layout in Bangalore
    "bellandur": {"latitude": 12.9282, "longitude": 77.6776}  # Bellandur in Bangalore
}

# More comprehensive JavaScript to handle browser permissions
BROWSER_PERMISSIONS_SCRIPT = """
// Hide Webdriver flag to prevent bot detection
Object.defineProperty(navigator, 'webdriver', { get: () => false });

// Set user agent
const userAgent = "%s";
Object.defineProperty(navigator, 'userAgent', { get: () => userAgent });

// Mock geolocation API
const mockGeolocation = {
  getCurrentPosition: (success) => {
    success({
      coords: {
        latitude: %s,
        longitude: %s,
        accuracy: 100,
        altitude: null,
        altitudeAccuracy: null,
        heading: null,
        speed: null
      },
      timestamp: Date.now()
    });
  },
  watchPosition: (success) => {
    success({
      coords: {
        latitude: %s,
        longitude: %s,
        accuracy: 100,
        altitude: null,
        altitudeAccuracy: null,
        heading: null,
        speed: null
      },
      timestamp: Date.now()
    });
    return 0;
  },
  clearWatch: () => {}
};

// Override the geolocation API
navigator.geolocation = mockGeolocation;

// Override permissions API to always return granted
if (navigator.permissions) {
  navigator.permissions.query = (parameters) => {
    return Promise.resolve({ state: 'granted', onchange: null });
  };
}

console.log("Browser permissions and identity configured successfully");
"""

# Simpler setup instructions that work with Playwright MCP
BROWSER_SETUP_INSTRUCTIONS = """
Please follow these steps to set up the headless browser:

1. First, use browser_install to install the necessary browser components
2. Navigate to about:blank using browser_navigate
3. Use browser_execute_javascript to run this script that sets up all permissions:

```javascript
%s
```

4. Test that the permissions are working by navigating to a simple website like example.com
5. Let me know when the browser is ready for searches
"""

# JavaScript to automatically handle cookie popups and other blocking elements
COOKIE_CONSENT_BYPASS_SCRIPT = """
function bypassCookieConsent() {
  // Common cookie consent button selectors
  const cookieSelectors = [
    // Common cookie accept buttons
    'button[id*="accept"], button[class*="accept"], button[id*="cookie"], button[class*="cookie"]',
    'a[id*="accept"], a[class*="accept"], a[id*="cookie"], a[class*="cookie"]',
    // Common popup close buttons
    'button[class*="close"], a[class*="close"], div[class*="close"]',
    // Specific selectors for common cookie banners
    '.cc-accept', '#cookieAccept', '.cookie-accept', '#cookie-banner button',
    // Common consent framework selectors
    '#onetrust-accept-btn-handler',
    '.js-accept-cookies',
    // Indian real estate sites specific selectors
    '.cookieNotification__Button', '.cookie-accept-btn',
    // General popup closing
    '.modal-close', '.popup-close'
  ];
  
  // Try all selectors
  for (const selector of cookieSelectors) {
    const elements = document.querySelectorAll(selector);
    for (const el of elements) {
      if (el.innerText && el.innerText.match(/accept|agree|allow|consent|okay|got it|i understand|yes/i)) {
        console.log('Clicking consent button:', el);
        el.click();
        return true;
      }
    }
  }
  
  // More aggressive approach - find buttons with relevant text
  const allButtons = document.querySelectorAll('button, a.button, input[type="button"], input[type="submit"]');
  for (const button of allButtons) {
    if (button.innerText && button.innerText.match(/accept|agree|allow|cookies|consent|okay|got it|i understand|yes/i)) {
      if (!button.innerText.match(/decline|reject|not now|dismiss/i)) {
        console.log('Found text-based consent button:', button);
        button.click();
        return true;
      }
    }
  }
  
  return false;
}

// Execute the bypass function
bypassCookieConsent();

// Also try to remove common overlay elements
const overlaySelectors = ['.overlay', '.modal', '.popup', '.cookie-banner', '.cookie-policy', '.consent-popup'];
for (const selector of overlaySelectors) {
  const elements = document.querySelectorAll(selector);
  for (const el of elements) {
    el.style.display = 'none';
  }
}

// Remove scroll blocking
document.body.style.overflow = 'auto';
document.documentElement.style.overflow = 'auto';
"""

# Define research topics and related keywords for Claude Research
RESEARCH_TOPICS = {
    "market_trends": ["real estate trends", "property price trends", "housing market", "market forecast", 
                     "property appreciation", "real estate bubble", "market crash", "market recovery"],
    "investment": ["real estate investment", "rental yield", "ROI", "property investment", 
                  "buy vs rent", "investment strategy", "property portfolio"],
    "locations": ["best areas to invest", "upcoming localities", "neighborhood analysis", 
                 "location factors", "gated communities", "proximity to amenities"],
    "legal": ["property laws india", "real estate regulations", "RERA", "property documents", 
             "title deed", "property tax", "stamp duty", "registration charges"],
    "loans": ["home loan", "mortgage", "interest rates", "loan eligibility", 
             "down payment", "loan tenure", "prepayment", "foreclosure"]
}

# Define a custom exception for rate limit errors
class RateLimitException(Exception):
    pass

# Define a custom retry function for the agent
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),  # Start with 4s, exponentially increase up to 60s
    stop=stop_after_attempt(5),  # Try up to 5 times
    retry=retry_if_exception_type(RateLimitException)
)
async def run_agent_with_retry(agent, message, message_history=None):
    try:
        return await agent.run(message, message_history=message_history)
    except Exception as e:
        error_str = str(e)
        if "rate_limit_error" in error_str or "status_code: 429" in error_str:
            logfire.warning(f"Rate limit hit. Retrying with backoff: {error_str}")
            # Add jitter to avoid synchronized retries in case of multiple instances
            time.sleep(random.uniform(0.1, 1.0))
            raise RateLimitException(error_str)
        else:
            # Re-raise other exceptions
            raise

async def visit_website_with_bypass(agent, url, city=None):
    """Visit a website and attempt to bypass cookie consent and other blocking elements."""
    try:
        print(f"Navigating to {url}...")
        
        # Navigate to the website
        navigate_result = await run_agent_with_retry(agent, f"Please navigate to {url}")
        
        # Wait a moment for the page to load
        time.sleep(2)
        
        # Execute the cookie consent bypass script
        cookie_bypass_prompt = f"""
        The page may have cookie consent popups or other blocking elements.
        Please execute this JavaScript to bypass them:
        
        ```javascript
        {COOKIE_CONSENT_BYPASS_SCRIPT}
        ```
        """
        
        cookie_bypass_result = await run_agent_with_retry(agent, cookie_bypass_prompt)
        
        # If a city is specified, try to set location
        if city and city in CITY_GEOLOCATION:
            location = CITY_GEOLOCATION[city]
            geo_script = f"""
            // Override geolocation for {city}
            const mockGeolocation = {{
              getCurrentPosition: (success) => {{
                success({{
                  coords: {{
                    latitude: {location['latitude']},
                    longitude: {location['longitude']},
                    accuracy: 100,
                    altitude: null,
                    altitudeAccuracy: null,
                    heading: null,
                    speed: null
                  }},
                  timestamp: Date.now()
                }});
              }},
              watchPosition: () => 0,
              clearWatch: () => {{}}
            }};
            navigator.geolocation = mockGeolocation;
            console.log("Geolocation set to {city}");
            """
            
            # Set geolocation
            geo_result = await run_agent_with_retry(
                agent,
                f"Please execute this JavaScript to set geolocation to {city}:\n```javascript\n{geo_script}\n```"
            )
        
        print(f"Successfully loaded {url} with bypass measures")
        
        # Wait for any search forms to load
        time.sleep(3)
        
        return True
    except Exception as e:
        print(f"Error visiting {url}: {str(e)}")
        return False

async def perform_market_research(agent, topic, location=None):
    """Use Claude Research to gather market intelligence about real estate."""
    try:
        print(f"Performing research on {topic} for {location if location else 'general market'}...")
        
        # Construct research query based on topic and location
        query = ""
        if topic == "market_trends":
            query = f"What are the current real estate trends in {location if location else 'India'}? Include price trends, demand-supply dynamics, and future outlook."
        elif topic == "investment":
            query = f"What are the best real estate investment opportunities in {location if location else 'India'} right now? Include ROI analysis and rental yield expectations."
        elif topic == "locations":
            if location:
                query = f"What are the best neighborhoods to invest in {location}? Which areas are up-and-coming vs established?"
            else:
                query = "What are the fastest growing real estate markets in India? Which cities offer the best investment potential?"
        elif topic == "legal":
            query = f"What are the important legal considerations for real estate transactions in {location if location else 'India'}? Include RERA regulations and documentation requirements."
        elif topic == "loans":
            query = "What are the current home loan interest rates offered by major banks in India? What are the eligibility criteria and documentation requirements?"
        else:
            # Default research query
            query = f"Provide the latest information about the real estate market in {location if location else 'India'}"
        
        # Use claude_research to get information
        research_prompt = f"""
        Please use claude_research to gather information on the following real estate query:
        
        Query: {query}
        
        Please search for recent and authoritative information on this topic. Format the results in a clear, 
        organized manner with headings and bullet points where appropriate.
        """
        
        research_result = await run_agent_with_retry(agent, research_prompt)
        
        print(f"Research on {topic} for {location if location else 'general market'} completed")
        
        return research_result
    except Exception as e:
        print(f"Error performing research: {str(e)}")
        return None

def detect_research_intent(user_input):
    """Detect if the user is asking for market research rather than property listings."""
    user_input_lower = user_input.lower()
    
    # Check for general research indicators
    research_indicators = ["research", "information", "data", "statistics", "report", 
                          "trends", "forecast", "outlook", "analysis", "insights"]
    
    if any(indicator in user_input_lower for indicator in research_indicators):
        # Try to determine which research topic
        for topic, keywords in RESEARCH_TOPICS.items():
            if any(keyword in user_input_lower for keyword in keywords):
                return topic
        
        # Default to market trends if research is indicated but no specific topic
        return "market_trends"
    
    # Not a research request
    return None

async def main():
    # Initial prompt that explains agent capabilities
    initial_prompt = """
    I'm a real estate browsing and research assistant. I can help you in two main ways:
    
    1. Find properties on websites like:
       - magicbricks.com
       - 99acres.com
       - housing.com
       - nobroker.com
    
    2. Provide in-depth research on real estate topics:
       - Market trends and price movements
       - Investment opportunities and rental yields
       - Location analysis and neighborhood comparisons
       - Legal considerations and RERA regulations
       - Home loan information and interest rates
    
    Tell me what you're looking for, whether it's specific properties (location, budget, type)
    or market research, and I'll help you find what you need.
    
    Type 'exit', 'quit', or 'bye' to end the session.
    """
    
    print("Starting Enhanced Real Estate Browser & Research Agent...")
    print("Initializing MCP servers...")
    
    async with agent.run_mcp_servers():
        print("MCP servers initialized")
        
        # First install the browser if needed
        try:
            print("Installing browser components in headless mode...")
            
            # Choose a random user agent and location
            user_agent = random.choice(USER_AGENTS)
            location = CITY_GEOLOCATION.get("bangalore")  # Default to Bangalore
            
            # Build the permission script with our variables
            permissions_script = BROWSER_PERMISSIONS_SCRIPT % (
                user_agent,
                location["latitude"],
                location["longitude"],
                location["latitude"],
                location["longitude"]
            )
            
            # Format setup instructions
            setup_instructions = BROWSER_SETUP_INSTRUCTIONS % permissions_script
            
            # Install and initialize the browser
            install_result = await run_agent_with_retry(agent, setup_instructions)
            
            logfire.info("Browser installation", result=install_result.output if hasattr(install_result, 'output') else install_result.data)
            print("Browser setup complete with custom user agent and location permissions")
            
            # Skip pre-initializing for now to avoid errors
            # We'll set permissions when needed for specific searches
            
        except Exception as e:
            error_msg = f"Browser installation failed: {str(e)}"
            logfire.error(error_msg)
            print(error_msg)
            print("Continuing anyway, but browsing might not work correctly.")
        
        # Now start the regular conversation
        print("\n" + "="*50)
        print("Enhanced Real Estate Property Search & Research Assistant")
        print("="*50 + "\n")
        
        result = await run_agent_with_retry(agent, initial_prompt)
        
        # Variables to track user intent
        last_location = None
        last_budget = None
        last_property_type = None  # "rent" or "buy"
        
        while True:
            # Log the agent's response
            logfire.info("Agent response", response=result.output if hasattr(result, 'output') else result.data)
            print(f"\n{result.output if hasattr(result, 'output') else result.data}")
            user_input = input("\nYou: ")
            # Exit condition
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\nThank you for using the real estate browsing and research assistant!")
                break
            
            # Log the user input
            logfire.info("User input", input=user_input)
            
            # Check if this is a research request
            research_topic = detect_research_intent(user_input)
            
            # Analyze user input for location and property intent
            user_input_lower = user_input.lower()
            
            # Check for locations in user query
            detected_location = None
            for location in CITY_GEOLOCATION.keys():
                if location in user_input_lower:
                    detected_location = location
                    last_location = location
                    break
            
            # Check for rent/buy intent
            if "rent" in user_input_lower or "rental" in user_input_lower:
                last_property_type = "rent"
            elif "buy" in user_input_lower or "purchase" in user_input_lower:
                last_property_type = "buy"
            
            # Look for budget indicators
            budget_indicators = ["budget", "afford", "cost", "price", "k", "lakh", "cr", "crore"]
            has_budget_indicator = any(indicator in user_input_lower for indicator in budget_indicators)
            
            # Handle research requests
            if research_topic:
                try:
                    print(f"Processing research request on {research_topic}...")
                    
                    # Perform research using Claude Research MCP
                    research_result = await perform_market_research(agent, research_topic, detected_location)
                    
                    if research_result:
                        # Let the agent integrate the research into a response
                        integration_prompt = f"""
                        I've gathered research on {research_topic} for {detected_location if detected_location else 'the Indian market'}.
                        
                        Please answer the user's question: "{user_input}"
                        
                        Based on the research data, provide a well-structured response with relevant information.
                        Include specific data points, trends, and actionable insights.
                        """
                        
                        result = await run_agent_with_retry(agent, integration_prompt, 
                                              message_history=result.new_messages())
                        continue
                        
                except Exception as e:
                    print(f"Error with research request: {str(e)}")
                    # Fall back to normal behavior
            
            # If we have both location and property type, try to use our special bypass method for browsing
            elif detected_location and last_property_type:
                try:
                    print(f"Searching for {last_property_type} properties in {detected_location}...")
                    
                    # Choose a site based on property type
                    if last_property_type == "rent":
                        # For rentals, nobroker is often good
                        site_name = "nobroker"
                        site_url = REAL_ESTATE_WEBSITES[site_name]
                        site_path = SEARCH_TEMPLATES[site_name]["rent"].format(city=detected_location)
                        full_url = f"{site_url}{site_path}"
                    else:
                        # For buying, try 99acres
                        site_name = "99acres"
                        site_url = REAL_ESTATE_WEBSITES[site_name]
                        site_path = SEARCH_TEMPLATES[site_name]["buy"].format(city=detected_location)
                        full_url = f"{site_url}{site_path}"
                    
                    # Use our helper to visit with bypass
                    await visit_website_with_bypass(agent, full_url, detected_location)
                    
                    # Let the agent continue with its normal flow but with added context
                    specific_prompt = f"""
                    I've helped you navigate to {full_url} with location permissions for {detected_location} 
                    and cookie consent bypassing. 
                    
                    Please answer the user's question: "{user_input}"
                    
                    Based on what you can see on the website, provide information about properties in {detected_location} 
                    that match their criteria. If you can't see specific properties, explain why and provide 
                    general information about that area.
                    """
                    
                    result = await run_agent_with_retry(agent, specific_prompt, 
                                            message_history=result.new_messages())
                    continue
                
                except Exception as e:
                    print(f"Error with special search: {str(e)}")
                    # Fall back to normal behavior
            
            # Normal flow - just process the user input
            try:
                result = await run_agent_with_retry(agent, user_input, 
                                        message_history=result.new_messages())
            except Exception as e:
                error_msg = f"Error during agent run: {str(e)}"
                logfire.error(error_msg)
                print(f"\nAn error occurred: {error_msg}")
                print("You can try again or type 'exit' to quit.")
                
                # Try to close browser gracefully on error
                try:
                    await run_agent_with_retry(agent, "Please close the browser using browser_close")
                except:
                    pass


if __name__ == "__main__":
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1) 