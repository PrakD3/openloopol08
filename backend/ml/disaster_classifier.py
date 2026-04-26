"""
Disaster Type Classifier
=========================
Lightweight keyword-based classifier that infers the disaster type from
transcript text, OCR text, LLM findings, and video URL/title.
No external model needed — works offline.
"""

from __future__ import annotations

import re

DISASTER_KEYWORDS: dict[str, list[str]] = {
    "flood": [
        "flood",
        "flooding",
        "inundated",
        "submerged",
        "water level",
        "deluge",
        "waterlogged",
        "overflow",
        "river burst",
        "cloudburst",
        "बाढ़",
        "வெள்ளம்",
        "홍수",
    ],
    "earthquake": [
        "earthquake",
        "tremor",
        "seismic",
        "magnitude",
        "aftershock",
        "rubble",
        "collapse",
        "quake",
        "richter",
        "epicenter",
        "epicentre",
        "भूकंप",
        "நிலநடுக்கம்",
        "지진",
    ],
    "cyclone": [
        "cyclone",
        "hurricane",
        "typhoon",
        "tropical storm",
        "wind speed",
        "landfall",
        "storm surge",
        "eye of the storm",
        "category",
        "चक्रवात",
        "சூறாவளி",
        "태풍",
    ],
    "tsunami": [
        "tsunami",
        "tidal wave",
        "coastal wave",
        "wave height",
        "seawave",
        "ocean surge",
        "sea surge",
        "सुनामी",
        "சுனாமி",
        "쓰나미",
    ],
    "wildfire": [
        "wildfire",
        "forest fire",
        "bushfire",
        "brushfire",
        "burning",
        "smoke",
        "evacuation",
        "blaze",
        "fire spread",
        "arson",
        "जंगल की आग",
        "காட்டுத் தீ",
        "산불",
    ],
    "landslide": [
        "landslide",
        "mudslide",
        "rockslide",
        "debris flow",
        "slope failure",
        "भूस्खलन",
        "நிலச்சரிவு",
        "산사태",
    ],
}


def classify_disaster(
    transcript: str | None = None,
    ocr_text: str | None = None,
    llm_findings: list[str] | None = None,
    video_url: str | None = None,
) -> str:
    """
    Returns the most likely disaster type as a string, or 'unknown'.
    Combines all available text signals and votes by keyword match count.
    """
    combined_text = " ".join(
        filter(
            None,
            [
                transcript or "",
                ocr_text or "",
                " ".join(llm_findings or []),
                video_url or "",
            ],
        )
    ).lower()

    if not combined_text.strip():
        return "unknown"

    scores: dict[str, int] = {dtype: 0 for dtype in DISASTER_KEYWORDS}

    for dtype, keywords in DISASTER_KEYWORDS.items():
        for kw in keywords:
            # whole-word match where possible
            pattern = re.compile(re.escape(kw.lower()))
            matches = pattern.findall(combined_text)
            scores[dtype] += len(matches)

    best_type = max(scores, key=lambda k: scores[k])
    return best_type if scores[best_type] > 0 else "unknown"
