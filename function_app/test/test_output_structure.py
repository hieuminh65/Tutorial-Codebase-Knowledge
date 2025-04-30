import requests
import json
import os
import sys

from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

# Local Azure Function URL for output-structure
repo_name = "Codex"  # Change this to match an existing repository you've generated
# function_url = f"http://localhost:7071/api/output-structure/{repo_name}"  # If testing locally
function_url = f"https://github-codebase-tutorial-generate.azurewebsites.net/api/output-structure/{repo_name}"  # If testing live deployed

print(f"Sending test request to Azure Function at: {function_url}")

# Send the request
try:
    response = requests.get(function_url, timeout=60)
    print(f"Status code: {response.status_code}")
    print(f"Response headers: {response.headers}")

    try:
        response_json = response.json()
        
        # Check if we got a successful response with chapters
        if response.status_code == 200 and 'chapters' in response_json:
            chapters = response_json['chapters']
            print(f"\nSuccessfully retrieved tutorial structure with {len(chapters)} chapters")
            
            # Print the tutorial structure in a readable format
            print("\nTutorial Structure:")
            for i, chapter in enumerate(chapters):
                print(f"Chapter {i+1}: {chapter['title']}")
                for j, lesson in enumerate(chapter['lessons']):
                    print(f"  - Lesson {j+1}: {lesson['title']} ({lesson['path']})")
            
            # Option to save full response
            save_full_response = input("\nSave full structure to tutorial_structure.json? (y/n): ").lower() == 'y'
            if save_full_response:
                with open('tutorial_structure.json', 'w') as f:
                    json.dump(response_json, f, indent=2)
                print("Saved full structure to tutorial_structure.json")
        else:
            # Print error or unexpected response
            print(f"Response body: {json.dumps(response_json, indent=2)}")
            
            if response.status_code == 404 and 'error' in response_json:
                print("\nNote: If you see 'Output not found' error, make sure:")
                print("1. You've successfully generated a tutorial for this repository")
                print("2. The repository name matches exactly what was used during generation")
                print("3. The tutorial generation process has completed successfully")
                
                # Offer to test with a different repo name
                try_another = input("\nWould you like to try with a different repository name? (y/n): ").lower() == 'y'
                if try_another:
                    new_repo = input("Enter repository name: ")
                    if new_repo:
                        # Restart the script with the new repo name
                        python = sys.executable
                        os.execl(python, python, __file__, new_repo)
                
    except json.JSONDecodeError:
        print(f"Response body (not JSON): {response.text}")

except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")

# Allow command-line argument for repo name
if __name__ == "__main__" and len(sys.argv) > 1:
    repo_name = sys.argv[1]
    function_url = f"http://localhost:7071/api/output-structure/{repo_name}"
    print(f"Using command-line provided repo name: {repo_name}")
    # Re-run the request with the new repo name
    try:
        response = requests.get(function_url, timeout=60)
        # ... Same processing as above
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")