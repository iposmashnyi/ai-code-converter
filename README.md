# AI Code Converter - LangGraph Edition

**Intelligent code conversion between programming languages using Claude Sonnet 4 and LangGraph.**

Convert entire codebases with automatic file discovery, consistent naming patterns, and built-in checkpointing for resumable conversions.

## 🌟 Features

- **🤖 LLM-Driven**: No hardcoded patterns - Claude intelligently understands and converts code
- **🔄 Smart File Discovery**: Automatically identifies source files and excludes build artifacts
- **🧰 Tool-Based Architecture**: LLM uses tools to explore, read, and write files
- **📊 State Management**: LangGraph handles all state and progress automatically

## 🏗️ Architecture

Built on **LangGraph** with **Claude Sonnet 4**:

```
┌─────────────────┐
│ analyze_project │  ← Understands project structure
└────────┬────────┘
         ↓
┌────────┴─────────┐
│ discover_files   │  ← Selects files to convert
└────────┬─────────┘
         ↓
┌────────┴─────────┐
│  convert_file    │  ← Converts with context
└────────┬─────────┘
         ↓
    [More files?] ──Yes→ (Loop back)
         │
         No
         ↓
       [END]
```

Each node automatically checkpointed by `InMemorySaver` for resume capability.

## 📦 Installation

```bash
git clone https://github.com/yourusername/ai-code-converter.git
cd ai-code-converter

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## 🚀 Usage

### Basic Conversion

```bash
python convert_project.py ./my-python-app ./my-js-app \
  --from python \
  --to javascript
```

### With Custom Thread ID (for resuming)

```bash
python convert_project.py ./source ./output \
  --from python \
  --to typescript \
  --thread-id my-session-001
```

If interrupted (Ctrl+C), resume with the same command and thread-id!

### Available Languages

The LLM handles **any programming language** - no hardcoded rules!

Common examples:
- Python ⇄ JavaScript
- JavaScript ⇄ TypeScript
- Java ⇄ Kotlin
- Python ⇄ Go
- And many more...

## 🎯 How It Works

### 1. **Intelligent File Discovery**

The agent uses tools to explore your project and selects files to convert:

```python
# No hardcoded patterns! The LLM decides:
- list_directory_files → Explore structure
- check_gitignore_patterns → Understand exclusions
- search_files_by_pattern → Find source files
```

### 2. **Context-Aware Conversion**

Each file is converted with accumulated context for consistency:

```python
conversion_context = {
  "UserModel": "UserModel",       # Kept same name
  "get_user": "getUser",          # snake_case → camelCase
  "flask.Flask": "express"        # Library mapping
}
```

The LLM sees this context and maintains consistency automatically!


## 📁 Project Structure

```
ai-code-converter/
├── src/
│   ├── state.py          # ConversionState TypedDict
│   ├── tools.py          # LangChain @tool functions
│   ├── prompts.py        # System prompt
│   └── agent.py          # LangGraph agent (main logic)
├── convert_project.py    # CLI entry point
├── requirements.txt      # Dependencies
└── .env                  # API key configuration
```

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### CLI Options

```bash
python convert_project.py [OPTIONS] SOURCE OUTPUT

Options:
  --from, -f           Source language (default: python)
  --to, -t             Target language (default: javascript)
  --thread-id          Thread ID for checkpointing (default: default)
  --model              Claude model (default: claude-sonnet-4-20250514)
  -h, --help           Show help message
```

## 🎨 Example Output

```
============================================================
  AI Code Converter - LangGraph + Claude Sonnet 4
============================================================

🤖 Initializing agent...
   Model: claude-sonnet-4-20250514
   Checkpointing: Enabled (thread-id: default)

🚀 Starting conversion: python → javascript
   Source: ./my-python-app
   Target: ./my-js-app
   Thread ID: default (use this to resume if interrupted)

📊 Analyzing project structure...
✓ Project type: web_application

🔍 Discovering files to convert...
✓ Found 8 files to convert

🔄 Converting [1/8]: app.py
  ✓ Saved to: ./my-js-app/app.js

🔄 Converting [2/8]: models.py
  ✓ Saved to: ./my-js-app/models.js

...

============================================================
✅ Conversion Complete!
   Succeeded: 8
   Failed: 0
   Patterns discovered: 12
============================================================

✅ Conversion complete!
   Output directory: ./my-js-app

📋 Conversion patterns discovered:
   User → User
   get_user → getUser
   create_user → createUser
   ... and 9 more
```

## 📚 Technical Details

### State Flow

```python
ConversionState = {
  "source_dir": str,
  "target_dir": str,
  "source_lang": str,
  "target_lang": str,
  "files_to_convert": List[str],
  "current_file_index": int,
  "converted_files": List[Dict],  # Accumulated
  "conversion_context": Dict,     # Replaces SymbolCache!
  "files_completed": int,
  "files_failed": int
}
```

### Tools Available to LLM

```python
- list_directory_files(directory)
- read_file_content(file_path)
- write_file_content(file_path, content)
- get_file_info(file_path)
- search_files_by_pattern(directory, pattern)
- check_gitignore_patterns(directory)
```

## 🤝 Contributing

Contributions welcome! The codebase is now much simpler to understand and extend.

## 📄 License

MIT

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - State machine framework
- [LangChain](https://github.com/langchain-ai/langchain) - LLM orchestration
- [Claude Sonnet 4](https://www.anthropic.com/) - AI model

---

**Note**: This is a complete architectural rewrite focusing on simplicity and LLM-native design. The LLM does the intelligent work - we just provide the tools and state management!
