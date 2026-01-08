"""
Trend Researcher Subagent

Researches current social media trends and ranks transcript data
by viral potential and algorithm favorability.
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.tools import DuckDuckGoSearchRun
import json
import os


class ResearcherState(TypedDict):
    """State schema for trend research."""
    transcript_summary: dict
    search_results: list
    research_result: dict


def load_system_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "../../trend-researcher/system_prompt.txt")
    with open(prompt_path, "r") as f:
        return f.read()


model = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=8192,
)

search = DuckDuckGoSearchRun()


def conduct_research(state: ResearcherState) -> ResearcherState:
    """Execute web searches for trend research."""
    transcript = state["transcript_summary"]
    themes = transcript.get("key_themes", [])

    search_queries = [
        # Platform-specific searches
        f"{themes[0]['theme'] if themes else 'education'} LinkedIn viral 2025",
        "K-12 education leadership LinkedIn trending",
        "teacher TikTok viral 2025",
        "education Instagram reels trending",
        # Sector searches
        "SPED education news 2025",
        "K-12 teacher retention trending",
        "school administrator burnout viral",
        # National context
        "education policy news January 2025",
    ]

    results = []
    for query in search_queries[:8]:  # Minimum 8 searches
        try:
            result = search.run(query)
            results.append({"query": query, "result": result})
        except Exception as e:
            results.append({"query": query, "error": str(e)})

    return {
        **state,
        "search_results": results,
    }


def analyze_trends(state: ResearcherState) -> ResearcherState:
    """Analyze search results and rank transcript data."""
    system_prompt = load_system_prompt()

    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Based on this transcript summary:

{json.dumps(state['transcript_summary'], indent=2)}

And these search results:

{json.dumps(state['search_results'], indent=2)}

Rank the transcript data by trend potential and provide content strategy recommendations.
Return ONLY valid JSON matching the output_schema from agent.json.""")
    ])

    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        result = {"error": "Failed to parse response as JSON", "raw": response.content}

    return {
        **state,
        "research_result": result,
    }


# Build graph
builder = StateGraph(ResearcherState)
builder.add_node("research", conduct_research)
builder.add_node("analyze", analyze_trends)
builder.add_edge(START, "research")
builder.add_edge("research", "analyze")
builder.add_edge("analyze", END)

graph = builder.compile()
