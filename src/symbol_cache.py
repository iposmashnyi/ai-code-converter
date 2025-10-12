"""
Symbol cache for maintaining consistency across file conversions.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict
import re


class SymbolCache:
    """
    Maintains a cache of symbol conversions to ensure consistency
    across multiple files in a project.
    """

    def __init__(self):
        """Initialize the symbol cache."""
        # Core symbol mappings (source -> target)
        self.symbol_mappings: Dict[str, str] = {}

        # Type mappings
        self.type_mappings: Dict[str, str] = {}

        # Import mappings (package/module conversions)
        self.import_mappings: Dict[str, str] = {}

        # Function/method name conversions
        self.function_mappings: Dict[str, str] = {}

        # Class name conversions
        self.class_mappings: Dict[str, str] = {}

        # Common patterns discovered
        self.patterns: List[Dict] = []

        # Files that have been processed
        self.processed_files: Set[str] = set()

        # Statistics
        self.stats = {
            "total_symbols": 0,
            "reused_symbols": 0,
            "files_processed": 0
        }

    def add_conversion(
        self,
        source_symbol: str,
        target_symbol: str,
        symbol_type: str = "general"
    ):
        """
        Add a symbol conversion to the cache.

        Args:
            source_symbol: Original symbol name
            target_symbol: Converted symbol name
            symbol_type: Type of symbol (general, class, function, type, import)
        """
        # Store in general mappings
        self.symbol_mappings[source_symbol] = target_symbol

        # Store in specific category
        if symbol_type == "class":
            self.class_mappings[source_symbol] = target_symbol
        elif symbol_type == "function":
            self.function_mappings[source_symbol] = target_symbol
        elif symbol_type == "type":
            self.type_mappings[source_symbol] = target_symbol
        elif symbol_type == "import":
            self.import_mappings[source_symbol] = target_symbol

        self.stats["total_symbols"] += 1

    def get_conversion(self, source_symbol: str) -> Optional[str]:
        """
        Get the converted version of a symbol if it exists.

        Args:
            source_symbol: Original symbol name

        Returns:
            Converted symbol name or None
        """
        if source_symbol in self.symbol_mappings:
            self.stats["reused_symbols"] += 1
            return self.symbol_mappings[source_symbol]
        return None

    def extract_symbols_from_code(
        self,
        source_code: str,
        target_code: str,
        source_lang: str,
        target_lang: str
    ):
        """
        Extract and cache symbols from converted code.

        Args:
            source_code: Original source code
            target_code: Converted code
            source_lang: Source language
            target_lang: Target language
        """
        if source_lang == "python" and target_lang == "javascript":
            self._extract_python_to_js_symbols(source_code, target_code)
        elif source_lang == "javascript" and target_lang == "python":
            self._extract_js_to_python_symbols(source_code, target_code)
        # Add more language pairs as needed

    def _extract_python_to_js_symbols(self, python_code: str, js_code: str):
        """Extract symbols from Python to JavaScript conversion."""

        # Extract Python classes
        python_classes = re.findall(r'class\s+(\w+)', python_code)
        # Extract JavaScript classes
        js_classes = re.findall(r'class\s+(\w+)', js_code)

        # Map classes if counts match
        if len(python_classes) == len(js_classes):
            for py_class, js_class in zip(python_classes, js_classes):
                self.add_conversion(py_class, js_class, "class")

        # Extract Python functions
        python_functions = re.findall(r'def\s+(\w+)\s*\(', python_code)
        # Extract JavaScript functions (various patterns)
        js_functions = []
        js_functions.extend(re.findall(r'function\s+(\w+)\s*\(', js_code))
        js_functions.extend(re.findall(r'const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>', js_code))

        # Map functions (approximate matching)
        for py_func in python_functions:
            # Convert snake_case to camelCase
            js_func_expected = self._snake_to_camel(py_func)
            if js_func_expected in js_functions:
                self.add_conversion(py_func, js_func_expected, "function")

        # Extract and map common imports
        if "import flask" in python_code and "express" in js_code:
            self.add_conversion("flask.Flask", "express", "import")
        if "import requests" in python_code and ("axios" in js_code or "fetch" in js_code):
            self.add_conversion("requests", "axios", "import")
        if "import json" in python_code:
            self.add_conversion("json.dumps", "JSON.stringify", "function")
            self.add_conversion("json.loads", "JSON.parse", "function")

    def _extract_js_to_python_symbols(self, js_code: str, python_code: str):
        """Extract symbols from JavaScript to Python conversion."""

        # Extract JavaScript classes
        js_classes = re.findall(r'class\s+(\w+)', js_code)
        # Extract Python classes
        python_classes = re.findall(r'class\s+(\w+)', python_code)

        # Map classes if counts match
        if len(js_classes) == len(python_classes):
            for js_class, py_class in zip(js_classes, python_classes):
                self.add_conversion(js_class, py_class, "class")

        # Extract JavaScript functions
        js_functions = []
        js_functions.extend(re.findall(r'function\s+(\w+)\s*\(', js_code))
        js_functions.extend(re.findall(r'const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>', js_code))

        # Extract Python functions
        python_functions = re.findall(r'def\s+(\w+)\s*\(', python_code)

        # Map functions
        for js_func in js_functions:
            py_func_expected = self._camel_to_snake(js_func)
            if py_func_expected in python_functions:
                self.add_conversion(js_func, py_func_expected, "function")

    def _snake_to_camel(self, snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])

    def _camel_to_snake(self, camel_str: str) -> str:
        """Convert camelCase to snake_case."""
        return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()

    def get_context_for_file(
        self,
        file_imports: List[str],
        max_context_items: int = 10
    ) -> Dict[str, any]:
        """
        Get relevant cached conversions for a file based on its imports.

        Args:
            file_imports: List of imports in the file
            max_context_items: Maximum number of context items to return

        Returns:
            Dictionary of relevant cached conversions
        """
        context = {
            "cached_symbols": {},
            "cached_imports": {},
            "cached_patterns": [],
            "suggested_conversions": {}
        }

        # Find relevant import mappings
        for import_str in file_imports:
            for cached_import, converted in self.import_mappings.items():
                if cached_import in import_str or import_str in cached_import:
                    context["cached_imports"][cached_import] = converted

        # Add most frequently used symbols
        symbol_count = min(max_context_items, len(self.symbol_mappings))
        if symbol_count > 0:
            # Get most recent symbols (they're likely more relevant)
            recent_symbols = list(self.symbol_mappings.items())[-symbol_count:]
            context["cached_symbols"] = dict(recent_symbols)

        # Add relevant patterns
        context["cached_patterns"] = self.patterns[:5]

        return context

    def add_pattern(self, pattern: Dict):
        """
        Add a discovered pattern for reuse.

        Args:
            pattern: Dictionary describing the pattern
                     e.g., {"from": "snake_case", "to": "camelCase", "type": "naming"}
        """
        if pattern not in self.patterns:
            self.patterns.append(pattern)

    def mark_file_processed(self, file_path: str):
        """Mark a file as processed."""
        self.processed_files.add(file_path)
        self.stats["files_processed"] += 1

    def is_file_processed(self, file_path: str) -> bool:
        """Check if a file has been processed."""
        return file_path in self.processed_files

    def save_to_file(self, output_path: str):
        """
        Save the cache to a JSON file for persistence.

        Args:
            output_path: Path to save the cache
        """
        cache_data = {
            "symbol_mappings": self.symbol_mappings,
            "type_mappings": self.type_mappings,
            "import_mappings": self.import_mappings,
            "function_mappings": self.function_mappings,
            "class_mappings": self.class_mappings,
            "patterns": self.patterns,
            "processed_files": list(self.processed_files),
            "stats": self.stats
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)

        print(f"Symbol cache saved to {output_path}")

    def load_from_file(self, input_path: str) -> bool:
        """
        Load cache from a JSON file.

        Args:
            input_path: Path to load the cache from

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            self.symbol_mappings = cache_data.get("symbol_mappings", {})
            self.type_mappings = cache_data.get("type_mappings", {})
            self.import_mappings = cache_data.get("import_mappings", {})
            self.function_mappings = cache_data.get("function_mappings", {})
            self.class_mappings = cache_data.get("class_mappings", {})
            self.patterns = cache_data.get("patterns", [])
            self.processed_files = set(cache_data.get("processed_files", []))
            self.stats = cache_data.get("stats", {
                "total_symbols": 0,
                "reused_symbols": 0,
                "files_processed": 0
            })

            print(f"Symbol cache loaded from {input_path}")
            print(f"  - {len(self.symbol_mappings)} symbols")
            print(f"  - {len(self.processed_files)} processed files")
            return True

        except Exception as e:
            print(f"Could not load cache: {e}")
            return False

    def get_summary(self) -> str:
        """Get a summary of the cache contents."""
        return f"""
Symbol Cache Summary:
  Total symbols cached: {len(self.symbol_mappings)}
  Classes: {len(self.class_mappings)}
  Functions: {len(self.function_mappings)}
  Types: {len(self.type_mappings)}
  Imports: {len(self.import_mappings)}
  Patterns: {len(self.patterns)}
  Files processed: {len(self.processed_files)}

Statistics:
  Total symbols added: {self.stats['total_symbols']}
  Symbols reused: {self.stats['reused_symbols']}
  Reuse rate: {self.stats['reused_symbols'] / max(self.stats['total_symbols'], 1) * 100:.1f}%
"""

    def clear(self):
        """Clear all cached data."""
        self.symbol_mappings.clear()
        self.type_mappings.clear()
        self.import_mappings.clear()
        self.function_mappings.clear()
        self.class_mappings.clear()
        self.patterns.clear()
        self.processed_files.clear()
        self.stats = {
            "total_symbols": 0,
            "reused_symbols": 0,
            "files_processed": 0
        }