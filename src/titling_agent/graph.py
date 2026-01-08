"""
Titling Agent Subagent

Generates research-backed podcast titles using trend data,
marketing psychology, and platform-specific optimization.
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.tools import DuckDuckGoSearchRun
import json
import os


class TitlingState(TypedDict):
    """State schema for title generation."""
    transcript_summary: dict
    trend_research: dict
    strategy_research: list
    titles_result: dict


def load_system_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "../../titling-agent/system_prompt.txt")
    with open(prompt_path, "r") as f:
        return f.read()


model = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=8192,
)

search = DuckDuckGoSearchRun()


def research_strategies(state: TitlingState) -> TitlingState:
    """Research current title strategies."""
    search_queries = [
        "viral podcast titles 2025",
        "LinkedIn headline formulas that work",
        "YouTube title optimization 2025",
        "FOMO marketing examples 2025",
        "curiosity gap headlines examples",
        "education content marketing headlines",
    ]

    results = []
    for query in search_queries:
        try:
            result = search.run(query)
            results.append({"query": query, "result": result})
        except Exception as e:
            results.append({"query": query, "error": str(e)})

    return {
        **state,
        "strategy_research": results,
    }


def generate_titles(state: TitlingState) -> TitlingState:
    """Generate 5 titles using different strategies."""
    system_prompt = load_system_prompt()

    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Generate 5 title options using this context:

Transcript Summary:
{json.dumps(state['transcript_summary'], indent=2)}

Trend Research:
{json.dumps(state['trend_research'], indent=2)}

Strategy Research:
{json.dumps(state['strategy_research'], indent=2)}

Each title must use a different strategy (FOMO, Reversal, Challenge, Curiosity Gap, Authority/Transformation).
Return ONLY valid JSON matching the output_schema from agent.json.""")
    ])

    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        result = {"error": "Failed to parse response as JSON", "raw": response.content}

    return {
        **state,
        "titles_result": result,
    }


# Build graph
builder = StateGraph(TitlingState)
builder.add_node("research", research_strategies)
builder.add_node("generate", generate_titles)
builder.add_edge(START, "research")
builder.add_edge("research", "generate")
builder.add_edge("generate", END)

graph = builder.compile()
