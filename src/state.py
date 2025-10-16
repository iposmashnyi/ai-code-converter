"""
State definition for the LangGraph code conversion agent.
This replaces the manual state management in ProgressTracker and SymbolCache.
"""

from typing import TypedDict, List, Dict, Annotated
from langchain_core.messages import BaseMessage
import operator


class ConversionState(TypedDict):
    """
    State that flows through the LangGraph conversion workflow.

    This state is automatically checkpointed by LangGraph's InMemorySaver,
    enabling resume capability without manual state management.
    """

    # Messages for tool calling (required by ToolNode)
    messages: Annotated[List[BaseMessage], operator.add]

    # Input configuration
    source_dir: str
    target_dir: str
    source_lang: str
    target_lang: str

    # Project understanding (populated by analyze_project node)
    project_analysis: Dict

    # Files to convert (populated by discover_files node)
    files_to_convert: List[str]
    current_file_index: int

    # Conversion results (accumulated using operator.add)
    converted_files: Annotated[List[Dict], operator.add]
    failed_files: Annotated[List[Dict], operator.add]

    # Conversion context - replaces SymbolCache!
    # The LLM maintains consistency by seeing this context
    conversion_context: Dict[str, str]

    # Simple counters (no token/cost tracking)
    files_completed: int
    files_failed: int
