"""
Progress tracking for multi-file code conversion.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from colorama import Fore, Style, init

init(autoreset=True)


class ProgressTracker:
    """
    Tracks progress of multi-file conversion with resume capability.
    """

    def __init__(self, total_files: int, output_dir: str = None):
        """
        Initialize progress tracker.

        Args:
            total_files: Total number of files to convert
            output_dir: Directory for saving state (optional)
        """
        self.total_files = total_files
        self.output_dir = output_dir

        # Progress tracking
        self.completed_files: List[str] = []
        self.failed_files: List[Dict] = []
        self.skipped_files: List[str] = []
        self.current_file: Optional[str] = None

        # Timing
        self.start_time = time.time()
        self.file_start_time = None

        # Token and cost tracking
        self.total_tokens = 0
        self.total_cost = 0.0
        self.tokens_per_file: Dict[str, int] = {}
        self.cost_per_file: Dict[str, float] = {}

        # State file for resume
        self.state_file = None
        if output_dir:
            self.state_file = Path(output_dir) / ".conversion_state.json"

        # Statistics
        self.stats = {
            "average_tokens_per_file": 0,
            "average_time_per_file": 0,
            "estimated_total_cost": 0,
            "estimated_time_remaining": 0
        }

    def start_file(self, file_path: str):
        """
        Mark the start of processing a file.

        Args:
            file_path: Path of the file being processed
        """
        self.current_file = file_path
        self.file_start_time = time.time()
        self._display_progress()

    def complete_file(
        self,
        file_path: str,
        tokens_used: int = 0,
        cost: float = 0.0,
        converted_code: str = None
    ):
        """
        Mark a file as successfully completed.

        Args:
            file_path: Path of the completed file
            tokens_used: Tokens used for this file
            cost: Cost for this file
            converted_code: The converted code (for analysis)
        """
        self.completed_files.append(file_path)
        self.current_file = None

        # Track tokens and cost
        if tokens_used:
            self.tokens_per_file[file_path] = tokens_used
            self.total_tokens += tokens_used
        if cost:
            self.cost_per_file[file_path] = cost
            self.total_cost += cost

        # Update statistics
        self._update_statistics()

        # Display progress
        self._display_progress(success=True, file_path=file_path)

        # Save state periodically (every 5 files)
        if len(self.completed_files) % 5 == 0:
            self.save_state()

    def fail_file(self, file_path: str, error: str):
        """
        Mark a file as failed.

        Args:
            file_path: Path of the failed file
            error: Error message
        """
        self.failed_files.append({
            "file": file_path,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        self.current_file = None

        # Display progress
        self._display_progress(success=False, file_path=file_path, error=error)

        # Save state
        self.save_state()

    def skip_file(self, file_path: str, reason: str = ""):
        """
        Mark a file as skipped.

        Args:
            file_path: Path of the skipped file
            reason: Reason for skipping
        """
        self.skipped_files.append(file_path)
        print(f"{Fore.YELLOW}⚠ Skipped: {Path(file_path).name} - {reason}{Style.RESET_ALL}")

    def _display_progress(
        self,
        success: Optional[bool] = None,
        file_path: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Display progress bar and status."""

        # Calculate progress
        processed = len(self.completed_files) + len(self.failed_files)
        percentage = (processed / self.total_files) * 100 if self.total_files > 0 else 0

        # Create progress bar
        bar_length = 30
        filled_length = int(bar_length * processed // self.total_files)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)

        # Status indicator
        if success is True:
            status = f"{Fore.GREEN}✓{Style.RESET_ALL}"
            file_name = Path(file_path).name if file_path else ""
            status_text = f"{status} {file_name}"
        elif success is False:
            status = f"{Fore.RED}✗{Style.RESET_ALL}"
            file_name = Path(file_path).name if file_path else ""
            status_text = f"{status} {file_name}"
            if error:
                status_text += f" - {Fore.RED}{error[:50]}{Style.RESET_ALL}"
        else:
            status_text = f"Processing: {Path(self.current_file).name if self.current_file else '...'}"

        # Calculate ETA
        if processed > 0:
            elapsed = time.time() - self.start_time
            avg_time = elapsed / processed
            remaining = (self.total_files - processed) * avg_time
            eta = str(timedelta(seconds=int(remaining)))
        else:
            eta = "calculating..."

        # Print progress
        print(f"\r[{bar}] {percentage:.1f}% ({processed}/{self.total_files}) | "
              f"ETA: {eta} | {status_text}", end='', flush=True)

        # New line after status messages
        if success is not None:
            print()  # New line after completion/failure

    def _update_statistics(self):
        """Update running statistics."""
        processed = len(self.completed_files)

        if processed > 0:
            # Average tokens per file
            if self.tokens_per_file:
                self.stats["average_tokens_per_file"] = (
                    sum(self.tokens_per_file.values()) / len(self.tokens_per_file)
                )

            # Average time per file
            elapsed = time.time() - self.start_time
            self.stats["average_time_per_file"] = elapsed / processed

            # Estimated total cost
            avg_cost = self.total_cost / processed
            self.stats["estimated_total_cost"] = avg_cost * self.total_files

            # Estimated time remaining
            remaining_files = self.total_files - processed - len(self.failed_files)
            self.stats["estimated_time_remaining"] = (
                remaining_files * self.stats["average_time_per_file"]
            )

    def save_state(self):
        """Save current state to file for resume capability."""
        if not self.state_file:
            return

        state = {
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "failed_files": self.failed_files,
            "skipped_files": self.skipped_files,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "tokens_per_file": self.tokens_per_file,
            "cost_per_file": self.cost_per_file,
            "start_time": self.start_time,
            "stats": self.stats,
            "timestamp": datetime.now().isoformat()
        }

        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not save state: {e}{Style.RESET_ALL}")

    def load_state(self, state_file: str) -> bool:
        """
        Load state from file to resume conversion.

        Args:
            state_file: Path to state file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.total_files = state["total_files"]
            self.completed_files = state["completed_files"]
            self.failed_files = state["failed_files"]
            self.skipped_files = state.get("skipped_files", [])
            self.total_tokens = state["total_tokens"]
            self.total_cost = state["total_cost"]
            self.tokens_per_file = state["tokens_per_file"]
            self.cost_per_file = state["cost_per_file"]
            self.start_time = state["start_time"]
            self.stats = state["stats"]

            print(f"{Fore.GREEN}Resumed from previous state:{Style.RESET_ALL}")
            print(f"  - {len(self.completed_files)} files completed")
            print(f"  - {len(self.failed_files)} files failed")
            print(f"  - ${self.total_cost:.4f} spent so far")

            return True

        except Exception as e:
            print(f"{Fore.RED}Could not load state: {e}{Style.RESET_ALL}")
            return False

    def should_process_file(self, file_path: str) -> bool:
        """
        Check if a file should be processed (not already done).

        Args:
            file_path: Path to check

        Returns:
            True if file should be processed
        """
        return (
            file_path not in self.completed_files
            and file_path not in [f["file"] for f in self.failed_files]
            and file_path not in self.skipped_files
        )

    def get_summary(self) -> str:
        """Get a summary of the conversion progress."""
        elapsed = time.time() - self.start_time
        elapsed_str = str(timedelta(seconds=int(elapsed)))

        successful_rate = (
            len(self.completed_files) / self.total_files * 100
            if self.total_files > 0 else 0
        )

        summary = f"""
{Fore.CYAN}{'=' * 50}
Conversion Summary
{'=' * 50}{Style.RESET_ALL}

Files:
  {Fore.GREEN}✓ Successfully converted: {len(self.completed_files)}/{self.total_files} ({successful_rate:.1f}%){Style.RESET_ALL}
  {Fore.RED}✗ Failed: {len(self.failed_files)}{Style.RESET_ALL}
  {Fore.YELLOW}⚠ Skipped: {len(self.skipped_files)}{Style.RESET_ALL}

Resources:
  Total tokens used: {self.total_tokens:,}
  Total cost: ${self.total_cost:.4f}
  Average tokens/file: {int(self.stats['average_tokens_per_file'])}

Time:
  Total time: {elapsed_str}
  Average time/file: {self.stats['average_time_per_file']:.1f}s

"""

        if self.failed_files:
            summary += f"{Fore.RED}Failed Files:{Style.RESET_ALL}\n"
            for failed in self.failed_files[:5]:  # Show first 5
                summary += f"  - {Path(failed['file']).name}: {failed['error'][:50]}\n"
            if len(self.failed_files) > 5:
                summary += f"  ... and {len(self.failed_files) - 5} more\n"

        return summary

    def generate_report(self, output_path: str):
        """
        Generate a detailed conversion report.

        Args:
            output_path: Path to save the report
        """
        report = {
            "summary": {
                "total_files": self.total_files,
                "successful": len(self.completed_files),
                "failed": len(self.failed_files),
                "skipped": len(self.skipped_files),
                "success_rate": f"{len(self.completed_files) / max(self.total_files, 1) * 100:.1f}%"
            },
            "resources": {
                "total_tokens": self.total_tokens,
                "total_cost": f"${self.total_cost:.4f}",
                "average_tokens_per_file": int(self.stats['average_tokens_per_file']),
                "average_cost_per_file": f"${self.total_cost / max(len(self.completed_files), 1):.4f}"
            },
            "timing": {
                "total_time": str(timedelta(seconds=int(time.time() - self.start_time))),
                "average_time_per_file": f"{self.stats['average_time_per_file']:.1f}s"
            },
            "completed_files": self.completed_files,
            "failed_files": self.failed_files,
            "skipped_files": self.skipped_files,
            "token_usage": self.tokens_per_file,
            "cost_breakdown": self.cost_per_file
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"\n{Fore.GREEN}Detailed report saved to: {output_path}{Style.RESET_ALL}")

    def reset(self):
        """Reset the tracker for a new conversion."""
        self.completed_files = []
        self.failed_files = []
        self.skipped_files = []
        self.current_file = None
        self.start_time = time.time()
        self.file_start_time = None
        self.total_tokens = 0
        self.total_cost = 0.0
        self.tokens_per_file = {}
        self.cost_per_file = {}
        self.stats = {
            "average_tokens_per_file": 0,
            "average_time_per_file": 0,
            "estimated_total_cost": 0,
            "estimated_time_remaining": 0
        }