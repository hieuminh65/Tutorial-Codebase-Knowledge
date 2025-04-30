import requests
import json
import os
import sys
import argparse

from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test the output-content API endpoint')
    parser.add_argument('--repo', '-r', default="hieuminh65", help='Repository name')
    parser.add_argument('--path', '-p', default="index.md", help='File path inside the repository')
    parser.add_argument('--live', '-l', action='store_true', help='Use live deployed function instead of localhost')
    args = parser.parse_args()

    repo_name = args.repo
    file_path = args.path
    
    # Build the function URL
    base_url = "https://github-codebase-tutorial-generate.azurewebsites.net" if args.live else "http://localhost:7071"
    function_url = f"{base_url}/api/output-content/{repo_name}/{file_path}"
    
    print(f"Testing output-content endpoint for repository: {repo_name}")
    print(f"Accessing file: {file_path}")
    print(f"Full URL: {function_url}")

    # Send the request
    try:
        response = requests.get(function_url, timeout=60)
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {response.headers}")

        try:
            response_json = response.json()
            
            # Check if we got a successful response with content
            if response.status_code == 200 and 'content' in response_json:
                content = response_json['content']
                print("\n" + "="*50)
                print(f"CONTENT OF {file_path}:")
                print("="*50)
                print(content)
                print("="*50)
                
                # Option to save content to file
                save_content = input("\nSave content to a local file? (y/n): ").lower() == 'y'
                if save_content:
                    output_filename = f"{repo_name}_{file_path.replace('/', '_')}"
                    with open(output_filename, 'w') as f:
                        f.write(content)
                    print(f"Content saved to {output_filename}")
                
                # If we got the structure successfully, let the user pick another file
                get_structure = input("\nWould you like to get the structure to choose another file? (y/n): ").lower() == 'y'
                if get_structure:
                    structure_url = f"{base_url}/api/output-structure/{repo_name}"
                    structure_response = requests.get(structure_url, timeout=60)
                    
                    if structure_response.status_code == 200:
                        structure = structure_response.json()
                        chapters = structure.get('chapters', [])
                        
                        if chapters:
                            print("\nAvailable files:")
                            file_options = []
                            
                            for i, chapter in enumerate(chapters):
                                print(f"\nChapter {i+1}: {chapter['title']}")
                                for j, lesson in enumerate(chapter['lessons']):
                                    option_index = len(file_options)
                                    file_options.append(lesson['path'])
                                    print(f"  [{option_index}] {lesson['title']} ({lesson['path']})")
                            
                            file_index = input("\nEnter number of file to view (or q to quit): ")
                            if file_index.lower() not in ('q', 'quit') and file_index.isdigit():
                                file_index = int(file_index)
                                if 0 <= file_index < len(file_options):
                                    # Re-run the script with the new file path
                                    python = sys.executable
                                    os.execl(python, python, __file__, 
                                            "--repo", repo_name, 
                                            "--path", file_options[file_index],
                                            "--live" if args.live else "")
            else:
                # Print error or unexpected response
                print(f"Response body: {json.dumps(response_json, indent=2)}")
                
                if response.status_code == 404:
                    print("\nNote: If you see 'File not found' error, make sure:")
                    print("1. You've successfully generated a tutorial for this repository")
                    print("2. The repository name matches exactly what was used during generation")
                    print("3. The file path is correct (check the structure endpoint first)")
                    
                    # Offer to check structure
                    check_structure = input("\nWould you like to check the tutorial structure? (y/n): ").lower() == 'y'
                    if check_structure:
                        python = sys.executable
                        structure_script = os.path.join(os.path.dirname(__file__), "test_output_structure.py")
                        os.execl(python, python, structure_script, repo_name)
                    
        except json.JSONDecodeError:
            print(f"Response body (not JSON): {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    main()