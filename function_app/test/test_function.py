import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Local Azure Function URL
# function_url = "http://localhost:7071/api/generate"
function_url = "https://github-codebase-tutorial-generate.azurewebsites.net/api/generate"

# Test data - replace with a real repository URL and API key
test_data = {
    'gemini_key': os.environ.get('GEMINI_API_KEY', None),
    'github_token': os.environ.get('GITHUB_TOKEN', None),  # Optional
    'repo_url': 'https://github.com/hieuminh65/api4all',  # A small repo for quick testing
    'include_patterns': '',  # Optional
    'exclude_patterns': 'test/*,node_modules/*',  # Optional
    'max_file_size': 50000  # Smaller size for faster testing
}

print(f"Sending test request to Azure Function at: {function_url}")
print(f"Request data: {json.dumps(test_data, indent=2)}")

# Send the request
try:
    response = requests.post(function_url, json=test_data, timeout=300)
    
    # Print response details
    print(f"Status code: {response.status_code}")
    print(f"Response headers: {response.headers}")
    
    # Parse and print JSON response if available
    try:
        print(f"Response body: {json.dumps(response.json(), indent=2)}")
    except json.JSONDecodeError:
        print(f"Response body (not JSON): {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")
