"""Agent node tests."""

import pytest

from agents.state import AgentFinding, AgentState


def _make_state() -> AgentState:
    return AgentState(
        video_url="https://www.youtube.com/watch?v=test",
        video_path=None,
        job_id="test-job-001",
        keyframes=[],
        audio_path=None,
        metadata={},
        transcript=None,
        ocr_text=None,
        deepfake_result=None,
        source_result=None,
        context_result=None,
        verdict=None,
        credibility_score=None,
        panic_index=None,
        summary=None,
        source_origin=None,
        original_date=None,
        claimed_location=None,
        actual_location=None,
        key_flags=[],
        error=None,
    )


@pytest.mark.asyncio
async def test_deepfake_detector_demo() -> None:
    """DeepFake detector returns a finding in demo mode."""
    from agents.nodes.deepfake_detector import deepfake_detector_node

    state = _make_state()
    result = await deepfake_detector_node(state)

    assert isinstance(result, AgentFinding)
    assert result.agent_id == "deepfake-detector"
    assert result.status == "done"


@pytest.mark.asyncio
async def test_source_hunter_demo() -> None:
    """Source hunter returns a finding in demo mode."""
    from agents.nodes.source_hunter import source_hunter_node

    state = _make_state()
    result = await source_hunter_node(state)

    assert isinstance(result, AgentFinding)
    assert result.agent_id == "source-hunter"
    assert result.status == "done"


@pytest.mark.asyncio
async def test_context_analyser_demo() -> None:
    """Context analyser returns a finding in demo mode."""
    from agents.nodes.context_analyser import context_analyser_node

    state = _make_state()
    result = await context_analyser_node(state)

    assert isinstance(result, AgentFinding)
    assert result.agent_id == "context-analyser"
    assert result.status == "done"
