import random

def run_orchestrator(agent_outputs: dict) -> dict:
    """
    Mock orchestrator that synthesizes agent outputs into a final verdict.
    """
    # Logic: If deepfake agent says fake, verdict is unverified
    is_fake = agent_outputs.get("deepfake", {}).get("label") == "fake"
    verdict = "unverified" if is_fake else "real"
    
    confidence = random.randint(40, 70)
    steps = [
        "Extracted keyframes",
        "Processed audio",
        "Analyzed deepfake score",
        "Verified source credibility",
        "Checked context consistency",
        "Analyzed temporal flow",
        "Synthesized final verdict"
    ]
    return {
        "verdict": verdict,
        "confidence": confidence,
        "steps": steps
    }
