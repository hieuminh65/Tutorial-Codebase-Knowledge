import requests
import json
import os

from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

# Local Azure Function URL for start-job
# function_url = "http://localhost:7071/api/start-job"  # If testing locally
function_url = "https://github-codebase-tutorial-generate.azurewebsites.net/api/start-job"  # If testing live deployed

# Test data - same as before
test_data = {
    'gemini_key': os.environ.get('GEMINI_API_KEY', None),
    'github_token': os.environ.get('GITHUB_TOKEN', None),  # Optional
    'repo_url': 'https://github.com/hieuminh65/hieuminh65',
    'include_patterns': '',
    'exclude_patterns': 'test/*,node_modules/*',
    'max_file_size': 1 * 1024 * 1024,  # 10 MB
}

print(f"Sending test request to Azure Function at: {function_url}")
print(f"Request data: {json.dumps(test_data, indent=2)}")

# Send the request
try:
    response = requests.post(function_url, json=test_data, timeout=60)  # No need 300s timeout for start-job
    print(f"Status code: {response.status_code}")
    print(f"Response headers: {response.headers}")

    try:
        print(f"Response body: {json.dumps(response.json(), indent=2)}")
    except json.JSONDecodeError:
        print(f"Response body (not JSON): {response.text}")

except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")
