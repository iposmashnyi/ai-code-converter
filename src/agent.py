"""
LangGraph-based code conversion agent using Claude Sonnet 4.

This agent orchestrates the conversion of entire codebases with automatic
state management, checkpointing, and resume capability via InMemorySaver.
"""

import os
import json
from pathlib import Path
from typing import Literal, List, Tuple, Dict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, ToolMessage

from src.state import ConversionState
from src.tools import ALL_TOOLS
from src.prompts import get_system_prompt


class CodeConverterAgent:
    """
    LangGraph agent that converts code from one language to another.

    Uses Claude Sonnet 4 with tools to intelligently analyze and convert
    entire projects while maintaining consistency.
    """

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the conversion agent.

        Args:
            api_key: Anthropic API key (reads from env if not provided)
            model: Claude model to use (default: claude-sonnet-4)
        """
        # Get API key
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")

        # Initialize Claude Sonnet 4
        self.llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0.1,
            max_tokens=8192,  # Increased from 4096 to handle larger file conversions
            timeout=300.0,
        )

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS)

        # Create tool name to function mapping
        self.tools_by_name = {tool.name: tool for tool in ALL_TOOLS}

        # System prompt
        self.system_prompt = get_system_prompt()

        # Build the graph
        self.graph = self._build_graph()

        # Compile with checkpointing!
        self.checkpointer = InMemorySaver()
        self.app = self.graph.compile(checkpointer=self.checkpointer)

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(ConversionState)

        # Define nodes
        workflow.add_node("analyze_project", self.analyze_project)
        workflow.add_node("discover_files", self.discover_files)
        workflow.add_node("convert_file", self.convert_file)

        # Define edges
        workflow.set_entry_point("analyze_project")
        workflow.add_edge("analyze_project", "discover_files")
        workflow.add_edge("discover_files", "convert_file")

        # Conditional edge: continue or finish?
        workflow.add_conditional_edges(
            "convert_file",
            self.should_continue,
            {
                "continue": "convert_file",  # Loop back for next file
                "end": END                     # All done
            }
        )

        return workflow

    def _extract_json_from_markdown(self, content: str) -> str:
        """
        Extract JSON from markdown code blocks if present.

        Handles formats like:
        - ```json\n{...}\n```
        - ```\n{...}\n```
        - Plain JSON
        """
        import re

        # Try to find JSON in markdown code blocks
        json_block_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
        matches = re.findall(json_block_pattern, content)

        if matches:
            return matches[0].strip()

        # Return original content if no code block found
        return content.strip()

    def _extract_json_list(self, content: str) -> List[str]:
        """
        Parse a JSON list from LLM response, handling markdown code blocks.

        Returns empty list if parsing fails.
        """
        try:
            # Extract from markdown if needed
            json_str = self._extract_json_from_markdown(content)

            # Parse JSON
            parsed = json.loads(json_str)

            # Ensure it's a list
            if isinstance(parsed, list):
                return parsed
            else:
                print(f"[WARNING] Expected list, got {type(parsed).__name__}")
                return []

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}")
            print(f"[ERROR] Content: {content[:200]}")
            return []

    def _extract_json_dict(self, content: str) -> Dict:
        """
        Parse a JSON dict from LLM response, handling markdown code blocks.

        Returns empty dict if parsing fails.
        """
        try:
            # Extract from markdown if needed
            json_str = self._extract_json_from_markdown(content)

            # Parse JSON
            parsed = json.loads(json_str)

            # Ensure it's a dict
            if isinstance(parsed, dict):
                return parsed
            else:
                print(f"[WARNING] Expected dict, got {type(parsed).__name__}")
                return {}

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}")
            print(f"[ERROR] Content: {content[:200]}")
            return {}

    def _call_llm_with_tools(self, messages: List[BaseMessage], max_iterations: int = 10) -> Tuple[str, List[BaseMessage]]:
        """
        Helper method that handles the tool calling loop.

        Calls the LLM, executes any requested tools, and repeats until
        the LLM provides a final response without tool calls.

        Args:
            messages: List of messages to send to the LLM
            max_iterations: Maximum number of tool calling iterations

        Returns:
            Tuple of (final_response_content, all_messages_including_tool_calls)
        """
        all_messages = messages.copy()

        for iteration in range(max_iterations):
            # Call LLM
            response = self.llm_with_tools.invoke(all_messages)
            all_messages.append(response)

            # Check if there are tool calls
            if not response.tool_calls:
                # No more tools to call, return final content
                return response.content, all_messages

            # Execute each tool call
            tool_errors = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                # Execute the tool
                if tool_name in self.tools_by_name:
                    try:
                        # Special validation for write_file_content
                        if tool_name == "write_file_content":
                            if "content" not in tool_args or not tool_args["content"]:
                                error_msg = "write_file_content requires both file_path and content parameters, but content parameter was missing in the function call"
                                tool_result = f"Tool execution failed: {error_msg}"
                                tool_errors.append(f"{tool_name}: {error_msg}")
                            else:
                                tool_result = self.tools_by_name[tool_name].invoke(tool_args)
                                if not isinstance(tool_result, str):
                                    tool_result = str(tool_result)
                        else:
                            tool_result = self.tools_by_name[tool_name].invoke(tool_args)
                            # Convert result to string if it isn't already
                            if not isinstance(tool_result, str):
                                tool_result = str(tool_result)
                    except Exception as e:
                        tool_result = f"Error executing tool: {str(e)}"
                        tool_errors.append(f"{tool_name}: {str(e)}")
                else:
                    tool_result = f"Error: Tool '{tool_name}' not found"
                    tool_errors.append(f"Tool not found: {tool_name}")

                # Add tool message to conversation
                all_messages.append(
                    ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_id
                    )
                )

            # If there were tool errors, add a reminder to return proper JSON
            if tool_errors:
                all_messages.append(
                    HumanMessage(content=f"Tool execution errors occurred: {'; '.join(tool_errors)}\n\nPlease respond with valid JSON indicating failure. Do not call the failed tool again.")
                )

        # If we hit max iterations, return what we have
        return all_messages[-1].content if all_messages else "", all_messages

    def analyze_project(self, state: ConversionState) -> ConversionState:
        """
        Node 1: Analyze the project structure using tools.

        The LLM explores the directory and understands the codebase.
        """
        print(f"\n📊 Analyzing project structure...")

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Analyze this {state['source_lang']} project at: {state['source_dir']}

            Your task:
            1. Use list_directory_files to explore the project structure
            2. Use check_gitignore_patterns to see what should be excluded
            3. Understand the project type (web app, library, CLI tool, etc.)
            4. Identify the main components and architecture
            
            Provide a JSON summary including:
            - project_type: What kind of project is this?
            - main_directories: Key directories and their purpose
            - estimated_file_count: Rough number of source files
            - notes: Any important observations
            
            Respond with JSON only.""")
        ]

        # Call LLM with tool execution loop
        response_content, all_messages = self._call_llm_with_tools(messages)

        # Debug: print what the LLM returned
        print(f"\n[DEBUG] LLM response content:\n{response_content[:500]}\n")

        # Parse the analysis - handle markdown code blocks
        analysis = self._extract_json_dict(response_content)

        # Fallback if empty
        if not analysis:
            analysis = {
                "project_type": "unknown",
                "notes": response_content[:500]
            }

        print(f"✓ Project type: {analysis.get('project_type', 'unknown')}")

        return {
            **state,
            "messages": all_messages,
            "project_analysis": analysis
        }

    def discover_files(self, state: ConversionState) -> ConversionState:
        """
        Node 2: Discover which files to convert.

        The LLM intelligently selects source files to convert,
        excluding tests, build artifacts, etc.
        """
        print(f"\n🔍 Discovering files to convert...")

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Based on your project analysis:
            {json.dumps(state['project_analysis'], indent=2)}

            SOURCE DIRECTORY: {state['source_dir']}

            Find all {state['source_lang']} source files IN THE SOURCE DIRECTORY ABOVE that need to be converted to {state['target_lang']}.

            IMPORTANT: Only search within the source directory specified above. Do not search other directories.

            Guidelines:
            - Use search_files_by_pattern or list_directory_files with the source directory
            - Include: Core source code files
            - Exclude: Test files (unless they have important logic)
            - Exclude: Build artifacts, dependencies (node_modules, __pycache__, etc.)
            - Exclude: Configuration files (unless they contain code)
            - Prioritize: Entry points and core business logic first

            Respond with a JSON array of file paths, ordered by conversion priority:
            ["path/to/file1.{state['source_lang']}", "path/to/file2.{state['source_lang']}", ...]

            Limit to 25 files max.""")
        ]

        # Call LLM with tool execution loop
        response_content, all_messages = self._call_llm_with_tools(messages)

        # Debug: print what the LLM returned
        print(f"\n[DEBUG] LLM response content:\n{response_content[:500]}\n")

        # Parse file list - try to extract JSON from markdown code blocks if needed
        files = self._extract_json_list(response_content)

        print(f"✓ Found {len(files)} files to convert")

        return {
            **state,
            "messages": all_messages,
            "files_to_convert": files,
            "current_file_index": 0,
            "files_completed": 0,
            "files_failed": 0,
            "converted_files": [],
            "failed_files": [],
            "conversion_context": {}
        }

    def convert_file(self, state: ConversionState) -> ConversionState:
        """
        Node 3: Convert the current file.

        The LLM reads the source file, converts it to the target language,
        and saves the result. It maintains consistency using conversion_context.
        """
        current_idx = state["current_file_index"]

        # Safety check: if no files to convert, return immediately
        if not state["files_to_convert"] or current_idx >= len(state["files_to_convert"]):
            return state

        file_path = state["files_to_convert"][current_idx]

        print(f"\n🔄 Converting [{current_idx + 1}/{len(state['files_to_convert'])}]: {Path(file_path).name}")

        # Check file size and warn if it's large
        try:
            file_size_kb = Path(file_path).stat().st_size / 1024
            if file_size_kb > 100:
                print(f"  ⚠️  Warning: Large file ({file_size_kb:.1f}KB) - conversion may require multiple attempts")
        except Exception:
            pass  # File size check is optional

        # Build context message
        context_info = ""
        if state.get("conversion_context"):
            context_info = f"\n\nPrevious conversion patterns:\n{json.dumps(state['conversion_context'], indent=2)}\n\nMaintain consistency with these patterns!"

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Convert this file from {state['source_lang']} to {state['target_lang']}.

            Project context:
            {json.dumps(state['project_analysis'], indent=2)}
            {context_info}

            File to convert: {file_path}

            CRITICAL INSTRUCTIONS:
            1. Use read_file_content to read the source file
            2. Convert the ENTIRE code to {state['target_lang']} - preserve all logic and functionality
            3. Determine the output path in {state['target_dir']} (change extension appropriately)
            4. Use write_file_content with BOTH parameters:
               - file_path: the output path
               - content: the COMPLETE converted code as a string
            5. IMPORTANT: You MUST provide the full converted code as the 'content' parameter to write_file_content
            6. After writing, tell me what naming patterns or library mappings you used

            If ANY step fails:
            - Do NOT call write_file_content
            - Respond with JSON indicating failure

            After all tools complete successfully, respond with JSON only:
            {{
              "converted": true/false,
              "output_path": "where you saved the file",
              "patterns_used": {{"pattern_name": "pattern_value"}},
              "error": "error message if failed (only if converted=false)"
            }}

            Remember: write_file_content requires TWO parameters: file_path AND content (the full converted code).""")
        ]

        try:
            # Call LLM with tool execution loop
            response_content, all_messages = self._call_llm_with_tools(messages)

            # Parse response - handle markdown code blocks
            result = self._extract_json_dict(response_content)

            # Fallback if parsing failed
            if not result:
                # Check if the response contains an error message about tool validation
                if "validation error" in response_content.lower() or "field required" in response_content.lower():
                    result = {
                        "converted": False,
                        "error": f"Tool calling error: {response_content[:200]}"
                    }
                else:
                    result = {
                        "converted": False,
                        "error": f"Invalid response format: {response_content[:200]}"
                    }

            if result.get("converted"):
                # Success!
                print(f"  ✓ Saved to: {result.get('output_path')}")

                # Update conversion context with new patterns
                new_patterns = result.get("patterns_used", {})
                updated_context = {**state.get("conversion_context", {}), **new_patterns}

                return {
                    **state,
                    "messages": all_messages,
                    "converted_files": [{
                        "source": file_path,
                        "target": result.get("output_path"),
                        "success": True
                    }],
                    "conversion_context": updated_context,
                    "current_file_index": current_idx + 1,
                    "files_completed": state.get("files_completed", 0) + 1
                }
            else:
                # Failed
                error = result.get("error", "Unknown error")
                print(f"  ✗ Failed: {error}")

                return {
                    **state,
                    "messages": all_messages,
                    "failed_files": [{
                        "file": file_path,
                        "error": error
                    }],
                    "current_file_index": current_idx + 1,
                    "files_failed": state.get("files_failed", 0) + 1
                }

        except Exception as e:
            print(f"  ✗ Exception: {str(e)}")

            return {
                **state,
                "failed_files": [{
                    "file": file_path,
                    "error": str(e)
                }],
                "current_file_index": current_idx + 1,
                "files_failed": state.get("files_failed", 0) + 1
            }

    def should_continue(self, state: ConversionState) -> Literal["continue", "end"]:
        """Decide whether to continue converting or finish."""
        if state["current_file_index"] >= len(state["files_to_convert"]):
            return "end"
        return "continue"

    def convert_project(
        self,
        source_dir: str,
        target_dir: str,
        source_lang: str,
        target_lang: str,
        thread_id: str = "default"
    ) -> ConversionState:
        """
        Convert an entire project.

        Args:
            source_dir: Source directory path
            target_dir: Output directory path
            source_lang: Source language (e.g., "python")
            target_lang: Target language (e.g., "javascript")
            thread_id: Thread ID for checkpointing (use same ID to resume)

        Returns:
            Final state with conversion results
        """
        # Create initial state
        initial_state: ConversionState = {
            "messages": [],
            "source_dir": str(Path(source_dir).resolve()),
            "target_dir": str(Path(target_dir).resolve()),
            "source_lang": source_lang,
            "target_lang": target_lang,
            "project_analysis": {},
            "files_to_convert": [],
            "current_file_index": 0,
            "converted_files": [],
            "failed_files": [],
            "conversion_context": {},
            "files_completed": 0,
            "files_failed": 0
        }

        # Configure with thread ID for checkpointing
        config = {"configurable": {"thread_id": thread_id}}

        # Run the graph (automatically checkpoints after each node!)
        print(f"\n🚀 Starting conversion: {source_lang} → {target_lang}")
        print(f"   Source: {source_dir}")
        print(f"   Target: {target_dir}")
        print(f"   Thread ID: {thread_id} (use this to resume if interrupted)")

        final_state = self.app.invoke(initial_state, config)

        # Print summary
        print(f"\n{'='*60}")
        print(f"✅ Conversion Complete!")
        print(f"   Succeeded: {final_state['files_completed']}")
        print(f"   Failed: {final_state['files_failed']}")
        print(f"   Patterns discovered: {len(final_state['conversion_context'])}")
        print(f"{'='*60}\n")

        return final_state
