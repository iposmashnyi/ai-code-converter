#!/usr/bin/env python
"""
Test script for the AI Code Converter.
This script demonstrates the basic usage of the single file converter.
"""

import sys
import os
from pathlib import Path
from colorama import init, Fore, Style

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.single_file_converter import FileConverter

# Initialize colorama
init(autoreset=True)


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}{Style.RESET_ALL}\n")


def test_basic_conversion():
    """Test basic Python to JavaScript conversion."""
    print_header("Testing Python to JavaScript Conversion")

    # Check if .env file exists
    if not os.path.exists(".env"):
        print(f"{Fore.YELLOW}Warning: .env file not found!")
        print(f"Creating .env from .env.example...")
        print(f"Please add your API keys to the .env file{Style.RESET_ALL}")

        # Copy .env.example to .env
        if os.path.exists(".env.example"):
            import shutil
            shutil.copy(".env.example", ".env")
            print(f"{Fore.GREEN}Created .env file. Please add your API keys before running.{Style.RESET_ALL}")
            return False
        else:
            print(f"{Fore.RED}Error: .env.example not found{Style.RESET_ALL}")
            return False

    # Create converter
    print("Initializing converter...")
    try:
        converter = FileConverter(
            source_lang="python",
            target_lang="javascript",
            model=os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        )
        print(f"{Fore.GREEN}✓ Converter initialized{Style.RESET_ALL}")
        print(f"  Model: {converter.model}")
        print(f"  Source: Python")
        print(f"  Target: JavaScript\n")
    except ValueError as e:
        print(f"{Fore.RED}Error initializing converter: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Please ensure your API keys are set in the .env file{Style.RESET_ALL}")
        return False

    # Test file path
    test_file = "examples/sample.py"

    if not os.path.exists(test_file):
        print(f"{Fore.RED}Error: Test file {test_file} not found{Style.RESET_ALL}")
        return False

    # Estimate cost first
    print("Estimating conversion cost...")
    estimate = converter.estimate_cost(test_file)
    print(f"  Input tokens: {estimate['input_tokens']}")
    print(f"  Estimated output tokens: {estimate['estimated_output_tokens']}")
    print(f"  Total tokens: {estimate['total_tokens']}")
    print(f"  Estimated cost: {estimate['estimated_cost']}\n")

    # Ask for confirmation
    response = input(f"{Fore.YELLOW}Proceed with conversion? (y/n): {Style.RESET_ALL}")
    if response.lower() != 'y':
        print("Conversion cancelled.")
        return False

    # Perform conversion
    output_path = "examples/output/sample.js"
    result = converter.convert_and_save(
        source_path=test_file,
        output_path=output_path,
        use_few_shot=True
    )

    if result["success"]:
        print(f"\n{Fore.GREEN}✅ Conversion completed successfully!{Style.RESET_ALL}")
        print(f"  Output saved to: {output_path}")

        # Display a preview of the converted code
        if os.path.exists(output_path):
            with open(output_path, 'r') as f:
                lines = f.readlines()[:20]  # First 20 lines
            print(f"\n{Fore.CYAN}Preview of converted code:{Style.RESET_ALL}")
            print("".join(lines))
            if len(lines) == 20:
                print("... (truncated)")
        return True
    else:
        print(f"\n{Fore.RED}❌ Conversion failed: {result.get('error', 'Unknown error')}{Style.RESET_ALL}")
        return False


def test_without_few_shot():
    """Test conversion without few-shot examples."""
    print_header("Testing Without Few-Shot Examples")

    if not os.path.exists(".env"):
        print(f"{Fore.RED}Please set up .env file first{Style.RESET_ALL}")
        return False

    try:
        converter = FileConverter(
            source_lang="python",
            target_lang="javascript",
            temperature=0.3  # Slightly higher temperature for creativity
        )

        # Create a simple test file
        simple_test = "examples/simple_test.py"
        with open(simple_test, 'w') as f:
            f.write("""
def greet(name):
    '''Greet a person by name.'''
    return f"Hello, {name}!"

def calculate_area(width, height):
    '''Calculate the area of a rectangle.'''
    return width * height

# Test the functions
if __name__ == "__main__":
    print(greet("World"))
    print(f"Area: {calculate_area(10, 5)}")
""")

        print(f"Testing simple conversion without few-shot examples...")
        result = converter.convert(simple_test, use_few_shot=False)

        if result["success"]:
            print(f"{Fore.GREEN}✓ Conversion successful (no few-shot){Style.RESET_ALL}")
            print(f"\nConverted code:\n{result['converted_code']}")
            return True
        else:
            print(f"{Fore.RED}✗ Conversion failed{Style.RESET_ALL}")
            return False

    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        return False


def test_different_models():
    """Test with different models if available."""
    print_header("Testing Different Models")

    models_to_test = [
        ("gpt-3.5-turbo", "OPENAI_API_KEY"),
        ("gpt-4", "OPENAI_API_KEY"),
        ("claude-3-sonnet-20240229", "ANTHROPIC_API_KEY")
    ]

    for model, api_key_env in models_to_test:
        if not os.getenv(api_key_env):
            print(f"{Fore.YELLOW}Skipping {model} (no API key){Style.RESET_ALL}")
            continue

        print(f"\nTesting with {model}...")
        try:
            converter = FileConverter(
                source_lang="python",
                target_lang="javascript",
                model=model,
                max_tokens=1000  # Smaller for testing
            )

            # Quick test with a simple function
            test_code = '''
def add(a, b):
    return a + b
'''
            with open("examples/temp_test.py", 'w') as f:
                f.write(test_code)

            result = converter.convert("examples/temp_test.py")

            if result["success"]:
                print(f"{Fore.GREEN}✓ {model} works!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ {model} failed{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}Error with {model}: {e}{Style.RESET_ALL}")


def main():
    """Run all tests."""
    print(f"{Fore.CYAN}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║          AI Code Converter - Test Suite               ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")

    # Run basic test
    success = test_basic_conversion()

    if success:
        # Run additional tests
        print(f"\n{Fore.YELLOW}Run additional tests? (y/n): {Style.RESET_ALL}", end="")
        if input().lower() == 'y':
            test_without_few_shot()
            # test_different_models()  # Uncomment if you want to test multiple models

    print(f"\n{Fore.CYAN}Testing complete!{Style.RESET_ALL}")
    print("\nNext steps:")
    print("1. Try converting your own Python files")
    print("2. Experiment with different languages (e.g., JavaScript to Python)")
    print("3. Adjust temperature and max_tokens for different results")
    print("4. Add more few-shot examples in src/prompts.py")


if __name__ == "__main__":
    main()