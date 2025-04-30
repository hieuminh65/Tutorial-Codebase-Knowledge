import requests
import json
import os

from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

# Local Azure Function URL for fetch-patterns
# function_url = "http://localhost:7071/api/fetch-patterns"  # If testing locally
function_url = "https://github-codebase-tutorial-generate.azurewebsites.net/api/fetch-patterns"  # If testing live deployed

# Test data
test_data = {
    'github_token': os.environ.get('GITHUB_TOKEN', None),  # Optional but recommended to avoid rate limits
    'repo_url': 'https://github.com/hieuminh65/go-micro',  # You can change this to any public repository
}

print(f"Sending test request to Azure Function at: {function_url}")
print(f"Request data: {json.dumps(test_data, indent=2)}")

# Send the request
try:
    response = requests.post(function_url, json=test_data, timeout=60)
    print(f"Status code: {response.status_code}")
    print(f"Response headers: {response.headers}")

    try:
        response_json = response.json()
        # Print a summary of the patterns if successful
        if response.status_code == 200 and 'patterns' in response_json:
            patterns = response_json['patterns']
            file_count = response_json.get('file_count', 0)
            print(f"\nSuccessfully retrieved {len(patterns)} pattern suggestions for {file_count} files")
            
            # Print first 5 patterns as a sample
            print("\nTop 5 patterns:")
            for i, pattern in enumerate(patterns[:5]):
                print(f"{i+1}. {pattern['label']} ({pattern['pattern']}) - {pattern.get('formatted_size', 'N/A')} ({pattern.get('count', 0)} files)")
            
            # Print full response if needed
            save_full_response = input("\nSave full pattern list to patterns.json? (y/n): ").lower() == 'y'
            if save_full_response:
                with open('patterns.json', 'w') as f:
                    json.dump(response_json, f, indent=2)
                print("Saved full pattern list to patterns.json")
        else:
            print(f"Response body: {json.dumps(response_json, indent=2)}")
    except json.JSONDecodeError:
        print(f"Response body (not JSON): {response.text}")

except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")