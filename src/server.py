"""
Lightweight FastAPI server for podcast packager agents.
Self-hosted alternative to LangGraph Platform.
"""

import os
import uuid
from typing import Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Import graphs
from main_packager.graph import graph as main_graph, PackagerState
from transcript_analyzer.graph import graph as transcript_graph
from trend_researcher.graph import graph as trend_graph
from titling_agent.graph import graph as titling_graph


# Database setup
DATABASE_URI = os.getenv("DATABASE_URI", os.getenv("POSTGRES_URI", ""))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Setup and teardown."""
    if DATABASE_URI:
        async with AsyncPostgresSaver.from_conn_string(DATABASE_URI) as checkpointer:
            await checkpointer.setup()
            app.state.checkpointer = checkpointer
            yield
    else:
        app.state.checkpointer = None
        yield


app = FastAPI(
    title="Podcast Packager Agents",
    description="Multi-agent system for podcast content packaging",
    version="2.1.0",
    lifespan=lifespan,
)


class RunRequest(BaseModel):
    """Request to run an agent."""
    input: dict[str, Any]
    thread_id: Optional[str] = None
    config: Optional[dict[str, Any]] = None


class ResumeRequest(BaseModel):
    """Request to resume after HITL interrupt."""
    thread_id: str
    response: Any
    config: Optional[dict[str, Any]] = None


class RunResponse(BaseModel):
    """Response from agent run."""
    thread_id: str
    state: dict[str, Any]
    status: str  # "completed", "interrupted", "error"
    interrupt_value: Optional[Any] = None


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "podcast-packager"}


@app.get("/assistants")
async def list_assistants():
    """List available agent assistants."""
    return {
        "assistants": [
            {
                "id": "podcast-packager",
                "name": "Main Packager",
                "description": "Orchestrates the full podcast packaging workflow with HITL",
            },
            {
                "id": "transcript-analyzer",
                "name": "Transcript Analyzer",
                "description": "Analyzes podcast transcripts and extracts key information",
            },
            {
                "id": "trend-researcher",
                "name": "Trend Researcher",
                "description": "Researches current trends for content optimization",
            },
            {
                "id": "titling-agent",
                "name": "Titling Agent",
                "description": "Generates optimized podcast titles",
            },
        ]
    }


def get_graph(assistant_id: str):
    """Get the graph for an assistant."""
    graphs = {
        "podcast-packager": main_graph,
        "transcript-analyzer": transcript_graph,
        "trend-researcher": trend_graph,
        "titling-agent": titling_graph,
    }
    if assistant_id not in graphs:
        raise HTTPException(status_code=404, detail=f"Assistant '{assistant_id}' not found")
    return graphs[assistant_id]


@app.post("/assistants/{assistant_id}/runs", response_model=RunResponse)
async def run_assistant(assistant_id: str, request: RunRequest):
    """Run an assistant with the given input."""
    graph = get_graph(assistant_id)

    thread_id = request.thread_id or str(uuid.uuid4())
    config = request.config or {}
    config["configurable"] = config.get("configurable", {})
    config["configurable"]["thread_id"] = thread_id

    # Add checkpointer if available
    checkpointer = getattr(app.state, "checkpointer", None)
    if checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)
    else:
        compiled = graph

    try:
        # Run the graph
        result = await compiled.ainvoke(request.input, config)

        return RunResponse(
            thread_id=thread_id,
            state=result,
            status="completed",
        )
    except Exception as e:
        # Check if it's an interrupt
        if "interrupt" in str(e).lower():
            # Get current state for interrupt value
            state = await compiled.aget_state(config)
            return RunResponse(
                thread_id=thread_id,
                state=state.values if state else {},
                status="interrupted",
                interrupt_value=getattr(state, "next", None),
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/threads/{thread_id}/resume", response_model=RunResponse)
async def resume_thread(thread_id: str, request: ResumeRequest):
    """Resume an interrupted thread with user response."""
    # For now, resume the main packager (most common use case)
    graph = main_graph

    config = request.config or {}
    config["configurable"] = config.get("configurable", {})
    config["configurable"]["thread_id"] = thread_id

    checkpointer = getattr(app.state, "checkpointer", None)
    if checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)
    else:
        raise HTTPException(
            status_code=400,
            detail="Cannot resume without checkpointer. Configure DATABASE_URI."
        )

    try:
        # Resume with the response
        result = await compiled.ainvoke(
            None,  # No new input, resume from checkpoint
            config,
            # Pass the user's response through command
        )

        return RunResponse(
            thread_id=thread_id,
            state=result,
            status="completed",
        )
    except Exception as e:
        if "interrupt" in str(e).lower():
            state = await compiled.aget_state(config)
            return RunResponse(
                thread_id=thread_id,
                state=state.values if state else {},
                status="interrupted",
                interrupt_value=getattr(state, "next", None),
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/threads/{thread_id}")
async def get_thread_state(thread_id: str):
    """Get the current state of a thread."""
    checkpointer = getattr(app.state, "checkpointer", None)
    if not checkpointer:
        raise HTTPException(
            status_code=400,
            detail="Cannot get thread state without checkpointer. Configure DATABASE_URI."
        )

    # Use main graph for state retrieval
    compiled = main_graph.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    state = await compiled.aget_state(config)
    if not state:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    return {
        "thread_id": thread_id,
        "state": state.values,
        "next": state.next,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
