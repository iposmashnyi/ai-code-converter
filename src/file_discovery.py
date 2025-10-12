"""
File discovery and analysis for multi-file code conversion.
"""

import os
from pathlib import Path
from typing import List, Dict, Set, Optional
import fnmatch
from colorama import Fore, Style


class FileDiscovery:
    """Discovers and analyzes files for conversion."""

    # Common file extensions by language
    LANGUAGE_EXTENSIONS = {
        "python": [".py"],
        "javascript": [".js", ".jsx"],
        "typescript": [".ts", ".tsx"],
        "java": [".java"],
        "go": [".go"],
        "rust": [".rs"],
        "c": [".c", ".h"],
        "cpp": [".cpp", ".cc", ".hpp", ".h"],
        "csharp": [".cs"],
        "ruby": [".rb"],
        "php": [".php"],
        "swift": [".swift"],
        "kotlin": [".kt"],
    }

    # Directories to always exclude
    DEFAULT_EXCLUDE_DIRS = {
        "__pycache__", ".git", ".svn", ".hg",
        "node_modules", ".venv", "venv", "env",
        "build", "dist", ".pytest_cache", ".tox",
        "vendor", "target", ".idea", ".vscode",
        "coverage", "htmlcov", ".mypy_cache"
    }

    # File patterns to exclude
    DEFAULT_EXCLUDE_PATTERNS = [
        "*.pyc", "*.pyo", "*.pyd", ".DS_Store",
        "*.so", "*.dylib", "*.dll", "*.class",
        "*.min.js", "*.map", "*.test.*", "*.spec.*",
        "*_test.py", "test_*.py", "conftest.py",
        "setup.py", "__init__.py"  # Often just imports
    ]

    def __init__(
        self,
        source_language: str,
        exclude_dirs: Optional[Set[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        include_tests: bool = False
    ):
        """
        Initialize file discovery.

        Args:
            source_language: Programming language to look for
            exclude_dirs: Additional directories to exclude
            exclude_patterns: Additional file patterns to exclude
            include_tests: Whether to include test files
        """
        self.source_language = source_language.lower()
        self.extensions = self.LANGUAGE_EXTENSIONS.get(self.source_language, [])

        if not self.extensions:
            raise ValueError(f"Unsupported language: {source_language}")

        # Build exclusion sets
        self.exclude_dirs = self.DEFAULT_EXCLUDE_DIRS.copy()
        if exclude_dirs:
            self.exclude_dirs.update(exclude_dirs)

        self.exclude_patterns = self.DEFAULT_EXCLUDE_PATTERNS.copy()
        if exclude_patterns:
            self.exclude_patterns.extend(exclude_patterns)

        # Remove test exclusions if including tests
        if include_tests:
            self.exclude_patterns = [
                p for p in self.exclude_patterns
                if not any(test in p for test in ["test", "spec"])
            ]

    def discover_files(
        self,
        root_directory: str,
        max_files: int = 25
    ) -> List[Dict[str, any]]:
        """
        Discover files to convert in the given directory.

        Args:
            root_directory: Root directory to search
            max_files: Maximum number of files to return

        Returns:
            List of file information dictionaries
        """
        root_path = Path(root_directory).resolve()

        if not root_path.exists():
            raise ValueError(f"Directory does not exist: {root_directory}")

        discovered_files = []

        # Check for .gitignore
        gitignore_patterns = self._parse_gitignore(root_path)

        # Walk through directory
        for current_dir, dirs, files in os.walk(root_path):
            current_path = Path(current_dir)

            # Filter out excluded directories
            dirs[:] = [
                d for d in dirs
                if d not in self.exclude_dirs
                and not self._matches_gitignore(
                    current_path / d,
                    root_path,
                    gitignore_patterns
                )
            ]

            # Process files
            for file in files:
                file_path = current_path / file

                # Check if file should be included
                if not self._should_include_file(
                    file_path,
                    root_path,
                    gitignore_patterns
                ):
                    continue

                # Get file info
                relative_path = file_path.relative_to(root_path)
                file_info = {
                    "path": str(file_path),
                    "relative_path": str(relative_path),
                    "name": file,
                    "size": file_path.stat().st_size,
                    "lines": self._count_lines(file_path)
                }

                discovered_files.append(file_info)

                # Stop if we've found enough files
                if len(discovered_files) >= max_files:
                    print(f"{Fore.YELLOW}Reached file limit ({max_files}){Style.RESET_ALL}")
                    break

            if len(discovered_files) >= max_files:
                break

        # Sort files by importance
        discovered_files = self._sort_by_importance(discovered_files)

        return discovered_files[:max_files]

    def _should_include_file(
        self,
        file_path: Path,
        root_path: Path,
        gitignore_patterns: List[str]
    ) -> bool:
        """Check if a file should be included in conversion."""

        # Check extension
        if not any(str(file_path).endswith(ext) for ext in self.extensions):
            return False

        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_path.name, pattern):
                return False

        # Check gitignore
        if self._matches_gitignore(file_path, root_path, gitignore_patterns):
            return False

        # Check file size (skip very large files)
        if file_path.stat().st_size > 100_000:  # 100KB limit
            print(f"{Fore.YELLOW}Skipping large file: {file_path.name}{Style.RESET_ALL}")
            return False

        return True

    def _parse_gitignore(self, root_path: Path) -> List[str]:
        """Parse .gitignore file if it exists."""
        gitignore_path = root_path / ".gitignore"

        if not gitignore_path.exists():
            return []

        patterns = []
        try:
            with open(gitignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except Exception:
            pass

        return patterns

    def _matches_gitignore(
        self,
        file_path: Path,
        root_path: Path,
        patterns: List[str]
    ) -> bool:
        """Check if path matches any gitignore pattern."""
        relative = str(file_path.relative_to(root_path))

        for pattern in patterns:
            # Simple pattern matching (not full gitignore spec)
            if pattern.endswith('/'):
                # Directory pattern
                if file_path.is_dir() and fnmatch.fnmatch(file_path.name, pattern[:-1]):
                    return True
            else:
                # File pattern
                if fnmatch.fnmatch(file_path.name, pattern):
                    return True
                if fnmatch.fnmatch(relative, pattern):
                    return True

        return False

    def _count_lines(self, file_path: Path) -> int:
        """Count non-empty lines in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    def _sort_by_importance(self, files: List[Dict]) -> List[Dict]:
        """
        Sort files by importance for conversion order.

        Priority:
        1. Main entry points (main.py, app.py, index.js)
        2. Configuration files
        3. Models/schemas
        4. Core business logic
        5. Utilities/helpers
        6. Tests (if included)
        """
        def importance_score(file_info: Dict) -> int:
            name = file_info["name"].lower()
            path = file_info["relative_path"].lower()

            # Entry points get highest priority
            if name in ["main.py", "app.py", "__main__.py", "index.js", "index.ts"]:
                return 0

            # Configuration
            if "config" in name or "settings" in name:
                return 1

            # Models and schemas
            if "model" in path or "schema" in path:
                return 2

            # Routes/views/controllers
            if any(x in path for x in ["route", "view", "controller", "handler"]):
                return 3

            # Services/business logic
            if "service" in path or "manager" in path:
                return 4

            # Database/repository
            if any(x in path for x in ["database", "db", "repository", "repo"]):
                return 5

            # Utilities
            if "util" in path or "helper" in path:
                return 6

            # Tests
            if "test" in path:
                return 8

            # Everything else
            return 7

        return sorted(files, key=importance_score)

    def analyze_dependencies(self, file_path: str) -> Dict[str, List[str]]:
        """
        Analyze file dependencies (imports).

        Args:
            file_path: Path to file to analyze

        Returns:
            Dictionary with imports and exports
        """
        imports = []
        exports = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if self.source_language == "python":
                # Extract Python imports
                import_lines = [
                    line for line in content.split('\n')
                    if line.strip().startswith(('import ', 'from '))
                ]
                imports = import_lines

                # Extract Python exports (classes and functions)
                import ast
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            exports.append(f"class {node.name}")
                        elif isinstance(node, ast.FunctionDef):
                            if not node.name.startswith('_'):
                                exports.append(f"def {node.name}")
                except Exception:
                    pass

            elif self.source_language in ["javascript", "typescript"]:
                # Extract JS/TS imports
                import re
                import_pattern = r'(?:import|require)\s*\([\'"]([^\'"]+)[\'"]\)'
                imports = re.findall(import_pattern, content)

                # Extract exports
                export_pattern = r'export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)'
                exports = re.findall(export_pattern, content)

        except Exception as e:
            print(f"{Fore.YELLOW}Could not analyze {file_path}: {e}{Style.RESET_ALL}")

        return {
            "imports": imports,
            "exports": exports
        }

    def generate_summary(self, files: List[Dict]) -> str:
        """Generate a summary of discovered files."""
        total_lines = sum(f.get("lines", 0) for f in files)
        total_size = sum(f.get("size", 0) for f in files)

        summary = f"""
{Fore.CYAN}File Discovery Summary{Style.RESET_ALL}
{'=' * 40}
Total files found: {len(files)}
Total lines of code: {total_lines:,}
Total size: {total_size / 1024:.1f} KB
Language: {self.source_language}

Files by directory:
"""
        # Group files by directory
        dirs = {}
        for f in files:
            dir_name = str(Path(f["relative_path"]).parent)
            if dir_name == ".":
                dir_name = "root"
            dirs.setdefault(dir_name, 0)
            dirs[dir_name] += 1

        for dir_name, count in sorted(dirs.items()):
            summary += f"  {dir_name}: {count} files\n"

        return summary