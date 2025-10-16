#!/usr/bin/env python
"""
AI Code Converter - LangGraph Edition

Simple CLI for converting codebases between programming languages
using Claude Sonnet 4 with intelligent file discovery and consistent conversions.
"""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent import CodeConverterAgent


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert codebases between programming languages using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert Python project to JavaScript
  python convert_project.py ./my_python_app ./output_js --from python --to javascript

  # Convert JavaScript to TypeScript
  python convert_project.py ./js_app ./ts_app --from javascript --to typescript

  # Resume interrupted conversion (use same thread-id)
  python convert_project.py ./my_app ./output --from python --to javascript --thread-id session-001

Notes:
  - Conversions are automatically checkpointed
  - Interrupt with Ctrl+C and resume with same --thread-id
  - The agent intelligently excludes tests, build artifacts, and dependencies
  - Consistency is maintained across all files via conversion context
        """
    )

    # Required arguments
    parser.add_argument(
        "source",
        help="Source directory containing code to convert"
    )
    parser.add_argument(
        "output",
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

    # Checkpointing
    parser.add_argument(
        "--thread-id",
        default="default",
        help="Thread ID for checkpointing (use same ID to resume)"
    )

    # Model selection
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Claude model to use (default: claude-sonnet-4-20250514)"
    )

    args = parser.parse_args()

    # Validate source directory
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"❌ Error: Source directory does not exist: {args.source}")
        return 1

    if not source_path.is_dir():
        print(f"❌ Error: Source path is not a directory: {args.source}")
        return 1

    # Print header
    print("\n" + "=" * 60)
    print("  AI Code Converter - LangGraph + Claude Sonnet 4")
    print("=" * 60)

    try:
        # Create agent
        print("\n🤖 Initializing agent...")
        agent = CodeConverterAgent(model=args.model)
        print(f"   Model: {args.model}")
        print(f"   Checkpointing: Enabled (thread-id: {args.thread_id})")

        # Run conversion
        final_state = agent.convert_project(
            source_dir=args.source,
            target_dir=args.output,
            source_lang=args.from_lang,
            target_lang=args.to_lang,
            thread_id=args.thread_id
        )

        # Check results
        if final_state["files_failed"] > 0:
            print(f"\n⚠️  Warning: {final_state['files_failed']} files failed to convert")
            print("   Check the error messages above for details")

        if final_state["files_completed"] == 0:
            print(f"\n❌ No files were successfully converted")
            return 1

        print(f"\n✅ Conversion complete!")
        print(f"   Output directory: {args.output}")

        # Show discovered patterns
        if final_state.get("conversion_context"):
            print(f"\n📋 Conversion patterns discovered:")
            for key, value in list(final_state["conversion_context"].items())[:10]:
                print(f"   {key}: {value}")
            if len(final_state["conversion_context"]) > 10:
                print(f"   ... and {len(final_state['conversion_context']) - 10} more")

        return 0

    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user")
        print(f"   To resume, run the same command with: --thread-id {args.thread_id}")
        return 130

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("   Make sure ANTHROPIC_API_KEY is set in your environment")
        return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
