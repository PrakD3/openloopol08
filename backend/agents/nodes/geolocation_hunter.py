import logging
import time
import json
import asyncio
import base64
from typing import Dict, List, Optional
from PIL import Image
import io

from agents.state import AgentState, AgentFinding
from config.settings import get_llm, settings

logger = logging.getLogger(__name__)

# OSINT Geolocation Prompt inspired by GeoIntel
GEOLOCATION_PROMPT = """You are an expert OSINT Geolocation Analyst.
Your task is to analyze the provided image(s) to determine the exact location where they were taken.

Analyze the visual clues in phases:
1. ENVIRONMENT: Climate, vegetation, soil, topography.
2. INFRASTRUCTURE: Architecture, road markings, signage (language, fonts, symbols), utility poles, license plates.
3. LANDMARKS: Recognizable buildings, monuments, or natural features.
4. TEXTUAL CLUES: Shop names, posters, or any readable text in the image.

Your response MUST be a valid JSON object ONLY. No markdown formatting, no code blocks, no preamble.
The JSON structure should be:
{
  "interpretation": "3-5 sentence summary of your analysis.",
  "locations": [
    {
      "country": "Country name",
      "state": "State/Province name",
      "city": "City name",
      "coordinates": {"latitude": 0.0, "longitude": 0.0},
      "confidence": "High/Medium/Low",
      "explanation": "2-3 sentences explaining the evidence for this specific location."
    }
  ]
}
"""

class GeolocationHunter:
    def __init__(self):
        # ── Use centralized LLM factory (prioritizes Google AI Studio / Vertex) ─
        try:
            self.llm = get_llm(model=settings.gemini_model)
            self.mode = "google" if settings.google_api_key else "vertex"
            logger.info(f"Geolocation Hunter: Initialized with {self.mode.upper()} ({settings.gemini_model})")
        except Exception as e:
            logger.error(f"Geolocation Hunter: LLM init failed: {e}. Falling back to Groq...")
            self.llm = get_llm(model=settings.groq_vision_model)
            self.mode = "groq"
        
    def _encode_image(self, image_path: str) -> str:
        # Optimization: Resize image to save tokens and avoid 429
        img = Image.open(image_path)
        # Convert to RGB if necessary (to avoid issues with PNG transparency)
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Max dimension 768px (standard for vision models)
        img.thumbnail((768, 768))
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    async def run(self, state: AgentState) -> Dict:
        logger.info("Geolocation Hunter: Starting analysis")
        start_time = time.time()
        
        keyframes = state.get("keyframes", [])
        if not keyframes:
            return {
                "geolocation_result": AgentFinding(
                    agent_id="geolocation_hunter",
                    agent_name="Geo Hunter",
                    status="error",
                    findings=["No keyframes available for analysis"]
                )
            }

        # Analyze the first few keyframes (usually best for landscape/context)
        # In a real app, we might pick keyframes with most 'entropy' or clarity.
        target_frames = keyframes[:2] 
        
        all_findings = []
        best_location = None
        
        try:
            # We use the vision model to analyze the frames
            # Using ChatGroq via LangChain
            from langchain_core.messages import HumanMessage
            
            content = [
                {"type": "text", "text": GEOLOCATION_PROMPT}
            ]
            
            for frame_path in target_frames:
                base64_image = self._encode_image(frame_path)
                if self.mode == "gemini":
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    })
                else:
                    # Groq format (sometimes slightly different in langchain_groq)
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    })

            # Call the LLM
            message = HumanMessage(content=content)
            response = await asyncio.wait_for(self.llm.ainvoke([message]), timeout=60.0)
            
            # Parse JSON response
            # Sometimes LLMs wrap in markdown blocks, we strip them.
            raw_text = response.content.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].strip()
                
            data = json.loads(raw_text)
            
            interpretation = data.get("interpretation", "No interpretation provided.")
            locations = data.get("locations", [])
            
            if locations:
                best_location = locations[0]
                loc_str = f"{best_location.get('city')}, {best_location.get('country')}"
                all_findings.append(f"Predicted Location: {loc_str}")
                all_findings.append(f"Confidence: {best_location.get('confidence')}")
                
            duration = int((time.time() - start_time) * 1000)
            
            finding = AgentFinding(
                agent_id="geolocation_hunter",
                agent_name="Geo Hunter",
                status="done",
                findings=all_findings,
                detail=interpretation,
                duration_ms=duration
            )
            
            return {
                "geolocation_result": finding,
                "actual_location": f"{best_location.get('city')}, {best_location.get('state')}, {best_location.get('country')}" if best_location else "Unknown",
                "latitude": best_location.get("coordinates", {}).get("latitude") if best_location else None,
                "longitude": best_location.get("coordinates", {}).get("longitude") if best_location else None,
                "key_flags": state.get("key_flags", []) + (["Geolocation Mismatch"] if state.get("claimed_location") and best_location and state.get("claimed_location").lower() not in loc_str.lower() else [])
            }

        except Exception as e:
            logger.error(f"Geolocation Hunter Error: {e}")
            return {
                "geolocation_result": AgentFinding(
                    agent_id="geolocation_hunter",
                    agent_name="Geo Hunter",
                    status="error",
                    findings=[f"Analysis failed: {str(e)}"]
                )
            }

async def geolocation_node(state: AgentState) -> Dict:
    hunter = GeolocationHunter()
    return await hunter.run(state)
