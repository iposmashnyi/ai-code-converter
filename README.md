# AI Code Converter - Single File Prototype

A minimal LangChain-based code converter that transforms code between programming languages using LLMs. This prototype focuses on single-file conversion with smart token management.

## Features

- 🔄 **Single File Conversion**: Convert one file at a time with full control
- 💰 **Cost Estimation**: Preview token usage and cost before conversion
- 🎯 **Few-Shot Learning**: Uses examples for better conversion quality
- 🔧 **Multiple LLM Support**: Works with OpenAI GPT and Anthropic Claude
- 📊 **Token Tracking**: Monitor token usage and costs
- 🎨 **Language Support**: Python ↔ JavaScript (easily extendable)

## Quick Start

### 1. Setup

```bash
# Clone and enter directory
cd ai-code-converter

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your OpenAI or Anthropic API key
```

### 2. Test the Converter

```bash
# Run the test script
python test_converter.py

# Or convert a specific file
python -m src.single_file_converter examples/sample.py \
  --from-lang python \
  --to-lang javascript \
  --output examples/output/sample.js
```

### 3. Use in Your Code

```python
from src.single_file_converter import FileConverter

# Initialize converter
converter = FileConverter(
    source_lang="python",
    target_lang="javascript",
    model="gpt-3.5-turbo"  # or "gpt-4", "claude-3-sonnet"
)

# Estimate cost before conversion
estimate = converter.estimate_cost("your_file.py")
print(f"Estimated cost: {estimate['estimated_cost']}")

# Convert and save
result = converter.convert_and_save(
    source_path="your_file.py",
    output_path="your_file.js"
)

if result["success"]:
    print(f"Conversion successful! Tokens used: {result['tokens_used']}")
```

## Project Structure

```
ai-code-converter/
├── src/
│   ├── single_file_converter.py  # Main converter logic
│   └── prompts.py                # LangChain prompts & templates
├── examples/
│   ├── sample.py                 # Test input file
│   └── output/                   # Converted files go here
├── test_converter.py             # Test script
├── requirements.txt              # Python dependencies
└── .env                         # API keys (create from .env.example)
```

## How It Works

1. **File Loading**: Reads source code file
2. **Token Estimation**: Calculates approximate token usage
3. **LangChain Processing**:
   - Uses few-shot examples for common patterns
   - Applies language-specific conversion rules
   - Manages prompts through LangChain templates
4. **LLM Conversion**: Sends to GPT/Claude for transformation
5. **Output Generation**: Saves converted code with proper formatting

## Token Management Strategy

This prototype implements efficient token usage:

- **Per-file processing**: No full codebase context loading
- **Token estimation**: Preview costs before running
- **Streaming support**: See results as they generate
- **Model selection**: Use cheaper models for simple files

Example token usage for a 100-line Python file:
- Input tokens: ~500
- Output tokens: ~600
- Total: ~1,100 tokens
- Cost: ~$0.002 (GPT-3.5)

## Supported Conversions

Currently supports:
- Python → JavaScript ✅
- JavaScript → Python ✅
- Python → TypeScript 🚧

Easy to add more by updating `prompts.py`.

## Configuration

Edit `.env` file:

```env
# Choose your LLM provider
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Model selection
DEFAULT_MODEL=gpt-3.5-turbo

# Conversion settings
MAX_TOKENS=2000
TEMPERATURE=0.1
```

## Limitations

This is a minimal prototype with:
- Single file conversion only
- No dependency resolution
- No cross-file context
- Basic error handling
- Manual review recommended

## Next Steps for Scaling

To handle larger codebases (1000+ files):

1. **Chunking System**: Process files in small batches
2. **Symbol Cache**: Track converted names for consistency
3. **Parallel Processing**: Convert multiple files simultaneously
4. **Context Extraction**: Minimal context without full loading
5. **Streaming Pipeline**: Start seeing results immediately

## Troubleshooting

**API Key Issues:**
```bash
# Check if .env file exists and has keys
cat .env | grep API_KEY
```

**Installation Issues:**
```bash
# Use specific versions if conflicts occur
pip install langchain==0.3.14 langchain-openai==0.2.14
```

**Token Limit Exceeded:**
- Reduce `MAX_TOKENS` in .env
- Split large files into smaller chunks
- Use GPT-3.5 for simple conversions

## Development

Run tests:
```bash
python test_converter.py
```

Add new language support:
1. Edit `src/prompts.py`
2. Add examples to `PYTHON_TO_X_EXAMPLES`
3. Update `CONVERSION_RULES` dictionary
4. Test with sample files

## License

MIT

---

Built as a prototype for efficient, token-conscious code conversion using LangChain.