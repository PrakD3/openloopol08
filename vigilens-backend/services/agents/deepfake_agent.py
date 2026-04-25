from typing import List

async def run_deepfake_agent(frames: List[str]) -> dict:
    """
    Mock agent to simulate deepfake detection on video frames.
    """
    return {
        "label": "fake",
        "confidence": 0.7
    }
