import os
import subprocess
import json
import glob
import requests
from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS

app = Flask(__name__)

# --- CORS Configuration ---
# Explicitly allow the Cloud Workstation frontend origin and common local origins
frontend_origin_cloud = "https://5173-idx-tutorial-codebase-knowledge-1745606939195.cluster-2xid2zxbenc4ixa74rpk7q7fyk.cloudworkstations.dev"
frontend_origin_local = "http://localhost:5173" # Common Vite default
frontend_origin_local_cra = "http://localhost:3000" # Common Create React App default

CORS(app, resources={
    r"/api/*": {
        "origins": [frontend_origin_cloud, frontend_origin_local, frontend_origin_local_cra]
    }
})
# -------------------------

# Assume the main.py script is in the parent directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

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

@app.route('/api/generate', methods=['POST'])
def generate_tutorial():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    gemini_key = data.get('gemini_key')
    github_token = data.get('github_token') # Optional
    repo_url = data.get('repo_url')
    include_patterns = data.get('include_patterns', '') # Assuming comma-separated string for simplicity
    exclude_patterns = data.get('exclude_patterns', '') # Assuming comma-separated string
    max_file_size = data.get('max_file_size', 100000) # Default to 100KB if not provided

    if not gemini_key or not repo_url:
        return jsonify({"error": "Missing required fields: gemini_key, repo_url"}), 400

    repo_name = get_repo_name_from_url(repo_url)
    output_path = os.path.join(OUTPUT_DIR, repo_name)

    # Construct the command
    # SECURITY WARNING: Directly passing API keys like this is risky.
    # Consider environment variables or temporary config files for production.
    command = [
        'python',
        os.path.join(PROJECT_ROOT, 'main.py'),
        '--repo', repo_url,
        '--name', repo_name,  # Add explicit project name to prevent duplication
        '--max-size', str(max_file_size)  # Add max file size parameter
    ]
    
    # Add include patterns if provided
    if include_patterns:
        command.extend(['--include'] + include_patterns.split(','))
    
    # Add exclude patterns if provided
    if exclude_patterns:
        command.extend(['--exclude'] + exclude_patterns.split(','))
    
    # For simplicity, let's assume main.py reads keys from environment
    env = os.environ.copy()
    if gemini_key:
        env['GEMINI_API_KEY'] = gemini_key
    if github_token:
        env['GITHUB_TOKEN'] = github_token
        
    print(f"Setting environment variables: GEMINI_API_KEY={gemini_key[:5]}... GITHUB_TOKEN={github_token[:5] if github_token else None}...")

    print(f"Running command: {' '.join(command)}")
    try:
        # Execute the script from the project root directory
        process = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True, # Raise exception on non-zero exit code
            env=env,
            timeout=300 # Add a timeout (e.g., 5 minutes)
        )
        print("Script STDOUT:", process.stdout)
        print("Script STDERR:", process.stderr)
        return jsonify({"message": "Generation complete", "repo_name": repo_name}), 200
    except subprocess.TimeoutExpired as e:
        print(f"Error executing main.py: Timeout Expired")
        print("STDOUT so far:", e.stdout)
        print("STDERR so far:", e.stderr)
        return jsonify({"error": "Generation failed", "details": "Script execution timed out."}), 500
    except subprocess.CalledProcessError as e:
        print(f"Error executing main.py: {e}")
        print("Error STDOUT:", e.stdout)
        print("Error STDERR:", e.stderr)
        error_detail = e.stderr or e.stdout or "Unknown execution error"
        return jsonify({"error": "Generation failed", "details": error_detail}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@app.route('/api/output-structure/<repo_name>', methods=['GET'])
def get_output_structure(repo_name):
    safe_repo_name = get_repo_name_from_url(repo_name) # Sanitize just in case
    repo_output_path = os.path.join(OUTPUT_DIR, safe_repo_name)
    if not os.path.isdir(repo_output_path):
        return jsonify({"error": "Output not found for this repository"}), 404

    structure = {"chapters": []}
    try:
        # Simple structure assumption: Chapters are dirs like 'chapter_1', 'chapter_2'
        # Lessons are markdown files within chapter dirs.
        # Sort chapters numerically if possible
        chapter_dirs = sorted(
            [d for d in glob.glob(os.path.join(repo_output_path, 'chapter_*')) if os.path.isdir(d)],
            key=lambda x: int(os.path.basename(x).split('_')[-1]) if os.path.basename(x).split('_')[-1].isdigit() else float('inf')
        )

        if not chapter_dirs:
             # Fallback: Look for index.md and maybe other top-level md files
             index_md = os.path.join(repo_output_path, 'index.md')
             other_md_files = glob.glob(os.path.join(repo_output_path, '*.md'))
             lessons = []
             if os.path.exists(index_md):
                  lessons.append({"title": "Overview", "path": "index.md"})
             # Add other top-level md files, excluding index.md if it exists
             for md_file in other_md_files:
                 if os.path.basename(md_file) != 'index.md':
                     lesson_basename = os.path.basename(md_file)
                     lesson_title = os.path.splitext(lesson_basename)[0].replace('_', ' ').title()
                     lessons.append({"title": lesson_title, "path": lesson_basename})

             if lessons:
                 structure["chapters"].append({
                     "title": repo_name, # Use repo name as title
                     "lessons": lessons
                 })
             else:
                 # No recognizable structure
                 return jsonify({"error": "Could not determine tutorial structure (no chapter_* dirs or *.md files found)"}), 404

        else:
            for chapter_dir in chapter_dirs:
                chapter_name = os.path.basename(chapter_dir)
                chapter_title = chapter_name.replace('_', ' ').title() # e.g., "Chapter 1"

                lessons = []
                # Sort lessons numerically if possible
                lesson_files = sorted(
                    glob.glob(os.path.join(chapter_dir, '*.md')),
                     key=lambda x: int(os.path.splitext(os.path.basename(x))[0].split('_')[-1]) if os.path.splitext(os.path.basename(x))[0].split('_')[-1].isdigit() else float('inf')
                )

                for lesson_file in lesson_files:
                    lesson_basename = os.path.basename(lesson_file)
                    lesson_title = os.path.splitext(lesson_basename)[0].replace('_', ' ').title() # e.g., "Lesson 1 Intro"
                    # Use os.path.join for cross-platform compatibility
                    lesson_path = os.path.join(chapter_name, lesson_basename).replace('', '/') # Ensure forward slashes
                    lessons.append({"title": lesson_title, "path": lesson_path})

                if lessons:
                    structure["chapters"].append({"title": chapter_title, "lessons": lessons})

        # Handle case where chapter folders exist but contain no markdown files
        if not structure["chapters"]:
             return jsonify({"error": "Could not determine tutorial structure (found chapter_* dirs but no *.md files inside)"}), 404

        return jsonify(structure), 200

    except Exception as e:
        print(f"Error scanning output directory: {e}")
        return jsonify({"error": "Failed to read tutorial structure"}), 500


@app.route('/api/output-content/<repo_name>/<path:file_path>', methods=['GET'])
def get_output_content(repo_name, file_path):
    safe_repo_name = get_repo_name_from_url(repo_name) # Sanitize just in case
    # Basic security check: prevent accessing files outside the intended output dir
    repo_output_path = os.path.join(OUTPUT_DIR, safe_repo_name)

    # Decode the file path which might be URL-encoded
    decoded_file_path = request.path.split(f'/api/output-content/{repo_name}/', 1)[1]
    full_path = os.path.join(repo_output_path, decoded_file_path)

    # Normalize paths to prevent directory traversal (../)
    safe_base_path = os.path.abspath(repo_output_path)
    safe_full_path = os.path.abspath(full_path)

    # Extra check: ensure the resolved path is still within the intended directory
    if not safe_full_path.startswith(safe_base_path + os.sep) and safe_full_path != safe_base_path:
         # Check if it's exactly the base path if file_path was empty or '/' (though unlikely with routing)
         if not (safe_full_path == safe_base_path and (not decoded_file_path or decoded_file_path == '/')):
            print(f"Access Denied: Path traversal attempt? Base: {safe_base_path}, Requested: {safe_full_path}")
            abort(404, description="Access denied: Invalid file path")

    if not os.path.isfile(safe_full_path):
        print(f"File Not Found: {safe_full_path}")
        abort(404, description="File not found")

    try:
        # Read the file content
        # Need to be careful with large files - consider streaming later
        with open(safe_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"content": content}), 200
    except Exception as e:
        print(f"Error reading file {safe_full_path}: {e}")
        abort(500, description="Failed to read file content")


@app.route('/api/fetch-patterns', methods=['POST'])
def fetch_patterns():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    github_token = data.get('github_token')
    repo_url = data.get('repo_url')

    if not repo_url:
        return jsonify({"error": "Missing repository URL"}), 400

    try:
        # Use the existing function to extract the repo name from URL
        repo_name = get_repo_name_from_url(repo_url)
        
        # Extract owner and repo from URL
        parts = repo_url.strip('/').split('/')
        if len(parts) < 2:
            return jsonify({"error": "Invalid repository URL format"}), 400
            
        # Handle both https://github.com/owner/repo and git@github.com:owner/repo.git formats
        if 'github.com' in repo_url:
            if 'github.com/' in repo_url:
                owner_repo = repo_url.split('github.com/')[1].split('/')
            else:
                owner_repo = repo_url.split(':')[1].split('/')
                
            owner = owner_repo[0]
            repo = owner_repo[1].replace('.git', '')
        else:
            return jsonify({"error": "Only GitHub repositories are supported"}), 400
            
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
            return jsonify({
                "error": f"GitHub API error: {response.status_code}",
                "details": response.json().get('message', 'Unknown error')
            }), response.status_code
            
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
        
        return jsonify({
            "patterns": patterns,
            "file_count": len(all_files)
        }), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to connect to GitHub API", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

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

if __name__ == '__main__':
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Make sure to adjust host and port as needed
    # Run on 0.0.0.0 to be accessible within the container network
    app.run(host='0.0.0.0', port=5001, debug=True)
