import os
import subprocess
import json
import glob
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

    if not gemini_key or not repo_url:
        return jsonify({"error": "Missing required fields: gemini_key, repo_url"}), 400

    repo_name = get_repo_name_from_url(repo_url)

    # Construct the command
    # SECURITY WARNING: Directly passing API keys like this is risky.
    # Consider environment variables or temporary config files for production.
    command = [
        'python',
        os.path.join(PROJECT_ROOT, 'main.py'),
        '--repo', repo_url
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


if __name__ == '__main__':
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Make sure to adjust host and port as needed
    # Run on 0.0.0.0 to be accessible within the container network
    app.run(host='0.0.0.0', port=5001, debug=True)
