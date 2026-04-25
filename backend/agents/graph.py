import asyncio
from typing import Any, Dict

from langgraph.graph import END, StateGraph
from langsmith import traceable

from agents.nodes.context_analyser import context_analyser_node
from agents.nodes.deepfake_detector import deepfake_detector_node
from agents.nodes.orchestrator import orchestrator_node
from agents.nodes.source_hunter import source_hunter_node
from agents.state import AgentState
from agents.tools.ffmpeg_tools import extract_audio, extract_keyframes


def create_vigilens_graph() -> Any:
    """
    Vigilens LangGraph pipeline.

    Flow:
      [preprocess] -> [parallel_analysis] -> [orchestrator] -> END

    The three detection agents run concurrently using asyncio.gather inside
    a single 'parallel_analysis' node.
    """
    workflow: StateGraph = StateGraph(AgentState)

    workflow.add_node("preprocess", preprocess_node)
    workflow.add_node("parallel_analysis", parallel_analysis_node)
    workflow.add_node("orchestrator", orchestrator_node)

    workflow.set_entry_point("preprocess")
    workflow.add_edge("preprocess", "parallel_analysis")
    workflow.add_edge("parallel_analysis", "orchestrator")
    workflow.add_edge("orchestrator", END)

    return workflow.compile()


@traceable(name="preprocess")
async def preprocess_node(state: AgentState) -> Dict:
    """Extract keyframes and audio from the video."""
    source = state.get("video_path") or state.get("video_url") or ""
    frames = await extract_keyframes(source)
    audio = await extract_audio(source)
    return {**state, "keyframes": frames, "audio_path": audio}


@traceable(name="parallel_analysis")
async def parallel_analysis_node(state: AgentState) -> Dict:
    """Run all 3 detection agents concurrently and merge results."""
    deepfake_result, source_result, context_result = await asyncio.gather(
        deepfake_detector_node(state),
        source_hunter_node(state),
        context_analyser_node(state),
        return_exceptions=False,
    )
    return {
        **state,
        "deepfake_result": deepfake_result,
        "source_result": source_result,
        "context_result": context_result,
    }


# Instantiate once at import
graph = create_vigilens_graph()
