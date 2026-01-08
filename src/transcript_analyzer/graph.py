"""
Transcript Analyzer Subagent

Reads full podcast transcripts and extracts structured data including
guest info, themes, quote bank, pain points, and voice profile.
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
import json
import os


class AnalyzerState(TypedDict):
    """State schema for transcript analysis."""
    folder_id: str
    document_id: str | None
    user_email: str
    transcript_content: str
    analysis_result: dict


def load_system_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "../../transcript-analyzer/system_prompt.txt")
    with open(prompt_path, "r") as f:
        return f.read()


model = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=8192,
)


def fetch_transcript(state: AnalyzerState) -> AnalyzerState:
    """Fetch transcript from Google Drive using MCP tools."""
    # TODO: Implement using MCP tools:
    # - list_drive_items to find transcript if folder_id provided
    # - get_doc_content to read transcript

    return {
        **state,
        "transcript_content": "",  # Would be populated from Drive
    }


def analyze_transcript(state: AnalyzerState) -> AnalyzerState:
    """Analyze transcript and extract structured data."""
    system_prompt = load_system_prompt()

    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Analyze this transcript and return structured JSON output:

{state['transcript_content']}

Return ONLY valid JSON matching the output_schema from agent.json.""")
    ])

    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        result = {"error": "Failed to parse response as JSON", "raw": response.content}

    return {
        **state,
        "analysis_result": result,
    }


# Build graph
builder = StateGraph(AnalyzerState)
builder.add_node("fetch", fetch_transcript)
builder.add_node("analyze", analyze_transcript)
builder.add_edge(START, "fetch")
builder.add_edge("fetch", "analyze")
builder.add_edge("analyze", END)

graph = builder.compile()
