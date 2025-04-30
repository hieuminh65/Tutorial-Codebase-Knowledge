import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
import logging
import requests
import glob
import os
import sys
import json
import uuid

# Add the current directory to the path to help with imports
# current_dir = os.path.dirname(os.path.abspath(__file__))
# if current_dir not in sys.path:
#     sys.path.insert(0, current_dir)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Define the blob container name for outputs
OUTPUT_DIR = "tutorials"

@app.function_name(name="start_job")
@app.route(route="start-job", methods=["POST"])
def start_job(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON"}), 
            status_code=400,
            mimetype="application/json"
        )

    # Connect to the storage queue
    queue_connection_string = os.getenv('AzureWebJobsStorage')
    queue_client = QueueClient.from_connection_string(queue_connection_string, queue_name="jobsqueue")

    # Push message into the queue
    job_message = json.dumps(req_body)
    queue_client.send_message(job_message)

    logging.info(f"Message sent to queue: {job_message}")

    return func.HttpResponse(
        json.dumps({"message": "Job accepted."}), 
        status_code=202,
        mimetype="application/json"
    )

# Helper function
def get_repo_name_from_url(url):
    """Extracts a likely repo name from a GitHub URL."""
    try:
        if url.endswith('.git'):
            url = url[:-4]
        repo_name = url.split('/')[-1]
        # Basic sanitization to prevent directory issues
        repo_name = repo_name.replace('..', '').replace('/', '')
        return repo_name or "unknown_repo"
    except Exception:
        return "unknown_repo" # Fallback
    
def save_error_log(error_message: str):
    try:
        connection_string = os.environ.get("AzureWebJobsStorage")
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client("errors")
        try:
            container_client.create_container()
        except Exception:
            pass  # container already exists

        blob_name = f"log-{uuid.uuid4()}.txt"
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(error_message, overwrite=True)
        print(f"Saved error log to Blob: {blob_name}")
    except Exception as e:
        print(f"Failed to save error log: {e}")

@app.function_name(name="generate")
@app.queue_trigger(arg_name="msg", queue_name="jobsqueue", connection="AzureWebJobsStorage")
def generate(msg: func.QueueMessage) -> None:
    """Triggered by a message in the queue. This function will process the message."""
    try:
        req_body = json.loads(msg.get_body().decode('utf-8'))
    except Exception as e:
        error_message = f"Invalid JSON in queue message: {str(e)}"
        save_error_log(error_message)
        print(error_message)
        return

    try:
        from main import generate_tutorial_content
        logging.info("Successfully imported project modules")
    except Exception as e:
        error_message = f"Failed to import project modules: {str(e)}"
        save_error_log(error_message)
        print(error_message)
        return

    # Extract parameters
    gemini_key = req_body.get('gemini_key')
    github_token = req_body.get('github_token')
    repo_url = req_body.get('repo_url')
    include_patterns = req_body.get('include_patterns', '')
    exclude_patterns = req_body.get('exclude_patterns', '')
    max_file_size = req_body.get('max_file_size', 100000)

    if not gemini_key or not repo_url:
        error_message = "Missing required fields: gemini_key, repo_url."
        save_error_log(error_message)
        return

    # Get repo name
    repo_name = get_repo_name_from_url(repo_url)

    # Set environment variables
    os.environ['GEMINI_API_KEY'] = gemini_key
    if github_token:
        os.environ['GITHUB_TOKEN'] = github_token

    try:
        # Call your direct function
        result = generate_tutorial_content(
            repo_url=repo_url,
            repo_name=repo_name,
            include_patterns=include_patterns.split(',') if include_patterns else [],
            exclude_patterns=exclude_patterns.split(',') if exclude_patterns else [],
            max_file_size=max_file_size
        )

        if isinstance(result, dict) and "blob_storage_info" in result:
            logging.info(f"Generated and uploaded successfully: {result['blob_storage_info']}")

    except Exception as e:
        error_message = f"Error during generation: {str(e)}"
        save_error_log(error_message)
        return

@app.function_name(name="get_output_structure")
@app.route(route="output-structure/{repo_name}", methods=["GET"])
def get_output_structure(req: func.HttpRequest) -> func.HttpResponse:
    """Get the structure of the output directory for a given repository."""
    try:
        repo_name = req.route_params.get('repo_name')
        if not repo_name:
            req_body = req.get_json()
            repo_name = req_body.get('repo_name')
    except:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON or missing repo_name"}), 
            status_code=400,
            mimetype="application/json"
        )
    
    if not repo_name:
        return func.HttpResponse(
            json.dumps({"error": "Missing repo_name parameter"}), 
            status_code=400,
            mimetype="application/json"
        )
    
    safe_repo_name = get_repo_name_from_url(repo_name) # Sanitize just in case
    
    # Connect to blob storage instead of local filesystem
    connection_string = os.environ.get("AzureWebJobsStorage")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(OUTPUT_DIR)
    
    # Check if there are any blobs with the prefix of the repo name
    blobs = list(container_client.list_blobs(name_starts_with=f"{safe_repo_name}/"))
    if not blobs:
        return func.HttpResponse(
            json.dumps({"error": "Output not found for this repository"}), 
            status_code=404,
            mimetype="application/json"
        )

    structure = {"chapters": []}
    try:
        # Get all blobs with the repo prefix
        blobs_list = list(container_client.list_blobs(name_starts_with=f"{safe_repo_name}/"))
        
        # Extract chapter and lesson paths
        chapter_dirs = set()
        for blob in blobs_list:
            # Skip if not a markdown file
            if not blob.name.endswith('.md'):
                continue
                
            # Extract chapter from path
            path_parts = blob.name.split('/')
            if len(path_parts) > 2:  # repo_name/chapter_X/lesson.md
                chapter_name = path_parts[1]
                if chapter_name.startswith('chapter_'):
                    chapter_dirs.add(chapter_name)
        
        # Sort chapters numerically if possible
        chapter_dirs = sorted(
            list(chapter_dirs),
            key=lambda x: int(x.split('_')[-1]) if x.split('_')[-1].isdigit() else float('inf')
        )

        if not chapter_dirs:
            # Fallback: Look for index.md and other top-level md files
            lessons = []
            for blob in blobs_list:
                if not blob.name.endswith('.md'):
                    continue
                    
                # Only consider files directly under repo_name/
                path_parts = blob.name.split('/')
                if len(path_parts) != 2:  # Only repo_name/file.md
                    continue
                    
                lesson_basename = path_parts[1]
                if lesson_basename == 'index.md':
                    lessons.insert(0, {"title": "Overview", "path": "index.md"})
                else:
                    lesson_title = os.path.splitext(lesson_basename)[0].replace('_', ' ').title()
                    lessons.append({"title": lesson_title, "path": lesson_basename})

            if lessons:
                structure["chapters"].append({
                    "title": repo_name,  # Use repo name as title
                    "lessons": lessons
                })
            else:
                # No recognizable structure
                return func.HttpResponse(
                    json.dumps({"error": "Could not determine tutorial structure (no chapter_* dirs or *.md files found)"}), 
                    status_code=404,
                    mimetype="application/json"
                )
        else:
            for chapter_name in chapter_dirs:
                chapter_title = chapter_name.replace('_', ' ').title()  # e.g., "Chapter 1"
                
                lessons = []
                # Get all markdown files in this chapter
                chapter_lessons = [
                    blob for blob in blobs_list 
                    if blob.name.startswith(f"{safe_repo_name}/{chapter_name}/") and blob.name.endswith('.md')
                ]
                
                # Sort lessons by name
                chapter_lessons.sort(key=lambda x: x.name)
                
                for lesson_blob in chapter_lessons:
                    lesson_path = lesson_blob.name.split(f"{safe_repo_name}/")[1]  # Get relative path
                    lesson_basename = lesson_path.split('/')[-1]
                    lesson_title = os.path.splitext(lesson_basename)[0].replace('_', ' ').title()
                    lessons.append({"title": lesson_title, "path": lesson_path})
                
                if lessons:
                    structure["chapters"].append({"title": chapter_title, "lessons": lessons})

        # Handle case where chapter folders exist but contain no markdown files
        if not structure["chapters"]:
            return func.HttpResponse(
                json.dumps({"error": "Could not determine tutorial structure (found chapter_* dirs but no *.md files inside)"}), 
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(structure), 
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        error_message = f"Error scanning output structure: {str(e)}"
        logging.error(error_message)
        save_error_log(error_message)
        return func.HttpResponse(
            json.dumps({"error": "Failed to read tutorial structure"}), 
            status_code=500,
            mimetype="application/json"
        )

@app.function_name(name="get_output_content") 
@app.route(route="output-content/{repo_name}/{*file_path}", methods=["GET"])
def get_output_content(req: func.HttpRequest) -> func.HttpResponse:
    """Get the content of a specific markdown file from the tutorial."""
    repo_name = req.route_params.get('repo_name')
    file_path = req.route_params.get('file_path')
    
    if not repo_name or not file_path:
        return func.HttpResponse(
            json.dumps({"error": "Missing repo_name or file_path parameter"}), 
            status_code=400,
            mimetype="application/json"
        )
    
    safe_repo_name = get_repo_name_from_url(repo_name)  # Sanitize just in case
    
    # Connect to blob storage
    connection_string = os.environ.get("AzureWebJobsStorage")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(OUTPUT_DIR)
    
    # Construct the full blob path
    blob_path = f"{safe_repo_name}/{file_path}"
    
    try:
        # Get the blob
        blob_client = container_client.get_blob_client(blob_path)
        
        if not blob_client.exists():
            return func.HttpResponse(
                json.dumps({"error": "File not found"}), 
                status_code=404,
                mimetype="application/json"
            )
        
        # Download the blob content
        content = blob_client.download_blob().readall().decode('utf-8')
        
        return func.HttpResponse(
            json.dumps({"content": content}), 
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        error_message = f"Error reading file {blob_path}: {str(e)}"
        logging.error(error_message)
        save_error_log(error_message)
        return func.HttpResponse(
            json.dumps({"error": "Failed to read file content"}), 
            status_code=500,
            mimetype="application/json"
        )

@app.function_name(name="fetch_patterns")
@app.route(route="fetch-patterns", methods=["POST"])
def fetch_patterns(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        if not data:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON"}), 
                status_code=400,
                mimetype="application/json"
            )

        github_token = data.get('github_token')
        repo_url = data.get('repo_url')

        if not repo_url:
            return func.HttpResponse(
                json.dumps({"error": "Missing repository URL"}), 
                status_code=400,
                mimetype="application/json"
            )

        # Use the existing function to extract the repo name from URL
        repo_name = get_repo_name_from_url(repo_url)
        
        # Extract owner and repo from URL
        parts = repo_url.strip('/').split('/')
        if len(parts) < 2:
            return func.HttpResponse(
                json.dumps({"error": "Invalid repository URL format"}), 
                status_code=400,
                mimetype="application/json"
            )
            
        # Handle both https://github.com/owner/repo and git@github.com:owner/repo.git formats
        if 'github.com' in repo_url:
            if 'github.com/' in repo_url:
                owner_repo = repo_url.split('github.com/')[1].split('/')
            else:
                owner_repo = repo_url.split(':')[1].split('/')
                
            owner = owner_repo[0]
            repo = owner_repo[1].replace('.git', '')
        else:
            return func.HttpResponse(
                json.dumps({"error": "Only GitHub repositories are supported"}), 
                status_code=400,
                mimetype="application/json"
            )
            
        # GitHub API endpoint for listing repo contents
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
        
        headers = {}
        if github_token:
            headers['Authorization'] = f'token {github_token}'
            
        response = requests.get(api_url, headers=headers)
        
        # If main branch doesn't exist, try master
        if response.status_code == 404:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
            response = requests.get(api_url, headers=headers)
            
        if response.status_code != 200:
            return func.HttpResponse(
                json.dumps({
                    "error": f"GitHub API error: {response.status_code}",
                    "details": response.json().get('message', 'Unknown error')
                }),
                status_code=response.status_code,
                mimetype="application/json"
            )
            
        # Extract file paths and sizes from the response
        tree = response.json().get('tree', [])
        all_files = []
        
        # Extract both path and size from the tree
        for item in tree:
            if item['type'] == 'blob':
                all_files.append({
                    'path': item['path'],
                    'size': item.get('size', 0)  # GitHub API provides size in bytes
                })
        
        # Generate pattern suggestions with sizes
        patterns = generate_pattern_suggestions(all_files)
        
        return func.HttpResponse(
            json.dumps({
                "patterns": patterns,
                "file_count": len(all_files)
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except requests.exceptions.RequestException as e:
        return func.HttpResponse(
            json.dumps({"error": "Failed to connect to GitHub API", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

def generate_pattern_suggestions(file_entries):
    """
    Generate pattern suggestions based on file paths with size information.
    file_entries: List of dicts with 'path' and 'size' keys
    """
    extensions = {}  # {ext: {'count': 0, 'size': 0}}
    directories = {}  # {dir: {'count': 0, 'size': 0}}
    specific_files = {}  # {filename: {'count': 0, 'size': 0}}
    
    # Analyze file paths and sizes
    for entry in file_entries:
        path = entry['path']
        size = entry['size']
        
        # Check if this is a file in a directory
        if '/' in path:
            # Extract top-level directory
            top_dir = path.split('/')[0]
            
            if top_dir not in directories:
                directories[top_dir] = {'count': 0, 'size': 0}
                
            directories[top_dir]['count'] += 1
            directories[top_dir]['size'] += size
            
            # Extract filename from path
            filename = path.split('/')[-1]
        else:
            # This is a file at the root level
            filename = path
            
        # Handle files with no extension (like .gitignore, Dockerfile)
        if filename.startswith('.') and '.' not in filename[1:]:
            # This is a dotfile with no extension (like .gitignore)
            if filename not in specific_files:
                specific_files[filename] = {'count': 0, 'size': 0}
                
            specific_files[filename]['count'] += 1
            specific_files[filename]['size'] += size
            continue
            
        # Handle special files with no extension
        if '.' not in filename and filename in ['Dockerfile', 'Makefile', 'README', 'LICENSE']:
            if filename not in specific_files:
                specific_files[filename] = {'count': 0, 'size': 0}
                
            specific_files[filename]['count'] += 1
            specific_files[filename]['size'] += size
            continue
            
        # Extract extension for normal files
        if '.' in filename:
            # Handle cases where the filename might have multiple dots
            ext = filename.split('.')[-1].lower()
            # Skip if the extension is too long (likely not an extension but part of the name)
            if len(ext) <= 10:  # Reasonable limit for extension length
                if ext not in extensions:
                    extensions[ext] = {'count': 0, 'size': 0}
                    
                extensions[ext]['count'] += 1
                extensions[ext]['size'] += size
    
    # Format file sizes for better display
    def format_size(size_in_bytes):
        """Convert size in bytes to human-readable format (KB, MB, etc.)"""
        if size_in_bytes < 1024:
            return f"{size_in_bytes} B"
        elif size_in_bytes < 1024 * 1024:
            return f"{size_in_bytes / 1024:.1f} KB"
        elif size_in_bytes < 1024 * 1024 * 1024:
            return f"{size_in_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_in_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    # Log some debug information
    print(f"Found {len(extensions)} unique extensions")
    print(f"Found {len(directories)} unique directories")
    print(f"Found {len(specific_files)} specific files")
    
    # Generate patterns
    patterns = []
    
    # Include ALL file extensions found in the repo
    for ext, data in extensions.items():
        count = data['count']
        size = data['size']
        formatted_size = format_size(size)
        
        # Create a readable label
        if ext in ['py', 'js', 'jsx', 'ts', 'tsx', 'go', 'java', 'c', 'cpp', 'h', 'md', 'yml', 
                  'yaml', 'json', 'css', 'html', 'rs', 'rb', 'php', 'swift']:
            # For common extensions, use descriptive names
            ext_labels = {
                'py': 'Python', 'js': 'JavaScript', 'jsx': 'React JSX', 'ts': 'TypeScript',
                'tsx': 'TypeScript React', 'go': 'Go', 'java': 'Java', 'c': 'C', 
                'cpp': 'C++', 'h': 'Header', 'md': 'Markdown', 'yml': 'YAML', 
                'yaml': 'YAML', 'json': 'JSON', 'css': 'CSS', 'html': 'HTML', 
                'rs': 'Rust', 'rb': 'Ruby', 'php': 'PHP', 'swift': 'Swift'
            }
            label = f"{ext_labels[ext]} Files (*.{ext})"
        else:
            # For uncommon extensions, use generic format
            label = f"Files with .{ext} extension (*.{ext})"
            
        patterns.append({
            "pattern": f"*.{ext}",
            "label": label,
            "count": count,
            "size": size,
            "formatted_size": formatted_size,
            "type": "extension"
        })
    
    # Include specific files
    for filename, data in specific_files.items():
        count = data['count']
        size = data['size']
        formatted_size = format_size(size)
        
        patterns.append({
            "pattern": filename,
            "label": f"{filename} Files",
            "count": count,
            "size": size,
            "formatted_size": formatted_size,
            "type": "specific_file"
        })
    
    # Include ALL directories found in the repo
    for dir_name, data in directories.items():
        count = data['count']
        size = data['size']
        formatted_size = format_size(size)
        
        # Skip directories that start with a dot (hidden directories)
        if dir_name.startswith('.') and dir_name not in ['.github', '.vscode']:
            continue
            
        # Create a readable label
        if dir_name in ['src', 'lib', 'test', 'tests', 'docs', 'examples', 'node_modules', 
                        'build', 'dist', 'venv', '.venv']:
            # For common directories, use descriptive names
            dir_labels = {
                'src': 'Source', 'lib': 'Library', 'test': 'Test',
                'tests': 'Tests', 'docs': 'Documentation', 'examples': 'Examples',
                'node_modules': 'Node Modules', 'build': 'Build Output', 
                'dist': 'Distribution', 'venv': 'Python Virtual Environment',
                '.venv': 'Python Virtual Environment', '.github': 'GitHub', 
                '.vscode': 'VS Code'
            }
            label = f"{dir_labels[dir_name]} Folder ({dir_name}/**)"
        else:
            # For uncommon directories, use generic format
            label = f"{dir_name}/** Folder"
            
        patterns.append({
            "pattern": f"*{dir_name}*",
            "label": label,
            "count": count,
            "size": size,
            "formatted_size": formatted_size,
            "type": "directory"
        })
    
    # Sort patterns: directories first, then extensions, then specific files
    # Within each category, sort by count (descending)
    directory_patterns = [p for p in patterns if p['type'] == 'directory']
    extension_patterns = [p for p in patterns if p['type'] == 'extension']
    specific_file_patterns = [p for p in patterns if p['type'] == 'specific_file']
    
    directory_patterns.sort(key=lambda x: x['count'], reverse=True)
    extension_patterns.sort(key=lambda x: x['count'], reverse=True)
    specific_file_patterns.sort(key=lambda x: x['count'], reverse=True)
    
    # Combine the sorted patterns
    sorted_patterns = directory_patterns + extension_patterns + specific_file_patterns
    
    return sorted_patterns