"""
Brighter Together Podcast Packager - Main Orchestrator Graph

This LangGraph implementation coordinates three subagents to transform
podcast transcripts into marketing packages with human-in-the-loop title selection.
"""

from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
import json
import os

# Import subagent graphs
from ..transcript_analyzer.graph import graph as transcript_analyzer_graph
from ..trend_researcher.graph import graph as trend_researcher_graph
from ..titling_agent.graph import graph as titling_agent_graph


class PackagerState(TypedDict):
    """State schema for the podcast packager workflow."""
    # Input
    folder_id: str
    user_email: str

    # Preflight
    packaging_status: Literal["new_episode", "already_packaged", "no_transcript"]
    transcript_location: Literal["root", "full_length_assets"]
    user_decision: Literal["cancel", "repackage"] | None

    # Discovery
    guest_name: str
    transcript_id: str

    # Subagent outputs
    transcript_summary: dict
    trend_research: dict
    title_options: list

    # User selection
    selected_title: dict

    # Generated content
    episode_description: str
    lht_social_posts: dict
    guest_social_posts: dict

    # Drive operations
    created_files: list
    created_folders: list
    moved_files: list
    created_shortcuts: list
    archived_files: list

    # Workflow state
    current_phase: str
    messages: list


# Load system prompt from file
def load_system_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "../../main-packager/system_prompt.txt")
    with open(prompt_path, "r") as f:
        return f.read()


# Initialize model
model = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=8192,
)


def preflight_check(state: PackagerState) -> PackagerState:
    """Phase 0: Check if episode is new or already packaged."""
    # TODO: Implement Google Drive folder scanning using MCP tools
    # - list_drive_items to scan folder
    # - Check if transcript is in root or Full Length Assets

    # Placeholder logic
    return {
        **state,
        "current_phase": "preflight",
        "packaging_status": "new_episode",  # Would be determined by Drive scan
        "transcript_location": "root",
    }


def should_prompt_repackage(state: PackagerState) -> str:
    """Route based on preflight check results."""
    if state["packaging_status"] == "already_packaged":
        return "prompt_repackage"
    elif state["packaging_status"] == "no_transcript":
        return "error"
    return "discovery"


def prompt_repackage(state: PackagerState) -> PackagerState:
    """Interrupt for user decision on re-packaging."""
    decision = interrupt({
        "type": "repackage_decision",
        "message": "This episode appears to have been packaged before (transcript is in Full Length Assets/).\n\nWould you like to:\n1. Cancel - Do nothing\n2. Re-package - Archive existing content and create new versions",
        "options": ["cancel", "repackage"]
    })

    return {
        **state,
        "user_decision": decision,
    }


def should_continue_after_decision(state: PackagerState) -> str:
    """Route based on user's repackage decision."""
    if state["user_decision"] == "cancel":
        return END
    return "archive"


def archive_previous(state: PackagerState) -> PackagerState:
    """Archive existing generated files before re-packaging."""
    # TODO: Implement archive logic using MCP tools
    # - Create _Archive folder if not exists
    # - Move existing Episode Description, Title Options, etc. with date suffix
    # - Delete existing shortcuts in Guest Package

    return {
        **state,
        "current_phase": "archive",
        "archived_files": [],  # Would be populated by actual operations
    }


def discovery(state: PackagerState) -> PackagerState:
    """Phase 1: Extract guest name and confirm transcript."""
    # TODO: Implement discovery using MCP tools
    # - Find transcript in folder
    # - Extract guest name from filename or content

    return {
        **state,
        "current_phase": "discovery",
        "guest_name": "Guest Name",  # Would be extracted from transcript
        "transcript_id": "transcript_doc_id",
    }


def analyze_transcript(state: PackagerState) -> PackagerState:
    """Phase 2: Invoke Transcript Analyzer subagent."""
    result = transcript_analyzer_graph.invoke({
        "folder_id": state["folder_id"],
        "user_email": state["user_email"],
    })

    return {
        **state,
        "current_phase": "analyze",
        "transcript_summary": result,
    }


def research_trends(state: PackagerState) -> PackagerState:
    """Phase 3: Invoke Trend Researcher subagent."""
    result = trend_researcher_graph.invoke({
        "transcript_summary": state["transcript_summary"],
    })

    return {
        **state,
        "current_phase": "research",
        "trend_research": result,
    }


def generate_titles(state: PackagerState) -> PackagerState:
    """Phase 4: Invoke Titling Agent subagent and present options."""
    result = titling_agent_graph.invoke({
        "transcript_summary": state["transcript_summary"],
        "trend_research": state["trend_research"],
    })

    return {
        **state,
        "current_phase": "titles",
        "title_options": result.get("titles", []),
    }


def title_selection(state: PackagerState) -> PackagerState:
    """Phase 4b: Human-in-the-loop title selection."""
    titles_display = "\n".join([
        f"{i+1}. {t['title']} - {t['strategy']}\n   {t['rationale']}"
        for i, t in enumerate(state["title_options"])
    ])

    selection = interrupt({
        "type": "title_selection",
        "message": f"Based on transcript analysis and current social media trends, here are 5 title options:\n\n{titles_display}\n\nWhich title would you like to use, or do you have another suggestion?",
        "options": state["title_options"],
        "allowed_decisions": ["approve", "edit", "reject"],
    })

    return {
        **state,
        "selected_title": selection,
    }


def create_content(state: PackagerState) -> PackagerState:
    """Phase 5: Generate all marketing content using selected title."""
    system_prompt = load_system_prompt()

    # Build context from all subagent outputs
    context = {
        "transcript_summary": state["transcript_summary"],
        "trend_research": state["trend_research"],
        "selected_title": state["selected_title"],
        "guest_name": state["guest_name"],
    }

    # Generate Episode Description
    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Generate the Episode Description using this context:

{json.dumps(context, indent=2)}

Follow the Episode Description format from the system prompt exactly.
Use the selected title as the header.
NO EMOJIS. NO ASTERISKS.""")
    ])
    episode_description = response.content

    # Generate LHT Social Posts (4 platforms)
    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Generate LHT Social Posts for LinkedIn, Facebook, TikTok, and Instagram using this context:

{json.dumps(context, indent=2)}

Follow platform-specific formats from the system prompt.
All posts must tie back to the selected title theme.
NO EMOJIS. NO ASTERISKS.""")
    ])
    lht_social_posts = {"content": response.content}

    # Generate Guest Social Posts (in guest's voice)
    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Generate Guest Social Posts for {state['guest_name']} to post on their own LinkedIn, Facebook, TikTok, and Instagram.

Context:
{json.dumps(context, indent=2)}

Use the guest's voice profile from transcript_summary.
Write as if the guest is posting these themselves.
NO EMOJIS. NO ASTERISKS.""")
    ])
    guest_social_posts = {"content": response.content}

    return {
        **state,
        "current_phase": "content",
        "episode_description": episode_description,
        "lht_social_posts": lht_social_posts,
        "guest_social_posts": guest_social_posts,
    }


def drive_output(state: PackagerState) -> PackagerState:
    """Phase 6: Create folders, docs, and organize files in Google Drive."""
    # TODO: Implement using MCP tools:
    # - create_drive_file for folders
    # - create_doc for documents
    # - update_drive_file to move files
    # - create_drive_shortcut for Guest Package

    created_folders = [
        "Full Length Assets",
        "Podcast Artwork",
        "Social Assets",
        f"Guest Package - {state['guest_name']}",
    ]

    created_files = [
        f"{state['guest_name']} - Episode Description",
        f"{state['guest_name']} - Title Options",
        f"{state['guest_name']} - LHT Social Posts",
        f"{state['guest_name']} - Guest Social Posts",
    ]

    return {
        **state,
        "current_phase": "output",
        "created_folders": created_folders,
        "created_files": created_files,
    }


def organize_files(state: PackagerState) -> PackagerState:
    """Phase 6b: Move files and create shortcuts."""
    # TODO: Implement file organization using MCP tools
    # - Move media files to Full Length Assets
    # - Move shorts to Social Assets
    # - Move transcript to Full Length Assets
    # - Create shortcuts in Guest Package

    return {
        **state,
        "moved_files": [],
        "created_shortcuts": [],
    }


def deliver(state: PackagerState) -> PackagerState:
    """Phase 7: Final delivery summary."""
    return {
        **state,
        "current_phase": "complete",
    }


# Build the graph
builder = StateGraph(PackagerState)

# Add nodes
builder.add_node("preflight", preflight_check)
builder.add_node("prompt_repackage", prompt_repackage)
builder.add_node("archive", archive_previous)
builder.add_node("discovery", discovery)
builder.add_node("analyze", analyze_transcript)
builder.add_node("research", research_trends)
builder.add_node("titles", generate_titles)
builder.add_node("title_selection", title_selection)
builder.add_node("content", create_content)
builder.add_node("output", drive_output)
builder.add_node("organize", organize_files)
builder.add_node("deliver", deliver)

# Add edges
builder.add_edge(START, "preflight")
builder.add_conditional_edges("preflight", should_prompt_repackage)
builder.add_conditional_edges("prompt_repackage", should_continue_after_decision)
builder.add_edge("archive", "discovery")
builder.add_edge("discovery", "analyze")
builder.add_edge("analyze", "research")
builder.add_edge("research", "titles")
builder.add_edge("titles", "title_selection")
builder.add_edge("title_selection", "content")
builder.add_edge("content", "output")
builder.add_edge("output", "organize")
builder.add_edge("organize", "deliver")
builder.add_edge("deliver", END)

# Compile with checkpointer for HITL support
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)
