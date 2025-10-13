# AI Code Converter

LangChain-based code converter for transforming codebases between programming languages using LLMs (GPT-4, Claude). Optimized for token efficiency and consistency across multi-file projects.

## Features

- **Single & Multi-File Conversion**: Handles individual files or projects up to 25 files
- **Token-Efficient Processing**: File-by-file conversion to avoid context explosion
- **Symbol Cache**: Maintains naming consistency (e.g., snake_case → camelCase)
- **Progress Tracking & Resume**: Checkpoint-based recovery for interrupted conversions
- **Smart File Discovery**: Respects .gitignore patterns
- **Multi-LLM Support**: OpenAI GPT-4/GPT-3.5, Anthropic Claude

## Installation

```bash
git clone https://github.com/yourusername/ai-code-converter.git
cd ai-code-converter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
```

## Configuration

`.env` file:
```env
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-api03-...
DEFAULT_MODEL=gpt-4
MAX_TOKENS=4000
TEMPERATURE=0.1
```

## Usage

### Single File
```bash
python single_file_converter.py input.py \
  --from-lang python \
  --to-lang javascript \
  --output output.js
```

### Multi-File Project
```bash
python convert_project.py \
  --source ./my-python-project \
  --output ./my-js-project \
  --source-lang python \
  --target-lang javascript \
  --model gpt-4 \
  --max-files 25
```

### Resume Interrupted Conversion
```bash
python convert_project.py \
  --source ./my-python-project \
  --output ./my-js-project \
  --resume
```

## Project Structure

```
ai-code-converter/
├── src/
│   ├── single_file_converter.py  # Single file logic
│   ├── multi_file_converter.py   # Multi-file orchestration
│   ├── file_discovery.py         # File detection
│   ├── symbol_cache.py           # Naming consistency
│   ├── progress_tracker.py       # Checkpoint management
│   └── prompts.py                # LangChain templates
├── convert_project.py            # Multi-file CLI
├── single_file_converter.py      # Single file CLI
├── requirements.txt
└── .env.example
```

## Python API

```python
from src.multi_file_converter import MultiFileConverter

converter = MultiFileConverter(
    source_lang="python",
    target_lang="javascript",
    model="gpt-4",
    max_tokens=4000
)

result = converter.convert_project(
    source_dir="./src",
    output_dir="./dist",
    max_files=25
)
```

## CLI Options

```bash
convert_project.py:
  --source PATH         Source directory
  --output PATH         Output directory
  --source-lang LANG    python|javascript|typescript
  --target-lang LANG    python|javascript|typescript
  --model MODEL         gpt-4|gpt-3.5-turbo|claude-3-sonnet-20240229
  --max-tokens INT      Max tokens per request (default: 4000)
  --max-files INT       Max files to convert (default: 25)
  --temperature FLOAT   Model temperature (default: 0.1)
  --resume             Resume from checkpoint
  --verbose            Detailed output
```

## Token Management

- Processes files individually (~2-3K tokens per 100 lines)
- Symbol cache for cross-file consistency
- No full codebase context loading

## Limitations

- Max 25 files per run (configurable)
- No cross-file type inference
- Binary files skipped
- Generated code requires review

## Troubleshooting

```bash
# Check API keys
python -c "import os; print('Keys configured:', bool(os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')))"

# Token limit issues
python convert_project.py --max-tokens 2000

# Resume after failure
python convert_project.py --resume

# Version conflicts
pip install langchain==0.3.14 langchain-openai==0.2.14
```

## Requirements

See `requirements.txt`:
- langchain==0.3.14
- langchain-openai==0.2.14
- langchain-anthropic==0.3.0
- python-dotenv==1.0.1
- tiktoken==0.8.0
- colorama==0.4.6

## License

MIT