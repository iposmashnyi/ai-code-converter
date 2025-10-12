"""
Prompt templates for code conversion using LangChain
"""

from langchain.prompts import PromptTemplate, FewShotPromptTemplate
from langchain.prompts.example_selector import LengthBasedExampleSelector


# Base conversion template
BASE_CONVERSION_TEMPLATE = """You are an expert code converter. Convert the following {source_lang} code to {target_lang}.

Important rules:
1. Preserve the exact functionality and logic
2. Use idiomatic {target_lang} patterns and conventions
3. Maintain code structure and organization
4. Convert comments and docstrings appropriately
5. Handle language-specific features properly (e.g., Python decorators, JavaScript promises)
6. Ensure proper syntax for {target_lang}

Source code ({source_lang}):
```{source_lang}
{source_code}
```

Converted code ({target_lang}):
```{target_lang}"""

# Create the main conversion prompt
conversion_prompt = PromptTemplate(
    input_variables=["source_lang", "target_lang", "source_code"],
    template=BASE_CONVERSION_TEMPLATE
)

# Few-shot examples for common patterns
PYTHON_TO_JAVASCRIPT_EXAMPLES = [
    {
        "source_code": """class Calculator:
    def __init__(self, initial_value=0):
        self.value = initial_value

    def add(self, x):
        self.value += x
        return self.value""",
        "converted_code": """class Calculator {
    constructor(initialValue = 0) {
        this.value = initialValue;
    }

    add(x) {
        this.value += x;
        return this.value;
    }
}"""
    },
    {
        "source_code": """def process_list(items):
    \"\"\"Process a list of items and return filtered results.\"\"\"
    result = []
    for item in items:
        if item > 10:
            result.append(item * 2)
    return result""",
        "converted_code": """function processList(items) {
    /**
     * Process a list of items and return filtered results.
     */
    const result = [];
    for (const item of items) {
        if (item > 10) {
            result.push(item * 2);
        }
    }
    return result;
}"""
    },
    {
        "source_code": """import math

def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)""",
        "converted_code": """function calculateDistance(x1, y1, x2, y2) {
    return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
}"""
    }
]

JAVASCRIPT_TO_PYTHON_EXAMPLES = [
    {
        "source_code": """const fetchData = async (url) => {
    try {
        const response = await fetch(url);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error:', error);
        return null;
    }
};""",
        "converted_code": """import aiohttp
import asyncio

async def fetch_data(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return data
    except Exception as error:
        print(f'Error: {error}')
        return None"""
    }
]

# Few-shot prompt for Python to JavaScript
python_to_js_example_template = PromptTemplate(
    input_variables=["source_code", "converted_code"],
    template="""Python code:
```python
{source_code}
```

JavaScript code:
```javascript
{converted_code}
```"""
)

python_to_js_few_shot_prompt = FewShotPromptTemplate(
    examples=PYTHON_TO_JAVASCRIPT_EXAMPLES,
    example_prompt=python_to_js_example_template,
    prefix="You are an expert at converting Python code to JavaScript. Here are some examples:",
    suffix="\nNow convert this Python code:\n```python\n{source_code}\n```\n\nJavaScript code:\n```javascript",
    input_variables=["source_code"]
)

# Language-specific conversion rules
CONVERSION_RULES = {
    ("python", "javascript"): {
        "type_mappings": {
            "dict": "object",
            "list": "array",
            "tuple": "array",
            "str": "string",
            "int": "number",
            "float": "number",
            "bool": "boolean",
            "None": "null"
        },
        "function_style": "camelCase",
        "class_style": "PascalCase",
        "indentation": 2,
        "semicolons": True
    },
    ("javascript", "python"): {
        "type_mappings": {
            "object": "dict",
            "array": "list",
            "string": "str",
            "number": "float",
            "boolean": "bool",
            "null": "None",
            "undefined": "None"
        },
        "function_style": "snake_case",
        "class_style": "PascalCase",
        "indentation": 4,
        "semicolons": False
    },
    ("python", "typescript"): {
        "type_mappings": {
            "dict": "Record<string, any>",
            "list": "Array<any>",
            "tuple": "[any, any]",
            "str": "string",
            "int": "number",
            "float": "number",
            "bool": "boolean",
            "None": "null"
        },
        "function_style": "camelCase",
        "class_style": "PascalCase",
        "indentation": 2,
        "semicolons": True,
        "add_types": True
    }
}

def get_conversion_prompt(source_lang: str, target_lang: str, use_few_shot: bool = True):
    """
    Get the appropriate prompt template for the conversion.

    Args:
        source_lang: Source programming language
        target_lang: Target programming language
        use_few_shot: Whether to use few-shot examples

    Returns:
        PromptTemplate or FewShotPromptTemplate
    """
    # Normalize language names
    source_lang = source_lang.lower()
    target_lang = target_lang.lower()

    # For now, use a simple prompt template with examples inline
    # This avoids the FewShotPromptTemplate parsing issues with curly braces in code
    if use_few_shot and source_lang == "python" and target_lang == "javascript":
        # Create a prompt with examples built-in
        enhanced_template = """You are an expert at converting Python code to JavaScript.

Here are some examples:

Python code:
```python
class Calculator:
    def __init__(self, initial_value=0):
        self.value = initial_value

    def add(self, x):
        self.value += x
        return self.value
```

JavaScript code:
```javascript
class Calculator {{
    constructor(initialValue = 0) {{
        this.value = initialValue;
    }}

    add(x) {{
        this.value += x;
        return this.value;
    }}
}}
```

Python code:
```python
def process_list(items):
    \"\"\"Process a list of items and return filtered results.\"\"\"
    result = []
    for item in items:
        if item > 10:
            result.append(item * 2)
    return result
```

JavaScript code:
```javascript
function processList(items) {{
    /**
     * Process a list of items and return filtered results.
     */
    const result = [];
    for (const item of items) {{
        if (item > 10) {{
            result.push(item * 2);
        }}
    }}
    return result;
}}
```

Now convert this Python code to JavaScript:

Source code (Python):
```python
{source_code}
```

Converted code (JavaScript):
```javascript"""

        return PromptTemplate(
            input_variables=["source_code"],
            template=enhanced_template
        )

    # Otherwise use the base template
    return conversion_prompt

def get_conversion_rules(source_lang: str, target_lang: str):
    """
    Get language-specific conversion rules.

    Args:
        source_lang: Source programming language
        target_lang: Target programming language

    Returns:
        Dictionary of conversion rules
    """
    key = (source_lang.lower(), target_lang.lower())
    return CONVERSION_RULES.get(key, {})


# Multi-file conversion template with context
MULTI_FILE_CONVERSION_TEMPLATE = """You are an expert code converter working on a multi-file project.
This is file {current_file}/{total_files} in the project.

IMPORTANT: Maintain consistency with previously converted files by using these established patterns:

Previously converted symbols:
{cached_symbols}

Import conversions:
{cached_imports}

Naming patterns to follow:
{patterns}

Source language: {source_lang}
Target language: {target_lang}

Current file: {file_name}
File imports: {file_imports}

Important rules:
1. Use the cached symbol mappings above for consistency
2. If a class/function was already converted, use the same name
3. Follow the established patterns for naming conventions
4. Preserve the exact functionality and logic
5. Use idiomatic {target_lang} patterns

Source code ({source_lang}):
```{source_lang}
{source_code}
```

Converted code ({target_lang}):
```{target_lang}"""


def get_multi_file_prompt(
    source_lang: str,
    target_lang: str,
    context: dict = None
):
    """
    Get prompt template for multi-file conversion with context.

    Args:
        source_lang: Source programming language
        target_lang: Target programming language
        context: Dictionary with cached symbols and patterns

    Returns:
        PromptTemplate configured for multi-file conversion
    """
    from langchain.prompts import PromptTemplate

    # Format context for the prompt
    if context:
        cached_symbols = "\n".join([
            f"  {src} → {tgt}"
            for src, tgt in context.get("cached_symbols", {}).items()
        ][:10])  # Show top 10

        cached_imports = "\n".join([
            f"  {src} → {tgt}"
            for src, tgt in context.get("cached_imports", {}).items()
        ])

        patterns = "\n".join([
            f"  - {p.get('description', str(p))}"
            for p in context.get("cached_patterns", [])
        ])
    else:
        cached_symbols = "  (No previous conversions)"
        cached_imports = "  (No import conversions yet)"
        patterns = "  - Use standard conventions for {target_lang}"

    # Create the prompt with injected context
    template = MULTI_FILE_CONVERSION_TEMPLATE.format(
        cached_symbols=cached_symbols or "  (None yet)",
        cached_imports=cached_imports or "  (None yet)",
        patterns=patterns or "  - Follow standard {target_lang} conventions",
        source_lang="{source_lang}",
        target_lang="{target_lang}",
        current_file="{current_file}",
        total_files="{total_files}",
        file_name="{file_name}",
        file_imports="{file_imports}",
        source_code="{source_code}"
    )

    return PromptTemplate(
        input_variables=[
            "source_lang", "target_lang", "source_code",
            "current_file", "total_files", "file_name", "file_imports"
        ],
        template=template
    )
