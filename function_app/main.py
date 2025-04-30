import dotenv
import os
import argparse
# Import the function that creates the flow
from flow import create_tutorial_flow

dotenv.load_dotenv()

# Default file patterns
DEFAULT_INCLUDE_PATTERNS = {
    "*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go", "*.java", "*.pyi", "*.pyx",
    "*.c", "*.cc", "*.cpp", "*.h", "*.md", "*.rst", "Dockerfile",
    "Makefile", "*.yaml", "*.yml",
}

DEFAULT_EXCLUDE_PATTERNS = {
    "venv/*", ".venv/*", "*test*", "tests/*", "docs/*", "examples/*", "v1/*",
    "dist/*", "build/*", "experimental/*", "deprecated/*",
    "legacy/*", ".git/*", ".github/*", ".next/*", ".vscode/*", "obj/*", "bin/*", "node_modules/*", "*.log"
}

# New function for Azure Functions integration
def generate_tutorial_content(repo_url, repo_name, include_patterns=None, exclude_patterns=None, max_file_size=100000, language="english"):
    """
    Generate tutorial content for the given repository.
    This function is called directly by the Azure Function instead of via subprocess.
    
    Args:
        repo_url: URL of the GitHub repository
        repo_name: Name of the repository (project name)
        include_patterns: List of file patterns to include
        exclude_patterns: List of file patterns to exclude
        max_file_size: Maximum file size in bytes
        language: Language for the tutorial
        
    Returns:
        A dictionary with the generation results
    """
    # Get GitHub token from environment variable
    github_token = os.environ.get('GITHUB_TOKEN')
    
    # Initialize the shared dictionary with inputs
    shared = {
        "repo_url": repo_url,
        "local_dir": None,  # We're only supporting repos in this function
        "project_name": repo_name,
        "github_token": github_token,
        "output_dir": "output",  # Base directory for output
        
        # Add include/exclude patterns and max file size
        "include_patterns": set(include_patterns) if include_patterns else DEFAULT_INCLUDE_PATTERNS,
        "exclude_patterns": set(exclude_patterns) if exclude_patterns else DEFAULT_EXCLUDE_PATTERNS,
        "max_file_size": max_file_size,
        
        # Add language for multi-language support
        "language": language,
        
        # Outputs will be populated by the nodes
        "files": [],
        "abstractions": [],
        "relationships": {},
        "chapter_order": [],
        "chapters": [],
        "final_output_dir": None
    }
    
    # Display starting message
    print(f"Starting tutorial generation for: {repo_url} in {language.capitalize()} language")
    
    # Create the flow instance
    tutorial_flow = create_tutorial_flow()
    
    # Run the flow
    tutorial_flow.run(shared)
    
    # Return the results
    return {
        "success": True,
        "repo_name": repo_name,
        "output_dir": shared.get("final_output_dir"),
        "chapters": shared.get("chapters", []),
        "chapter_order": shared.get("chapter_order", [])
    }

# --- Main Function ---
def main():
    parser = argparse.ArgumentParser(description="Generate a tutorial for a GitHub codebase or local directory.")

    # Create mutually exclusive group for source
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--repo", help="URL of the public GitHub repository.")
    source_group.add_argument("--dir", help="Path to local directory.")

    parser.add_argument("-n", "--name", help="Project name (optional, derived from repo/directory if omitted).")
    parser.add_argument("-t", "--token", help="GitHub personal access token (optional, reads from GITHUB_TOKEN env var if not provided).")
    parser.add_argument("-o", "--output", default="output", help="Base directory for output (default: ./output).")
    parser.add_argument("-i", "--include", nargs="+", help="Include file patterns (e.g. '*.py' '*.js'). Defaults to common code files if not specified.")
    parser.add_argument("-e", "--exclude", nargs="+", help="Exclude file patterns (e.g. 'tests/*' 'docs/*'). Defaults to test/build directories if not specified.")
    parser.add_argument("-s", "--max-size", type=int, default=100000, help="Maximum file size in bytes (default: 100000, about 100KB).")
    # Add language parameter for multi-language support
    parser.add_argument("--language", default="english", help="Language for the generated tutorial (default: english)")

    args = parser.parse_args()

    # Get GitHub token from argument or environment variable if using repo
    github_token = None
    if args.repo:
        github_token = args.token or os.environ.get('GITHUB_TOKEN')
        if not github_token:
            print("Warning: No GitHub token provided. You might hit rate limits for public repositories.")

    # Initialize the shared dictionary with inputs
    shared = {
        "repo_url": args.repo,
        "local_dir": args.dir,
        "project_name": args.name, # Can be None, FetchRepo will derive it
        "github_token": github_token,
        "output_dir": args.output, # Base directory for CombineTutorial output

        # Add include/exclude patterns and max file size
        "include_patterns": set(args.include) if args.include else DEFAULT_INCLUDE_PATTERNS,
        "exclude_patterns": set(args.exclude) if args.exclude else DEFAULT_EXCLUDE_PATTERNS,
        "max_file_size": args.max_size,

        # Add language for multi-language support
        "language": args.language,

        # Outputs will be populated by the nodes
        "files": [],
        "abstractions": [],
        "relationships": {},
        "chapter_order": [],
        "chapters": [],
        "final_output_dir": None
    }

    # Display starting message with repository/directory and language
    print(f"Starting tutorial generation for: {args.repo or args.dir} in {args.language.capitalize()} language")

    # Create the flow instance
    tutorial_flow = create_tutorial_flow()

    # Run the flow
    tutorial_flow.run(shared)

if __name__ == "__main__":
    main()
