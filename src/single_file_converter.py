"""
Single file code converter using LangChain
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import tiktoken

from langchain_community.callbacks.manager import get_openai_callback
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from colorama import init, Fore, Style

try:
    from prompts import get_conversion_prompt, get_conversion_rules
except ImportError:
    # Handle both module and script execution
    from src.prompts import get_conversion_prompt, get_conversion_rules

# Initialize colorama for colored output
init(autoreset=True)

# Load environment variables
load_dotenv()


class FileConverter:
    """Converts single code files between programming languages using LLMs."""

    def __init__(
        self,
        source_lang: str,
        target_lang: str,
        model: str = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ):
        """
        Initialize the file converter.

        Args:
            source_lang: Source programming language (e.g., 'python')
            target_lang: Target programming language (e.g., 'javascript')
            model: LLM model to use (defaults to env variable)
            temperature: LLM temperature for generation
            max_tokens: Maximum tokens for response
        """
        self.source_lang = source_lang.lower()
        self.target_lang = target_lang.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Get model from env if not specified
        if model is None:
            model = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        self.model = model

        # Initialize the LLM
        self.llm = self._initialize_llm(model)

        # Get conversion rules
        self.conversion_rules = get_conversion_rules(source_lang, target_lang)

        # Token counter for cost estimation
        self.total_tokens_used = 0
        self.total_cost = 0.0

    def _initialize_llm(self, model: str):
        """Initialize the appropriate LLM based on model name."""
        if "gpt" in model.lower():
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            return ChatOpenAI(
                model=model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=api_key
            )
        elif "claude" in model.lower():
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            return ChatAnthropic(
                model=model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=api_key
            )
        else:
            raise ValueError(f"Unsupported model: {model}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text for cost estimation."""
        try:
            encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            # Fallback to cl100k_base encoding
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))

    def estimate_cost(self, file_path: str) -> Dict[str, Any]:
        """
        Estimate the cost of converting a file.

        Args:
            file_path: Path to the source file

        Returns:
            Dictionary with token count and estimated cost
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        input_tokens = self.count_tokens(content)
        # Estimate output tokens (usually similar size to input)
        estimated_output_tokens = int(input_tokens * 1.2)
        total_tokens = input_tokens + estimated_output_tokens

        # Cost estimation (rough estimates)
        cost_per_1k = {
            "gpt-3.5-turbo": 0.002,
            "gpt-4": 0.03,
            "claude-3-opus": 0.015,
            "claude-3-sonnet": 0.003
        }

        model_key = self.model
        for key in cost_per_1k:
            if key in self.model.lower():
                model_key = key
                break

        cost = (total_tokens / 1000) * cost_per_1k.get(model_key, 0.002)

        return {
            "input_tokens": input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": f"${cost:.4f}"
        }

    def convert(self, file_path: str, use_few_shot: bool = True) -> Dict[str, Any]:
        """
        Convert a single code file.

        Args:
            file_path: Path to the source file
            use_few_shot: Whether to use few-shot examples

        Returns:
            Dictionary containing converted code and metadata
        """
        print(f"{Fore.CYAN}Converting {file_path}...{Style.RESET_ALL}")

        # Read source file
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        if not source_code.strip():
            return {
                "success": False,
                "error": "Source file is empty",
                "converted_code": ""
            }

        # Get appropriate prompt template
        prompt = get_conversion_prompt(self.source_lang, self.target_lang, use_few_shot)

        # Create chain using LCEL (LangChain Expression Language)
        chain = prompt | self.llm

        try:
            # Track token usage for OpenAI models
            if "gpt" in self.model.lower():
                with get_openai_callback() as cb:
                    # Run conversion
                    result = chain.invoke({
                        "source_lang": self.source_lang,
                        "target_lang": self.target_lang,
                        "source_code": source_code
                    })

                    # Update token tracking
                    self.total_tokens_used += cb.total_tokens
                    self.total_cost += cb.total_cost

                    print(f"{Fore.GREEN}✓ Conversion successful{Style.RESET_ALL}")
                    print(f"  Tokens used: {cb.total_tokens}")
                    print(f"  Cost: ${cb.total_cost:.4f}")
            else:
                # For non-OpenAI models, just run the conversion
                result = chain.invoke({
                    "source_lang": self.source_lang,
                    "target_lang": self.target_lang,
                    "source_code": source_code
                })
                print(f"{Fore.GREEN}✓ Conversion successful{Style.RESET_ALL}")

            # Extract the converted code from the AI message
            converted_code = result.content if hasattr(result, 'content') else str(result)

            # Clean up the response (remove markdown code blocks if present)
            if "```" in converted_code:
                # Extract code between backticks
                import re
                pattern = r"```(?:\w+)?\n?(.*?)```"
                matches = re.findall(pattern, converted_code, re.DOTALL)
                if matches:
                    converted_code = matches[0].strip()

            return {
                "success": True,
                "converted_code": converted_code,
                "source_file": file_path,
                "tokens_used": self.total_tokens_used,
                "cost": self.total_cost
            }

        except Exception as e:
            print(f"{Fore.RED}✗ Conversion failed: {str(e)}{Style.RESET_ALL}")
            return {
                "success": False,
                "error": str(e),
                "converted_code": ""
            }

    def save_output(self, output_path: str, result: Dict[str, Any]) -> bool:
        """
        Save the converted code to a file.

        Args:
            output_path: Path where to save the converted file
            result: Conversion result dictionary

        Returns:
            True if successful, False otherwise
        """
        if not result.get("success"):
            print(f"{Fore.RED}Cannot save: Conversion was not successful{Style.RESET_ALL}")
            return False

        try:
            # Create output directory if it doesn't exist
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save the converted code
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result["converted_code"])

            print(f"{Fore.GREEN}✓ Saved to {output_path}{Style.RESET_ALL}")
            return True

        except Exception as e:
            print(f"{Fore.RED}✗ Failed to save: {str(e)}{Style.RESET_ALL}")
            return False

    def convert_and_save(
        self,
        source_path: str,
        output_path: str,
        use_few_shot: bool = True
    ) -> Dict[str, Any]:
        """
        Convert a file and save the output in one operation.

        Args:
            source_path: Path to source file
            output_path: Path to save converted file
            use_few_shot: Whether to use few-shot examples

        Returns:
            Conversion result dictionary
        """
        # First estimate cost
        estimate = self.estimate_cost(source_path)
        print(f"{Fore.YELLOW}Estimated tokens: {estimate['total_tokens']}")
        print(f"Estimated cost: {estimate['estimated_cost']}{Style.RESET_ALL}")

        # Convert the file
        result = self.convert(source_path, use_few_shot)

        # Save if successful
        if result.get("success"):
            self.save_output(output_path, result)

        return result


def main():
    """Simple CLI for testing the converter."""
    import argparse

    parser = argparse.ArgumentParser(description="Convert code files between languages")
    parser.add_argument("source", help="Source file path")
    parser.add_argument("--output", "-o", help="Output file path", default=None)
    parser.add_argument("--from-lang", "-f", help="Source language", default="python")
    parser.add_argument("--to-lang", "-t", help="Target language", default="javascript")
    parser.add_argument("--model", "-m", help="Model to use", default=None)
    parser.add_argument("--no-few-shot", action="store_true", help="Disable few-shot examples")

    args = parser.parse_args()

    # Determine output path
    if args.output is None:
        source_path = Path(args.source)
        # Map common file extensions
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs"
        }
        new_ext = ext_map.get(args.to_lang.lower(), ".txt")
        output_path = source_path.with_suffix(new_ext)
        # Put in output directory
        output_path = Path("examples/output") / output_path.name
    else:
        output_path = args.output

    # Create converter
    converter = FileConverter(
        source_lang=args.from_lang,
        target_lang=args.to_lang,
        model=args.model
    )

    # Convert and save
    result = converter.convert_and_save(
        source_path=args.source,
        output_path=str(output_path),
        use_few_shot=not args.no_few_shot
    )

    # Print summary
    if result.get("success"):
        print(f"\n{Fore.GREEN}Conversion completed successfully!{Style.RESET_ALL}")
        if "gpt" in (converter.model or "").lower():
            print(f"Total tokens used: {result.get('tokens_used', 'N/A')}")
            print(f"Total cost: ${result.get('cost', 0):.4f}")
    else:
        print(f"\n{Fore.RED}Conversion failed: {result.get('error', 'Unknown error')}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()