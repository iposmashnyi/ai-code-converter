#!/usr/bin/env python
"""
AI Code Converter - Multi-File Project Conversion CLI

Convert entire codebases (up to 25 files) between programming languages.
Maintains consistency across files using symbol caching.
"""

import argparse
import sys
import os
from pathlib import Path
from colorama import init, Fore, Style

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.multi_file_converter import MultiFileConverter
from src.file_discovery import FileDiscovery

init(autoreset=True)


def print_banner():
    """Print the application banner."""
    print(f"{Fore.CYAN}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║            AI Code Converter - Project Mode                  ║")
    print("║         Convert entire projects between languages            ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}\n")


def list_supported_languages():
    """List all supported languages."""
    languages = {
        "Python": "python, py",
        "JavaScript": "javascript, js",
        "TypeScript": "typescript, ts",
        "Java": "java",
        "Go": "go, golang",
        "Rust": "rust, rs",
        "C#": "csharp, cs",
        "Ruby": "ruby, rb",
        "PHP": "php",
        "Swift": "swift",
        "Kotlin": "kotlin, kt"
    }

    print(f"{Fore.CYAN}Supported Languages:{Style.RESET_ALL}")
    for lang, aliases in languages.items():
        print(f"  • {lang}: {aliases}")
    print()


def analyze_project(source_dir: str, source_lang: str, max_files: int = 25):
    """
    Analyze a project without converting.

    Args:
        source_dir: Source directory path
        source_lang: Source language
        max_files: Maximum files to analyze
    """
    print(f"{Fore.CYAN}Analyzing project: {source_dir}{Style.RESET_ALL}\n")

    discovery = FileDiscovery(source_lang)
    files = discovery.discover_files(source_dir, max_files)

    if not files:
        print(f"{Fore.RED}No {source_lang} files found!{Style.RESET_ALL}")
        return

    print(discovery.generate_summary(files))

    # Show file list
    print(f"\n{Fore.CYAN}Files to be converted:{Style.RESET_ALL}")
    for i, file_info in enumerate(files, 1):
        size_kb = file_info["size"] / 1024
        print(f"  {i:2d}. {file_info['relative_path']} "
              f"({file_info['lines']} lines, {size_kb:.1f} KB)")

    # Rough cost estimate
    total_lines = sum(f.get("lines", 0) for f in files)
    estimated_tokens = total_lines * 20  # Rough estimate
    gpt35_cost = (estimated_tokens / 1000) * 0.002
    gpt4_cost = (estimated_tokens / 1000) * 0.03

    print(f"\n{Fore.YELLOW}Rough Cost Estimate:{Style.RESET_ALL}")
    print(f"  GPT-3.5-turbo: ~${gpt35_cost:.2f}")
    print(f"  GPT-4: ~${gpt4_cost:.2f}")
    print(f"  Estimated tokens: ~{estimated_tokens:,}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert entire projects between programming languages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a Python project to JavaScript
  python convert_project.py ./my_python_app ./output_js --from python --to javascript

  # Dry run to estimate cost
  python convert_project.py ./my_app ./output --dry-run

  # Resume interrupted conversion
  python convert_project.py ./my_app ./output --resume ./output/.conversion_state.json

  # Convert with specific model
  python convert_project.py ./my_app ./output --model gpt-4

  # Exclude directories
  python convert_project.py ./my_app ./output --exclude-dir tests --exclude-dir docs
        """
    )

    # Positional arguments
    parser.add_argument(
        "source",
        nargs="?",
        help="Source directory containing code to convert"
    )
    parser.add_argument(
        "output",
        nargs="?",
        help="Output directory for converted code"
    )

    # Language options
    parser.add_argument(
        "--from", "--from-lang", "-f",
        dest="from_lang",
        default="python",
        help="Source language (default: python)"
    )
    parser.add_argument(
        "--to", "--to-lang", "-t",
        dest="to_lang",
        default="javascript",
        help="Target language (default: javascript)"
    )

    # Model options
    parser.add_argument(
        "--model", "-m",
        help="LLM model to use (e.g., gpt-3.5-turbo, gpt-4, claude-3-sonnet)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Generation temperature (0.0-1.0, default: 0.1)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2000,
        help="Max tokens per response (default: 2000)"
    )

    # File options
    parser.add_argument(
        "--max-files",
        type=int,
        default=25,
        help="Maximum files to convert (default: 25)"
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test files in conversion"
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        dest="exclude_dirs",
        help="Exclude directory (can be used multiple times)"
    )
    parser.add_argument(
        "--exclude-pattern",
        action="append",
        dest="exclude_patterns",
        help="Exclude file pattern (can be used multiple times)"
    )

    # Execution options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and estimate cost without converting"
    )
    parser.add_argument(
        "--resume",
        help="Resume from saved state file"
    )
    parser.add_argument(
        "--no-continue",
        action="store_true",
        help="Stop on first error instead of continuing"
    )

    # Info options
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List supported languages"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze project without converting"
    )

    args = parser.parse_args()

    # Handle info commands
    if args.list_languages:
        list_supported_languages()
        return 0

    # Check required arguments
    if not args.source:
        print_banner()
        parser.print_help()
        return 1

    # Analyze mode
    if args.analyze:
        analyze_project(args.source, args.from_lang, args.max_files)
        return 0

    # Check output directory for conversion
    if not args.output and not args.dry_run:
        print(f"{Fore.RED}Error: Output directory required for conversion{Style.RESET_ALL}")
        print("Use --dry-run to estimate cost without converting")
        return 1

    # Print banner
    print_banner()

    # Validate source directory
    if not Path(args.source).exists():
        print(f"{Fore.RED}Error: Source directory does not exist: {args.source}{Style.RESET_ALL}")
        return 1

    # Check for .env file
    if not os.path.exists(".env"):
        print(f"{Fore.YELLOW}Warning: .env file not found!{Style.RESET_ALL}")
        print("Please ensure your API keys are set in environment variables or .env file")
        print("Example .env file:")
        print("  OPENAI_API_KEY=sk-...")
        print("  ANTHROPIC_API_KEY=sk-ant-...")
        response = input(f"\n{Fore.YELLOW}Continue anyway? (y/n): {Style.RESET_ALL}")
        if response.lower() != 'y':
            return 1

    try:
        # Create converter
        print(f"Initializing converter...")
        print(f"  Source language: {args.from_lang}")
        print(f"  Target language: {args.to_lang}")
        print(f"  Model: {args.model or 'default'}")
        print()

        converter = MultiFileConverter(
            source_lang=args.from_lang,
            target_lang=args.to_lang,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens
        )

        # Set error handling mode
        converter.continue_on_error = not args.no_continue

        # Run conversion
        results = converter.convert_project(
            source_dir=args.source,
            output_dir=args.output or "./output",
            max_files=args.max_files,
            resume_from=args.resume,
            exclude_dirs=args.exclude_dirs,
            exclude_patterns=args.exclude_patterns,
            include_tests=args.include_tests,
            dry_run=args.dry_run
        )

        # Check results
        if results.get("success"):
            if not args.dry_run:
                print(f"\n{Fore.GREEN}✅ Conversion completed successfully!{Style.RESET_ALL}")
                print(f"Output saved to: {args.output}")

                if results.get("files_failed", 0) > 0:
                    print(f"\n{Fore.YELLOW}Note: {results['files_failed']} files failed.{Style.RESET_ALL}")
                    print(f"Check {args.output}/failed_files.txt for details")
            return 0
        else:
            print(f"\n{Fore.RED}❌ Conversion failed: {results.get('error', 'Unknown error')}{Style.RESET_ALL}")
            return 1

    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Conversion interrupted by user{Style.RESET_ALL}")
        print("You can resume using: --resume .conversion_state.json")
        return 130

    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        import traceback
        if os.getenv("DEBUG"):
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())