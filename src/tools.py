"""
LangChain tools for file operations.
These tools allow the LLM to interact with the file system intelligently.

No hardcoded patterns - the LLM decides what to do!
"""

from langchain.tools import tool
from pathlib import Path
from typing import List, Dict, Any
import os


@tool
def list_directory_files(directory: str, max_depth: int = 3) -> str:
    """
    List all files in a directory up to a certain depth.
    Returns a formatted string showing the directory structure.

    Use this to explore the project structure and understand what files exist.

    Args:
        directory: Path to directory to list
        max_depth: Maximum depth to traverse (default: 3)
    """
    try:
        root = Path(directory).resolve()
        if not root.exists():
            return f"Error: Directory {directory} does not exist"

        files = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                relative = path.relative_to(root)
                depth = len(relative.parts)
                if depth <= max_depth:
                    # Format with indentation
                    indent = "  " * (depth - 1)
                    size_kb = path.stat().st_size / 1024
                    files.append(f"{indent}├── {path.name} ({size_kb:.1f}KB)")

        # Limit output to avoid token explosion
        result = "\n".join(files[:100])
        if len(files) > 100:
            result += f"\n... and {len(files) - 100} more files"

        return result

    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def read_file_content(file_path: str, max_lines: int = None) -> str:
    """
    Read the content of a file.
    Use this to understand what code is in a file before converting it.

    Args:
        file_path: Path to the file to read
        max_lines: Optional limit on number of lines to read
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File {file_path} does not exist"

        with open(path, 'r', encoding='utf-8') as f:
            if max_lines:
                lines = [f.readline() for _ in range(max_lines)]
                content = "".join(lines)
                if len(lines) == max_lines:
                    content += "\n... (file continues)"
            else:
                content = f.read()

        return content

    except UnicodeDecodeError:
        return f"Error: {file_path} appears to be a binary file, not text"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file_content(file_path: str, content: str) -> str:
    """
    Write content to a file, creating directories if needed.
    Use this to save converted code.

    Args:
        file_path: Path where to write the file
        content: Content to write
    """
    try:
        path = Path(file_path)

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Successfully wrote {len(content)} characters to {file_path}"

    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get metadata about a file (extension, size, parent directory).
    Use this to understand what type of file you're dealing with.

    Args:
        file_path: Path to the file
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File {file_path} does not exist"}

        stat = path.stat()

        return {
            "name": path.name,
            "extension": path.suffix,
            "size_bytes": stat.st_size,
            "parent_directory": path.parent.name,
            "absolute_path": str(path.resolve())
        }

    except Exception as e:
        return {"error": str(e)}


@tool
def search_files_by_pattern(directory: str, pattern: str) -> List[str]:
    """
    Search for files matching a pattern using glob syntax.

    Examples:
    - "*.py" - all Python files
    - "**/*.js" - all JavaScript files recursively
    - "**/test_*.py" - all test files

    Args:
        directory: Directory to search in
        pattern: Glob pattern to match
    """
    try:
        root = Path(directory)
        if not root.exists():
            return [f"Error: Directory {directory} does not exist"]

        matches = [str(p) for p in root.glob(pattern)]

        # Limit results
        if len(matches) > 50:
            return matches[:50] + [f"... and {len(matches) - 50} more matches"]

        return matches if matches else ["No files found matching pattern"]

    except Exception as e:
        return [f"Error searching files: {str(e)}"]


@tool
def check_gitignore_patterns(directory: str) -> List[str]:
    """
    Read .gitignore file if it exists to understand what files to exclude.

    Args:
        directory: Directory to check for .gitignore
    """
    try:
        gitignore_path = Path(directory) / ".gitignore"

        if not gitignore_path.exists():
            return ["No .gitignore file found"]

        with open(gitignore_path, 'r') as f:
            lines = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith('#')
            ]

        return lines[:50]  # Limit

    except Exception as e:
        return [f"Error reading .gitignore: {str(e)}"]


# Tool list for easy import
ALL_TOOLS = [
    list_directory_files,
    read_file_content,
    write_file_content,
    get_file_info,
    search_files_by_pattern,
    check_gitignore_patterns
]
