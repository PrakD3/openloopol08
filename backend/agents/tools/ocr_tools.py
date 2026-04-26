"""OCR tools using Groq Vision (replaces EasyOCR)."""

import base64
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


async def extract_text_from_frames(
    frame_paths: List[str],
    groq_client=None,
    vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct",
) -> str:
    """
    Extract all visible text from video keyframes using Groq Vision.
    Targets chyrons, lower thirds, watermarks, channel names, timestamps,
    location overlays, breaking news banners, and street signs.
    Returns concatenated text from all frames, deduplicated.

    Note: groq_client parameter kept for backward compatibility but not used
    directly — uses settings.groq_api_key via httpx directly.
    """
    if not frame_paths:
        return ""

    # Use top 3 frames only (middle frames tend to have clearest overlays)
    frames_to_check = (
        frame_paths[:3]
        if len(frame_paths) <= 3
        else [
            frame_paths[0],
            frame_paths[len(frame_paths) // 2],
            frame_paths[-1],
        ]
    )

    all_text_chunks = []

    import httpx

    from config.settings import settings

    if not settings.groq_api_key:
        return ""

    for frame_path in frames_to_check:
        if not Path(frame_path).exists():
            logger.warning(f"[OCR] Frame not found: {frame_path}")
            continue

        try:
            with open(frame_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    json={
                        "model": vision_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                                    },
                                    {
                                        "type": "text",
                                        "text": (
                                            "Extract ALL visible text from this image. "
                                            "Include: news tickers, lower third banners, chyrons, "
                                            "channel watermarks (e.g. @CHANNEL, network names), "
                                            "timestamps, location overlays, street signs, "
                                            "captions, breaking news banners, and any other text. "
                                            "Output ONLY the extracted text, one item per line. "
                                            "If no text is visible, output: [no text detected]"
                                        ),
                                    },
                                ],
                            }
                        ],
                        "max_tokens": 300,
                    },
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()
                if text and text != "[no text detected]":
                    all_text_chunks.append(text)
                    logger.info(f"[OCR] Frame {Path(frame_path).name}: extracted {len(text)} chars")

        except Exception as e:
            logger.error(f"[OCR] Vision OCR failed for {frame_path}: {e}")
            continue

    if not all_text_chunks:
        return ""

    # Deduplicate lines across frames
    seen = set()
    deduped = []
    for chunk in all_text_chunks:
        for line in chunk.splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                deduped.append(line)

    result = "\n".join(deduped)
    logger.info(f"[OCR] Final OCR result: {len(deduped)} unique lines")
    return result
