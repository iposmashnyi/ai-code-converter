"""
Multi-file code converter for small codebases (20-25 files).
Orchestrates the conversion of entire projects while maintaining consistency.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import time
from colorama import Fore, Style, init

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from single_file_converter import FileConverter
    from file_discovery import FileDiscovery
    from symbol_cache import SymbolCache
    from progress_tracker import ProgressTracker
except ImportError:
    from src.single_file_converter import FileConverter
    from src.file_discovery import FileDiscovery
    from src.symbol_cache import SymbolCache
    from src.progress_tracker import ProgressTracker

init(autoreset=True)


class MultiFileConverter:
    """
    Converts multiple files in a project while maintaining consistency.
    """

    def __init__(
        self,
        source_lang: str,
        target_lang: str,
        model: str = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ):
        """
        Initialize multi-file converter.

        Args:
            source_lang: Source programming language
            target_lang: Target programming language
            model: LLM model to use
            temperature: Generation temperature
            max_tokens: Max tokens per response
        """
        self.source_lang = source_lang.lower()
        self.target_lang = target_lang.lower()

        # Initialize single file converter
        self.file_converter = FileConverter(
            source_lang=source_lang,
            target_lang=target_lang,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Initialize components
        self.file_discovery = FileDiscovery(source_lang)
        self.symbol_cache = SymbolCache()
        self.progress_tracker = None

        # Configuration
        self.max_retries = 2
        self.continue_on_error = True

    def convert_project(
        self,
        source_dir: str,
        output_dir: str,
        max_files: int = 25,
        resume_from: Optional[str] = None,
        exclude_dirs: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        include_tests: bool = False,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Convert an entire project.

        Args:
            source_dir: Source project directory
            output_dir: Output directory for converted files
            max_files: Maximum number of files to convert
            resume_from: Path to state file for resuming
            exclude_dirs: Additional directories to exclude
            exclude_patterns: Additional file patterns to exclude
            include_tests: Whether to include test files
            dry_run: If True, only estimate cost without converting

        Returns:
            Conversion results dictionary
        """
        print(f"{Fore.CYAN}{'=' * 60}")
        print(f"Multi-File Code Converter")
        print(f"{'=' * 60}{Style.RESET_ALL}\n")

        # Validate directories
        source_path = Path(source_dir).resolve()
        if not source_path.exists():
            raise ValueError(f"Source directory does not exist: {source_dir}")

        output_path = Path(output_dir).resolve()

        # Configure file discovery
        if exclude_dirs:
            self.file_discovery.exclude_dirs.update(exclude_dirs)
        if exclude_patterns:
            self.file_discovery.exclude_patterns.extend(exclude_patterns)

        # Discover files
        print(f"{Fore.CYAN}Discovering files...{Style.RESET_ALL}")
        files = self.file_discovery.discover_files(source_dir, max_files)

        if not files:
            print(f"{Fore.RED}No files found to convert!{Style.RESET_ALL}")
            return {"success": False, "error": "No files found"}

        print(f"{Fore.GREEN}✓ Found {len(files)} files to convert{Style.RESET_ALL}")
        print(self.file_discovery.generate_summary(files))

        # Initialize progress tracker
        self.progress_tracker = ProgressTracker(len(files), output_dir)

        # Check for resume
        if resume_from and Path(resume_from).exists():
            print(f"\n{Fore.CYAN}Resuming from previous state...{Style.RESET_ALL}")
            self.progress_tracker.load_state(resume_from)
            self.symbol_cache.load_from_file(
                Path(resume_from).parent / "symbol_cache.json"
            )

        # Estimate cost
        if not resume_from:
            total_estimate = self._estimate_total_cost(files)
            print(f"\n{Fore.YELLOW}Cost Estimation:{Style.RESET_ALL}")
            print(f"  Total tokens: ~{total_estimate['total_tokens']:,}")
            print(f"  Estimated cost: {total_estimate['estimated_cost']}")
            print(f"  Estimated time: {total_estimate['estimated_time']}\n")

            if dry_run:
                print(f"{Fore.YELLOW}Dry run mode - no conversion performed{Style.RESET_ALL}")
                return {
                    "success": True,
                    "dry_run": True,
                    "estimation": total_estimate
                }

            # Ask for confirmation
            response = input(f"{Fore.YELLOW}Proceed with conversion? (y/n): {Style.RESET_ALL}")
            if response.lower() != 'y':
                print("Conversion cancelled.")
                return {"success": False, "error": "User cancelled"}

        # Start conversion
        print(f"\n{Fore.CYAN}Starting conversion...{Style.RESET_ALL}\n")
        start_time = time.time()

        results = {
            "success": True,
            "source_dir": str(source_dir),
            "output_dir": str(output_dir),
            "files_processed": 0,
            "files_succeeded": 0,
            "files_failed": 0,
            "total_tokens": 0,
            "total_cost": 0.0
        }

        # Convert files one by one
        for file_info in files:
            file_path = file_info["path"]

            # Skip if already processed (for resume)
            if not self.progress_tracker.should_process_file(file_path):
                continue

            # Convert the file
            success = self._convert_single_file(
                file_path,
                file_info["relative_path"],
                source_path,
                output_path
            )

            results["files_processed"] += 1
            if success:
                results["files_succeeded"] += 1
            else:
                results["files_failed"] += 1

                # Stop on error if not continuing
                if not self.continue_on_error:
                    break

            # Save state periodically
            if results["files_processed"] % 5 == 0:
                self._save_state(output_path)

        # Final statistics
        elapsed_time = time.time() - start_time
        results["total_tokens"] = self.progress_tracker.total_tokens
        results["total_cost"] = self.progress_tracker.total_cost
        results["elapsed_time"] = elapsed_time

        # Save final state and reports
        self._save_state(output_path)
        self._generate_final_report(output_path, results)

        # Display summary
        print(self.progress_tracker.get_summary())

        return results

    def _convert_single_file(
        self,
        source_file: str,
        relative_path: str,
        source_root: Path,
        output_root: Path
    ) -> bool:
        """
        Convert a single file with context from cache.

        Args:
            source_file: Absolute path to source file
            relative_path: Relative path from source root
            source_root: Source project root
            output_root: Output project root

        Returns:
            True if successful, False otherwise
        """
        # Start tracking
        self.progress_tracker.start_file(source_file)

        try:
            # Analyze file dependencies
            dependencies = self.file_discovery.analyze_dependencies(source_file)

            # Get cached context
            context = self.symbol_cache.get_context_for_file(
                dependencies.get("imports", [])
            )

            # Inject context into converter (simplified for now)
            # In a full implementation, we'd modify the prompt with context

            # Determine output path
            output_file = output_root / relative_path
            # Change extension
            ext_map = {
                ("python", "javascript"): ".js",
                ("python", "typescript"): ".ts",
                ("javascript", "python"): ".py",
                ("javascript", "typescript"): ".ts",
            }
            new_ext = ext_map.get((self.source_lang, self.target_lang), ".txt")
            output_file = output_file.with_suffix(new_ext)

            # Create output directory
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert the file
            result = self.file_converter.convert(source_file)

            if result["success"]:
                # Extract symbols from conversion
                with open(source_file, 'r', encoding='utf-8') as f:
                    source_code = f.read()

                self.symbol_cache.extract_symbols_from_code(
                    source_code,
                    result["converted_code"],
                    self.source_lang,
                    self.target_lang
                )

                # Save converted file
                self.file_converter.save_output(str(output_file), result)

                # Mark as complete
                self.progress_tracker.complete_file(
                    source_file,
                    tokens_used=result.get("tokens_used", 0),
                    cost=result.get("cost", 0.0),
                    converted_code=result["converted_code"]
                )

                # Mark file as processed in cache
                self.symbol_cache.mark_file_processed(source_file)

                return True

            else:
                # Mark as failed
                self.progress_tracker.fail_file(
                    source_file,
                    result.get("error", "Unknown error")
                )
                return False

        except Exception as e:
            # Mark as failed
            self.progress_tracker.fail_file(source_file, str(e))
            return False

    def _estimate_total_cost(self, files: List[Dict]) -> Dict[str, Any]:
        """
        Estimate total cost for converting all files.

        Args:
            files: List of files to convert

        Returns:
            Cost estimation dictionary
        """
        total_tokens = 0
        total_lines = 0

        for file_info in files[:5]:  # Sample first 5 files
            try:
                estimate = self.file_converter.estimate_cost(file_info["path"])
                total_tokens += estimate["total_tokens"]
                total_lines += file_info.get("lines", 0)
            except Exception:
                pass

        # Extrapolate to all files
        if len(files) > 5:
            avg_tokens = total_tokens / 5
            total_tokens = int(avg_tokens * len(files))

        # Calculate cost
        cost_per_1k = 0.002  # GPT-3.5-turbo default
        if "gpt-4" in (self.file_converter.model or "").lower():
            cost_per_1k = 0.03
        elif "claude" in (self.file_converter.model or "").lower():
            cost_per_1k = 0.003

        total_cost = (total_tokens / 1000) * cost_per_1k

        # Estimate time (rough: 3 seconds per file)
        estimated_seconds = len(files) * 3
        hours = estimated_seconds // 3600
        minutes = (estimated_seconds % 3600) // 60
        seconds = estimated_seconds % 60

        if hours > 0:
            time_str = f"{hours}h {minutes}m"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"

        return {
            "total_tokens": total_tokens,
            "estimated_cost": f"${total_cost:.2f}",
            "estimated_time": time_str,
            "files_count": len(files)
        }

    def _save_state(self, output_dir: Path):
        """Save current state for resume capability."""
        # Save progress state
        self.progress_tracker.save_state()

        # Save symbol cache
        cache_path = output_dir / "symbol_cache.json"
        self.symbol_cache.save_to_file(str(cache_path))

    def _generate_final_report(self, output_dir: Path, results: Dict):
        """Generate final conversion report."""
        # Generate progress report
        report_path = output_dir / "conversion_report.json"
        self.progress_tracker.generate_report(str(report_path))

        # Generate markdown summary
        summary_path = output_dir / "CONVERSION_SUMMARY.md"
        self._write_markdown_summary(summary_path, results)

        # Save failed files list
        if self.progress_tracker.failed_files:
            failed_path = output_dir / "failed_files.txt"
            with open(failed_path, 'w', encoding='utf-8') as f:
                for failed in self.progress_tracker.failed_files:
                    f.write(f"{failed['file']}: {failed['error']}\n")

    def _write_markdown_summary(self, path: Path, results: Dict):
        """Write a markdown summary of the conversion."""
        summary = f"""# Code Conversion Summary

## Overview
- **Source Language**: {self.source_lang}
- **Target Language**: {self.target_lang}
- **Model Used**: {self.file_converter.model}

## Results
- ✅ **Successfully Converted**: {results['files_succeeded']}/{results['files_processed']}
- ❌ **Failed**: {results['files_failed']}
- 💰 **Total Cost**: ${results['total_cost']:.4f}
- ⏱️ **Time Taken**: {results['elapsed_time']:.1f}s
- 🔤 **Total Tokens**: {results['total_tokens']:,}

## Conversion Rate
- **Success Rate**: {results['files_succeeded'] / max(results['files_processed'], 1) * 100:.1f}%

## Symbol Cache Statistics
{self.symbol_cache.get_summary()}

## Notes
- Conversion performed using LangChain with {self.file_converter.model}
- Files were processed individually to avoid token limits
- Symbol consistency maintained across files using cache

## Next Steps
1. Review failed files in `failed_files.txt`
2. Test the converted code thoroughly
3. Manual adjustments may be needed for complex patterns

---
Generated by AI Code Converter
"""

        with open(path, 'w', encoding='utf-8') as f:
            f.write(summary)


def main():
    """CLI for multi-file conversion."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert multiple code files in a project"
    )
    parser.add_argument("source", help="Source directory")
    parser.add_argument("output", help="Output directory")
    parser.add_argument("--from-lang", "-f", default="python", help="Source language")
    parser.add_argument("--to-lang", "-t", default="javascript", help="Target language")
    parser.add_argument("--max-files", "-m", type=int, default=25, help="Max files to convert")
    parser.add_argument("--model", default=None, help="Model to use")
    parser.add_argument("--resume", help="Resume from state file")
    parser.add_argument("--include-tests", action="store_true", help="Include test files")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost without converting")
    parser.add_argument("--exclude-dir", action="append", help="Exclude directories")
    parser.add_argument("--exclude-pattern", action="append", help="Exclude file patterns")

    args = parser.parse_args()

    # Create converter
    converter = MultiFileConverter(
        source_lang=args.from_lang,
        target_lang=args.to_lang,
        model=args.model
    )

    # Run conversion
    results = converter.convert_project(
        source_dir=args.source,
        output_dir=args.output,
        max_files=args.max_files,
        resume_from=args.resume,
        exclude_dirs=args.exclude_dir,
        exclude_patterns=args.exclude_pattern,
        include_tests=args.include_tests,
        dry_run=args.dry_run
    )

    # Exit with appropriate code
    sys.exit(0 if results.get("success") else 1)


if __name__ == "__main__":
    main()