# Vigilens — Sprint Patch Prompt
## Version: 1.5-PATCH | Applies on top of: vigilens-v1.md
## Stack: Next.js · FastAPI · LangGraph · Groq · Vertex AI (Google Cloud Vision)

---

## AGENT PRIME DIRECTIVE

You are patching an **already-running** Vigilens backend and frontend. The core LangGraph pipeline is functional and producing verdicts. Do NOT scaffold the project from scratch. Do NOT rename files. Do NOT change the scoring engine formula or the LangGraph graph topology unless explicitly told to in a section below.

Read every section before touching a single file. Each section has a **SCOPE** line telling you exactly which files to modify. Work section by section. Commit after each section as specified.

---

## CRITICAL CONTEXT (read before anything else)

The live pipeline currently has three silent failures. Fix these **first** — everything else depends on them:

| Failure | Symptom in logs | Root cause |
|---|---|---|
| Whisper transcription | `transcript = None` despite `audio_path` being valid | Exception swallowed silently in Whisper call |
| OCR returning empty | `ocr_text = ''` on video with visible on-screen text | OCR confidence threshold too high OR wrong frames being passed |
| Context analyser flag | `API_RESPONSE_ERROR_CONTEXT_ANALYSER` in `key_flags` | Context agent trying to analyse `None` transcript — cascades from fix #1 |

Fix these three first. The rest of the patch builds on top of working agents.

---

## SECTION 1 — FIX: Whisper Transcription Silent Failure

**SCOPE:** `backend/agents/nodes/context_analyser.py` OR wherever `audio.transcriptions.create()` is called. Also `backend/agents/state.py`.

**COMMIT:** `fix: add explicit error logging and fallback to whisper transcription node`

### 1.1 Wrap Whisper call with hard logging

Find the Groq Whisper API call (likely `client.audio.transcriptions.create(...)`). Replace the current call with this pattern:

```python
import logging
logger = logging.getLogger(__name__)

async def transcribe_audio(audio_path: str, groq_client) -> tuple[str | None, str | None]:
    """
    Returns (transcript_text, error_message).
    Never raises — always returns a tuple so callers can decide what to do.
    """
    if not audio_path or not os.path.exists(audio_path):
        logger.warning(f"[WHISPER] Audio path invalid or missing: {audio_path}")
        return None, "audio_path_invalid"

    file_size = os.path.getsize(audio_path)
    if file_size < 1000:  # less than 1KB = silent/corrupt audio
        logger.warning(f"[WHISPER] Audio file too small ({file_size} bytes), skipping transcription")
        return None, "audio_too_small"

    try:
        with open(audio_path, "rb") as audio_file:
            response = await groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=audio_file,
                response_format="text",
                language=None,  # auto-detect language
            )
        transcript = response if isinstance(response, str) else getattr(response, "text", str(response))
        logger.info(f"[WHISPER] Transcription success: {len(transcript)} chars")
        return transcript.strip(), None
    except Exception as e:
        logger.error(f"[WHISPER] Transcription failed: {type(e).__name__}: {e}")
        return None, f"whisper_error: {str(e)[:120]}"
```

### 1.2 Update AgentState to carry transcription error reason

In `backend/agents/state.py`, add:

```python
class AgentState(TypedDict):
    # ... existing fields ...
    transcript: Optional[str]
    transcript_error: Optional[str]   # NEW — reason if transcription failed
    ocr_text: Optional[str]
    ocr_error: Optional[str]          # NEW — reason if OCR failed
```

### 1.3 Update context analyser to handle None transcript gracefully

In the context analyser node, before building the LLM prompt, add a guard:

```python
transcript = state.get("transcript")
transcript_section = (
    f"AUDIO TRANSCRIPT:\n{transcript}"
    if transcript
    else "AUDIO TRANSCRIPT: [Unavailable — transcription failed or video has no speech]"
)

ocr_text = state.get("ocr_text", "")
ocr_section = (
    f"ON-SCREEN TEXT (OCR):\n{ocr_text}"
    if ocr_text
    else "ON-SCREEN TEXT: [None detected]"
)
```

Never pass `None` into an f-string or LLM prompt. If both transcript and OCR are unavailable, the context agent should still run on visual evidence alone and set confidence to 30% (low) rather than erroring.

### 1.4 Fix the error flag formatting

In the orchestrator or wherever `key_flags` is assembled, add this filter:

```python
def format_key_flags(raw_flags: list[str]) -> list[str]:
    """
    Convert internal error codes to user-readable flags.
    Raw API error strings must never reach the frontend.
    """
    flag_map = {
        "API_RESPONSE_ERROR_CONTEXT_ANALYSER": "⚠️ Context verification incomplete — partial analysis",
        "API_RESPONSE_ERROR_SOURCE_HUNTER":    "⚠️ Source tracing incomplete",
        "API_RESPONSE_ERROR_DEEPFAKE":         "⚠️ Deepfake analysis incomplete",
    }
    return [flag_map.get(f, f) for f in raw_flags if f]
```

Apply `format_key_flags()` before setting `key_flags` in the final response builder.

---

## SECTION 2 — FIX: OCR via Groq Vision (replace existing OCR)

**SCOPE:** `backend/agents/tools/ocr_tools.py` (or wherever OCR is currently called). `backend/agents/nodes/context_analyser.py`.

**COMMIT:** `fix: replace standalone OCR with Groq Vision text extraction for higher accuracy`

### 2.1 Why

The existing OCR tool (EasyOCR/Tesseract) is returning empty on frames that visibly contain on-screen text (news chyrons, watermarks, lower thirds). This is because:
- Confidence threshold is too aggressive on compressed video frames
- Standalone OCR models struggle with stylized broadcast text

Replace it entirely with a Groq Vision call on the top 3 keyframes.

### 2.2 New OCR function

In `backend/agents/tools/ocr_tools.py`, replace the current implementation with:

```python
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

async def extract_text_from_frames(
    frame_paths: list[str],
    groq_client,
    vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
) -> str:
    """
    Extract all visible text from video keyframes using Groq Vision.
    Targets chyrons, lower thirds, watermarks, channel names, timestamps,
    location overlays, breaking news banners, and street signs.
    Returns concatenated text from all frames, deduplicated.
    """
    if not frame_paths:
        return ""

    # Use top 3 frames only (middle frames tend to have clearest overlays)
    frames_to_check = frame_paths[:3] if len(frame_paths) <= 3 else [
        frame_paths[0],
        frame_paths[len(frame_paths) // 2],
        frame_paths[-1],
    ]

    all_text_chunks = []

    for frame_path in frames_to_check:
        if not Path(frame_path).exists():
            logger.warning(f"[OCR] Frame not found: {frame_path}")
            continue

        try:
            with open(frame_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            response = await groq_client.chat.completions.create(
                model=vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
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
                            )
                        }
                    ]
                }],
                max_tokens=300,
            )

            text = response.choices[0].message.content.strip()
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
```

### 2.3 Wire it into the context analyser

In the context analyser node, replace the existing OCR call with:

```python
ocr_text = await extract_text_from_frames(
    frame_paths=state.get("keyframes", []),
    groq_client=groq_client,
    vision_model=settings.vision_model,
)
state["ocr_text"] = ocr_text
```

Log the result: `logger.info(f"[CONTEXT] OCR extracted: {ocr_text[:200] if ocr_text else 'nothing'}")`

---

## SECTION 3 — NEW FEATURE: Deep Metadata + Uploader Intelligence

**SCOPE:** New file `backend/agents/tools/metadata_extractor.py`. New file `backend/agents/nodes/uploader_profiler.py`. Update `backend/agents/state.py`. Update `backend/agents/graph.py`.

**COMMIT:** `feat: add deep metadata extraction and uploader intelligence agent`

### 3.1 What this does

Pulls everything yt-dlp already has but isn't surfaced. For Reddit specifically, also queries the Reddit JSON API (no auth required). Feeds the combined metadata to a Groq call that writes a human-readable uploader credibility report.

This replaces the current minimal source result (2 findings, 0% authentic) with a proper intelligence panel.

### 3.2 Metadata extraction tool

Create `backend/agents/tools/metadata_extractor.py`:

```python
import yt_dlp
import httpx
import logging
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)


def _calc_account_age_days(info: dict) -> Optional[int]:
    """Estimate account age from channel creation date if available."""
    raw = info.get("channel_creation_date") or info.get("uploader_creation_date")
    if not raw:
        return None
    try:
        created = datetime.strptime(str(raw), "%Y%m%d").date()
        return (date.today() - created).days
    except Exception:
        return None


async def extract_platform_metadata(url: str) -> dict:
    """
    Extract deep metadata from video URL using yt-dlp.
    Works for Reddit, YouTube, Instagram, Twitter/X, TikTok.
    Returns a structured dict — never raises, returns error key on failure.
    """
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        metadata = {
            "platform":              _detect_platform(url),
            "uploader":              info.get("uploader"),
            "uploader_id":           info.get("uploader_id"),
            "uploader_url":          info.get("uploader_url"),
            "subscriber_count":      info.get("channel_follower_count"),
            "account_age_days":      _calc_account_age_days(info),
            "upload_date":           info.get("upload_date"),          # YYYYMMDD
            "upload_timestamp":      info.get("timestamp"),             # Unix epoch
            "view_count":            info.get("view_count"),
            "like_count":            info.get("like_count"),
            "comment_count":         info.get("comment_count"),
            "title":                 info.get("title", ""),
            "description":           (info.get("description") or "")[:600],
            "tags":                  info.get("tags", [])[:15],
            "categories":            info.get("categories", []),
            "original_url":          info.get("original_url") or info.get("webpage_url"),
            "duration_seconds":      info.get("duration"),
            "fps":                   info.get("fps"),
            "resolution":            f"{info.get('width', '?')}x{info.get('height', '?')}",
            "video_codec":           info.get("vcodec"),
            "audio_codec":           info.get("acodec"),
            "filesize_bytes":        info.get("filesize") or info.get("filesize_approx"),
            "age_limit":             info.get("age_limit", 0),
            "is_live":               info.get("is_live", False),
            "was_live":              info.get("was_live", False),
            "live_status":           info.get("live_status"),
            "availability":          info.get("availability"),
            "playable_in_embed":     info.get("playable_in_embed"),
        }

        logger.info(f"[METADATA] Extracted for {_detect_platform(url)}: uploader={metadata['uploader']}, date={metadata['upload_date']}")
        return metadata

    except Exception as e:
        logger.error(f"[METADATA] yt-dlp extraction failed: {e}")
        return {"error": str(e), "platform": _detect_platform(url)}


async def extract_reddit_metadata(url: str) -> dict:
    """
    For Reddit URLs: fetch additional post/author data via public Reddit JSON API.
    No OAuth required. Returns empty dict if not a Reddit URL or on failure.
    """
    if "reddit.com" not in url:
        return {}

    json_url = url.split("?")[0].rstrip("/") + ".json?limit=1"
    headers = {"User-Agent": "Vigilens/1.0 (disaster verification tool)"}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(json_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        post_data = data[0]["data"]["children"][0]["data"]

        # Fetch author profile
        author = post_data.get("author", "")
        author_data = {}
        if author and author != "[deleted]":
            try:
                author_resp = await client.get(
                    f"https://www.reddit.com/user/{author}/about.json",
                    headers=headers,
                    timeout=5.0
                )
                if author_resp.status_code == 200:
                    ainfo = author_resp.json().get("data", {})
                    created_utc = ainfo.get("created_utc", 0)
                    account_age_days = int((datetime.now().timestamp() - created_utc) / 86400) if created_utc else None
                    author_data = {
                        "account_age_days": account_age_days,
                        "post_karma":       ainfo.get("link_karma", 0),
                        "comment_karma":    ainfo.get("comment_karma", 0),
                        "is_verified":      ainfo.get("verified", False),
                        "has_verified_email": ainfo.get("has_verified_email", False),
                        "total_karma":      ainfo.get("total_karma", 0),
                    }
            except Exception as ae:
                logger.warning(f"[METADATA/Reddit] Author fetch failed: {ae}")

        return {
            "subreddit":          post_data.get("subreddit"),
            "subreddit_subscribers": post_data.get("subreddit_subscribers"),
            "post_score":         post_data.get("score"),
            "upvote_ratio":       post_data.get("upvote_ratio"),
            "num_comments":       post_data.get("num_comments"),
            "over_18":            post_data.get("over_18", False),
            "is_crosspost":       bool(post_data.get("crosspost_parent")),
            "crosspost_parent":   post_data.get("crosspost_parent"),
            "author":             author,
            "post_flair":         post_data.get("link_flair_text"),
            "author_flair":       post_data.get("author_flair_text"),
            "author_profile":     author_data,
        }

    except Exception as e:
        logger.warning(f"[METADATA/Reddit] Reddit API fetch failed: {e}")
        return {}


def _detect_platform(url: str) -> str:
    if "reddit.com" in url or "redd.it" in url: return "reddit"
    if "youtube.com" in url or "youtu.be" in url: return "youtube"
    if "instagram.com" in url: return "instagram"
    if "twitter.com" in url or "x.com" in url: return "twitter"
    if "tiktok.com" in url: return "tiktok"
    return "unknown"
```

### 3.3 Uploader profiler node

Create `backend/agents/nodes/uploader_profiler.py`:

```python
import json
import logging
from agents.state import AgentState
from agents.tools.metadata_extractor import extract_platform_metadata, extract_reddit_metadata
from config.settings import settings

logger = logging.getLogger(__name__)

UPLOADER_ANALYSIS_PROMPT = """
You are a forensic media analyst specializing in source credibility for disaster footage verification.

Analyze the following metadata about a video and its uploader. Provide a structured credibility assessment.

PLATFORM METADATA:
{platform_metadata}

REDDIT-SPECIFIC DATA (if applicable):
{reddit_metadata}

OCR TEXT FROM VIDEO (channel names, watermarks visible in frames):
{ocr_text}

Your task:
1. Assess uploader/account legitimacy (account age, follower count, karma, posting history signals)
2. Identify any temporal inconsistencies (upload date vs claimed event date)
3. Flag suspicious signals: brand-new account, no follower history, odd posting time, cross-post chains
4. Identify trust signals: verified account, established channel, consistent topic history
5. Cross-reference OCR channel names with the uploader to check for impersonation

Respond ONLY with valid JSON matching this schema exactly:
{{
  "trust_score": <integer 0-100>,
  "uploader_summary": "<2-3 sentence plain English summary of who uploaded this and their credibility>",
  "account_age_signal": "<'new_account' | 'established' | 'unknown'>",
  "red_flags": ["<flag1>", "<flag2>"],
  "trust_signals": ["<signal1>", "<signal2>"],
  "temporal_note": "<observation about upload timing relative to any event claims, or null>",
  "platform_notes": "<any platform-specific observations>"
}}
"""

async def run(state: AgentState) -> AgentState:
    logger.info(f"[UPLOADER_PROFILER] Starting for job {state.get('job_id', '?')}")

    video_url = state.get("video_url", "")
    ocr_text = state.get("ocr_text", "") or ""

    # Extract metadata
    platform_meta = await extract_platform_metadata(video_url)
    reddit_meta = await extract_reddit_metadata(video_url)

    # Store raw metadata in state
    state["platform_metadata"] = platform_meta
    state["reddit_metadata"] = reddit_meta

    # Build uploader intelligence via Groq
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.groq_api_key)

        prompt = UPLOADER_ANALYSIS_PROMPT.format(
            platform_metadata=json.dumps(platform_meta, indent=2, default=str),
            reddit_metadata=json.dumps(reddit_meta, indent=2, default=str) if reddit_meta else "N/A",
            ocr_text=ocr_text[:400] if ocr_text else "Not available",
        )

        response = await client.chat.completions.create(
            model=settings.orchestrator_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        uploader_intelligence = json.loads(raw)
        logger.info(f"[UPLOADER_PROFILER] Trust score: {uploader_intelligence.get('trust_score')}")

    except Exception as e:
        logger.error(f"[UPLOADER_PROFILER] Groq analysis failed: {e}")
        uploader_intelligence = {
            "trust_score": 50,
            "uploader_summary": "Uploader analysis unavailable.",
            "account_age_signal": "unknown",
            "red_flags": [],
            "trust_signals": [],
            "temporal_note": None,
            "platform_notes": f"Analysis error: {str(e)[:80]}",
        }

    state["uploader_intelligence"] = uploader_intelligence
    return state
```

### 3.4 Add new fields to AgentState

In `backend/agents/state.py`, add:

```python
class AgentState(TypedDict):
    # ... all existing fields ...
    platform_metadata:     Optional[dict]   # raw yt-dlp output
    reddit_metadata:       Optional[dict]   # reddit API output (None for non-reddit)
    uploader_intelligence: Optional[dict]   # Groq-generated uploader credibility report
```

### 3.5 Register the node in graph.py

In `backend/agents/graph.py`, import and add the uploader profiler to the `ANALYSIS_AGENTS` registry:

```python
from agents.nodes import uploader_profiler

ANALYSIS_AGENTS: list[tuple[str, callable]] = [
    ("deepfake_detector",  deepfake_detector.run),
    ("source_hunter",      source_hunter.run),
    ("context_analyser",   context_analyser.run),
    ("uploader_profiler",  uploader_profiler.run),  # NEW
]
```

---

## SECTION 4 — NEW FEATURE: Google Vision Reverse Frame Search

**SCOPE:** New file `backend/agents/tools/reverse_search.py`. Update `backend/agents/nodes/source_hunter.py`.

**COMMIT:** `feat: add Google Vision Web Detection for reverse frame search and temporal displacement`

### 4.1 Why

The current Source Hunter scores 0% with 2 findings ("earliest known appearance" + "no GPS metadata"). This is because no actual reverse search is running. This section wires in Google Vision Web Detection using your Vertex AI credentials — this uses your $1000 credits and is billed per API call.

### 4.2 Reverse search tool

Create `backend/agents/tools/reverse_search.py`:

```python
import base64
import logging
from pathlib import Path
from typing import Optional
from google.cloud import vision

logger = logging.getLogger(__name__)


def _get_vision_client() -> vision.ImageAnnotatorClient:
    """Returns authenticated Google Vision client using application default credentials."""
    return vision.ImageAnnotatorClient()


async def reverse_search_keyframes(
    frame_paths: list[str],
    max_frames: int = 3
) -> dict:
    """
    Run Google Vision Web Detection on keyframes to find prior appearances
    of the video content. This catches temporal displacement (real footage,
    wrong time context) that deepfake detectors cannot catch.

    Returns structured results including prior appearance URLs, dates,
    and matching page context.
    """
    if not frame_paths:
        return {"status": "no_frames", "matches": [], "earliest_appearance": None}

    # Select best frames: first, middle, last
    if len(frame_paths) <= max_frames:
        selected = frame_paths
    else:
        selected = [
            frame_paths[0],
            frame_paths[len(frame_paths) // 2],
            frame_paths[-1],
        ]

    try:
        client = _get_vision_client()
    except Exception as e:
        logger.error(f"[REVERSE_SEARCH] Failed to init Vision client: {e}")
        return {"status": "client_error", "error": str(e), "matches": []}

    all_results = []
    best_guess_labels = []
    full_match_urls = []
    partial_match_urls = []
    matching_pages = []

    for frame_path in selected:
        if not Path(frame_path).exists():
            continue

        try:
            with open(frame_path, "rb") as f:
                content = f.read()

            image = vision.Image(content=content)
            response = client.web_detection(image=image)

            if response.error.message:
                logger.warning(f"[REVERSE_SEARCH] Vision API error on {Path(frame_path).name}: {response.error.message}")
                continue

            web = response.web_detection

            # Collect best guess labels (what Google thinks this is)
            for label in web.best_guess_labels:
                if label.label not in best_guess_labels:
                    best_guess_labels.append(label.label)

            # Full matching images (exact same image found elsewhere)
            for img in web.full_matching_images[:5]:
                if img.url not in full_match_urls:
                    full_match_urls.append(img.url)

            # Partial matches (similar images)
            for img in web.partial_matching_images[:5]:
                if img.url not in partial_match_urls:
                    partial_match_urls.append(img.url)

            # Pages containing matching images
            for page in web.pages_with_matching_images[:8]:
                page_info = {
                    "url": page.url,
                    "title": page.page_title if hasattr(page, "page_title") else "",
                }
                if page_info not in matching_pages:
                    matching_pages.append(page_info)

            logger.info(
                f"[REVERSE_SEARCH] Frame {Path(frame_path).name}: "
                f"{len(web.full_matching_images)} full matches, "
                f"{len(web.pages_with_matching_images)} pages"
            )

        except Exception as e:
            logger.error(f"[REVERSE_SEARCH] Failed on frame {frame_path}: {e}")
            continue

    # Determine temporal displacement risk
    temporal_displacement_risk = "low"
    if len(full_match_urls) > 3:
        temporal_displacement_risk = "high"   # widely circulated before
    elif len(full_match_urls) > 0:
        temporal_displacement_risk = "medium"

    result = {
        "status": "complete",
        "frames_searched": len(selected),
        "best_guess_labels": best_guess_labels,
        "full_match_urls": full_match_urls,          # exact prior appearances
        "partial_match_urls": partial_match_urls,
        "matching_pages": matching_pages[:10],
        "temporal_displacement_risk": temporal_displacement_risk,
        "prior_appearances_count": len(full_match_urls),
        "earliest_known_page": matching_pages[0] if matching_pages else None,
    }

    logger.info(
        f"[REVERSE_SEARCH] Complete: {len(full_match_urls)} full matches, "
        f"temporal risk={temporal_displacement_risk}"
    )
    return result
```

### 4.3 Integrate into Source Hunter

In `backend/agents/nodes/source_hunter.py`, add the reverse search call alongside existing metadata extraction:

```python
from agents.tools.reverse_search import reverse_search_keyframes

# Inside the source_hunter run() function, add:
reverse_results = await reverse_search_keyframes(
    frame_paths=state.get("keyframes", []),
    max_frames=3,
)

# Add findings from reverse search
if reverse_results.get("prior_appearances_count", 0) > 0:
    source_findings.append(
        f"Prior appearances found: {reverse_results['prior_appearances_count']} matching pages"
    )
    if reverse_results["temporal_displacement_risk"] == "high":
        source_findings.append(
            "⚠️ HIGH temporal displacement risk — this footage has been widely circulated before"
        )
    source_findings.append(
        f"Content identified as: {', '.join(reverse_results.get('best_guess_labels', []))}"
    )
else:
    source_findings.append("No prior appearances found in Google Vision index")

# Store in state
state["reverse_search_result"] = reverse_results
```

### 4.4 Add to AgentState

```python
class AgentState(TypedDict):
    # ... existing fields ...
    reverse_search_result: Optional[dict]
```

### 4.5 Install dependency

Add to `backend/requirements.txt`:
```
google-cloud-vision>=3.7.0
```

Ensure `GOOGLE_APPLICATION_CREDENTIALS` environment variable points to your service account JSON, OR use Vertex AI application default credentials if already configured.

---

## SECTION 5 — NEW FEATURE: Reddit Comment Intelligence

**SCOPE:** New file `backend/agents/tools/comment_fetcher.py`. Update `backend/agents/nodes/uploader_profiler.py`.

**COMMIT:** `feat: add Reddit comment intelligence — community consensus extraction`

### 5.1 What this does

For Reddit URLs, fetches the top 10 comments (public API, no auth) and asks Groq to extract community consensus, original source claims, location information, and authenticity signals. This catches cases where comment sections have already debunked or confirmed a video.

### 5.2 Comment fetcher tool

Create `backend/agents/tools/comment_fetcher.py`:

```python
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Vigilens/1.0 (disaster video verification)"}


async def fetch_top_comments(url: str, limit: int = 15) -> list[dict]:
    """
    Fetch top comments from Reddit post.
    Returns list of {author, body, score, created_utc} dicts.
    Returns empty list for non-Reddit URLs or on failure.
    """
    if "reddit.com" not in url and "redd.it" not in url:
        return []

    # Ensure we have the canonical reddit.com URL (not redd.it short link)
    if "redd.it" in url:
        logger.info("[COMMENTS] Short URL detected — skipping comment fetch (resolve URL first)")
        return []

    json_url = url.split("?")[0].rstrip("/") + f".json?limit={limit}&sort=top"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(json_url, headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()

        if len(data) < 2:
            return []

        comments_listing = data[1]["data"]["children"]
        comments = []

        for item in comments_listing:
            if item.get("kind") != "t1":  # t1 = comment
                continue
            cdata = item.get("data", {})
            body = cdata.get("body", "").strip()
            if body in ("[deleted]", "[removed]", "") or len(body) < 10:
                continue
            comments.append({
                "author": cdata.get("author", "[deleted]"),
                "body":   body[:400],           # cap length
                "score":  cdata.get("score", 0),
                "is_op":  cdata.get("is_submitter", False),
            })

        comments.sort(key=lambda c: c["score"], reverse=True)
        logger.info(f"[COMMENTS] Fetched {len(comments)} comments from Reddit post")
        return comments[:10]  # top 10 by score

    except Exception as e:
        logger.warning(f"[COMMENTS] Failed to fetch comments: {e}")
        return []


async def analyse_comments_for_intelligence(
    comments: list[dict],
    groq_client,
    model: str,
) -> Optional[dict]:
    """
    Ask Groq to extract intelligence from comment section:
    - Community consensus on authenticity
    - Any original source citations in comments
    - Location or date corrections
    - Debunk or confirmation signals
    """
    if not comments:
        return None

    comment_text = "\n".join([
        f"[Score:{c['score']}] {c['body']}"
        for c in comments
    ])

    prompt = f"""Analyze these comments from a social media post containing disaster/news footage.

COMMENTS (sorted by score/upvotes):
{comment_text}

Extract the following and respond ONLY in valid JSON:
{{
  "community_verdict": "<'confirms_real' | 'disputes_authenticity' | 'mixed' | 'unclear'>",
  "consensus_summary": "<1-2 sentences summarizing what commenters collectively say about this video>",
  "original_source_claims": ["<any URLs or source claims mentioned in comments>"],
  "location_corrections": ["<if commenters dispute the claimed location>"],
  "date_corrections": ["<if commenters cite an earlier/different date for this footage>"],
  "debunk_signals": ["<direct quotes or paraphrases from comments debunking the video>"],
  "confirm_signals": ["<direct quotes or paraphrases confirming authenticity>"],
  "notable_comment": "<most informative single comment for verification purposes, or null>"
}}"""

    try:
        response = await groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"[COMMENTS] Groq analysis failed: {e}")
        return None
```

### 5.3 Wire into uploader profiler

In `backend/agents/nodes/uploader_profiler.py`, add at the end of the `run()` function (after uploader intelligence is computed):

```python
from agents.tools.comment_fetcher import fetch_top_comments, analyse_comments_for_intelligence

# Fetch and analyse comments
comments = await fetch_top_comments(video_url, limit=15)
comment_intelligence = None
if comments:
    comment_intelligence = await analyse_comments_for_intelligence(
        comments=comments,
        groq_client=client,
        model=settings.orchestrator_model,
    )
    logger.info(f"[UPLOADER_PROFILER] Comment analysis: {comment_intelligence.get('community_verdict') if comment_intelligence else 'failed'}")

state["comments_raw"] = comments
state["comment_intelligence"] = comment_intelligence
```

### 5.4 Add to AgentState

```python
class AgentState(TypedDict):
    # ... existing fields ...
    comments_raw:         Optional[list]   # raw top comments
    comment_intelligence: Optional[dict]   # Groq-extracted comment intelligence
```

---

## SECTION 6 — NEW FEATURE: Telegram Alert System

**SCOPE:** New file `backend/services/telegram_alerts.py`. Update `backend/agents/nodes/orchestrator.py`.

**COMMIT:** `feat: add Telegram alert system for high-risk verdicts`

### 6.1 Alert service

Create `backend/services/telegram_alerts.py`:

```python
import httpx
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

# Alert thresholds
ALERT_CREDIBILITY_THRESHOLD = 40    # credibility below this triggers alert
ALERT_PANIC_THRESHOLD       = 60    # panic index above this triggers alert

VERDICT_EMOJI = {
    "fake":       "🔴",
    "misleading": "🟠",
    "real":       "🟢",
    "unverified": "⚪",
}


async def send_verdict_alert(
    job_id: str,
    verdict: str,
    credibility_score: int,
    panic_index: int,
    video_url: str,
    summary: str,
    actual_location: str | None = None,
    key_flags: list[str] | None = None,
) -> bool:
    """
    Send Telegram alert for high-risk verdicts.
    Only sends if credibility < threshold OR panic > threshold.
    Returns True if sent, False if skipped or failed.
    """
    if not settings.telegram_bot_token or not settings.telegram_channel_id:
        logger.debug("[TELEGRAM] Not configured — skipping alert")
        return False

    # Only alert on genuinely suspicious verdicts
    should_alert = (
        verdict in ("fake", "misleading")
        or credibility_score < ALERT_CREDIBILITY_THRESHOLD
        or panic_index > ALERT_PANIC_THRESHOLD
    )

    if not should_alert:
        logger.debug(f"[TELEGRAM] No alert needed for job {job_id[:8]} (verdict={verdict}, cred={credibility_score})")
        return False

    emoji = VERDICT_EMOJI.get(verdict.lower(), "⚪")
    flags_text = ""
    if key_flags:
        clean_flags = [f for f in key_flags if not f.startswith("API_RESPONSE_ERROR")]
        if clean_flags:
            flags_text = "\n🏴 *Flags:* " + " | ".join(clean_flags[:3])

    location_text = f"\n📍 *Location:* {actual_location}" if actual_location else ""

    short_url = video_url[:70] + "..." if len(video_url) > 70 else video_url
    analysis_link = f"https://vigilens.app/v/{job_id}" if job_id else ""

    message = (
        f"{emoji} *VIGILENS ALERT*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"*Verdict:* {verdict.upper()}\n"
        f"*Credibility:* {credibility_score}/100\n"
        f"*Panic Index:* {panic_index}/100"
        f"{location_text}"
        f"{flags_text}\n\n"
        f"📹 `{short_url}`\n\n"
        f"_{summary[:180]}..._"
        + (f"\n\n🔗 [Full Analysis]({analysis_link})" if analysis_link else "")
    )

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": settings.telegram_channel_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
            if resp.status_code == 200:
                logger.info(f"[TELEGRAM] Alert sent for job {job_id[:8]} (verdict={verdict})")
                return True
            else:
                logger.warning(f"[TELEGRAM] API returned {resp.status_code}: {resp.text[:100]}")
                return False

    except Exception as e:
        logger.error(f"[TELEGRAM] Failed to send alert: {e}")
        return False
```

### 6.2 Add Telegram settings

In `backend/config/settings.py`, add:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    telegram_bot_token:  str | None = None
    telegram_channel_id: str | None = None   # e.g. "@vigilens_alerts" or numeric chat_id
```

In `backend/.env.example`, add:
```env
# ── TELEGRAM ALERTS (optional — leave blank to disable) ────────────────────────
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_ID=@vigilens_alerts
```

### 6.3 Wire into orchestrator

In `backend/agents/nodes/orchestrator.py`, at the end of the `run()` function after the final verdict is set:

```python
from services.telegram_alerts import send_verdict_alert

# Send Telegram alert (non-blocking — don't await if it slows the response)
import asyncio
asyncio.create_task(send_verdict_alert(
    job_id=state.get("job_id", ""),
    verdict=state.get("verdict", "unverified"),
    credibility_score=state.get("credibility_score", 50),
    panic_index=state.get("panic_index", 0),
    video_url=state.get("video_url", ""),
    summary=state.get("summary", ""),
    actual_location=state.get("actual_location"),
    key_flags=state.get("key_flags", []),
))
```

### 6.4 Telegram bot setup (do this manually — 5 minutes)

1. Message `@BotFather` on Telegram → `/newbot` → name it "Vigilens Alerts" → get token
2. Create a public channel named `vigilens_alerts` → add your bot as admin
3. Set `TELEGRAM_CHANNEL_ID=@vigilens_alerts` in `.env`
4. Test: send any video URL, if panic > 60 you should see the alert appear in the channel within seconds

---

## SECTION 7 — NEW FEATURE: Trained Model Integration

**SCOPE:** New file `backend/ml/custom_model.py`. Update `backend/ml/scoring_engine.py`.

**COMMIT:** `feat: integrate custom trained deepfake detection model into scoring engine`

### 7.1 Context

The scoring engine currently uses:
`Score = (0.60 * ConstraintScore) + (0.40 * MLModelScore)`

The `MLModelScore` is currently simulated/deterministic. Your friend's trained model slots into this `MLModelScore` component. This section provides adapters for the two most common model output formats.

### 7.2 Model loader with format detection

Create `backend/ml/custom_model.py`:

```python
import logging
import numpy as np
from pathlib import Path
from typing import Optional
import base64

logger = logging.getLogger(__name__)

# Path to your friend's model — set via env or place in backend/ml/weights/
MODEL_PATH = Path(__file__).parent / "weights" / "custom_deepfake_detector"


def load_model():
    """
    Auto-detect model format and load. Supports:
    - PyTorch checkpoint (.pt / .pth)
    - scikit-learn pickle (.pkl / .joblib)
    - ONNX (.onnx) — recommended for cross-platform use
    - HuggingFace local directory
    """
    if not MODEL_PATH.exists():
        logger.warning(f"[CUSTOM_MODEL] No model found at {MODEL_PATH} — will skip custom scoring")
        return None, None

    # Check for ONNX (fastest, no framework dependency)
    onnx_path = list(MODEL_PATH.glob("*.onnx"))
    if onnx_path:
        try:
            import onnxruntime as ort
            session = ort.InferenceSession(str(onnx_path[0]))
            logger.info(f"[CUSTOM_MODEL] Loaded ONNX model: {onnx_path[0].name}")
            return session, "onnx"
        except ImportError:
            logger.warning("[CUSTOM_MODEL] onnxruntime not installed — falling back")

    # Check for PyTorch checkpoint
    pt_paths = list(MODEL_PATH.glob("*.pt")) + list(MODEL_PATH.glob("*.pth"))
    if pt_paths:
        try:
            import torch
            model = torch.load(pt_paths[0], map_location="cpu")
            model.eval()
            logger.info(f"[CUSTOM_MODEL] Loaded PyTorch model: {pt_paths[0].name}")
            return model, "pytorch"
        except Exception as e:
            logger.error(f"[CUSTOM_MODEL] PyTorch load failed: {e}")

    # Check for sklearn pickle
    pkl_paths = list(MODEL_PATH.glob("*.pkl")) + list(MODEL_PATH.glob("*.joblib"))
    if pkl_paths:
        try:
            import joblib
            model = joblib.load(pkl_paths[0])
            logger.info(f"[CUSTOM_MODEL] Loaded sklearn model: {pkl_paths[0].name}")
            return model, "sklearn"
        except Exception as e:
            logger.error(f"[CUSTOM_MODEL] sklearn load failed: {e}")

    logger.warning("[CUSTOM_MODEL] No loadable model found in weights directory")
    return None, None


def score_frames_with_custom_model(
    frame_paths: list[str],
    model,
    model_type: str,
) -> Optional[float]:
    """
    Run inference on keyframes and return a single deepfake probability (0.0-1.0).
    Returns None if model unavailable or inference fails.
    0.0 = definitely real, 1.0 = definitely AI-generated.
    """
    if model is None or not frame_paths:
        return None

    try:
        from PIL import Image
        import torchvision.transforms as T

        transform = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        scores = []
        for fp in frame_paths[:5]:
            if not Path(fp).exists():
                continue
            img = Image.open(fp).convert("RGB")
            tensor = transform(img).unsqueeze(0)

            if model_type == "pytorch":
                import torch
                with torch.no_grad():
                    output = model(tensor)
                    if output.shape[-1] == 1:
                        prob = torch.sigmoid(output).item()
                    else:
                        prob = torch.softmax(output, dim=-1)[0][1].item()
                scores.append(prob)

            elif model_type == "onnx":
                input_name = model.get_inputs()[0].name
                output = model.run(None, {input_name: tensor.numpy()})
                # Assume output[0] is logit or probability
                raw = float(output[0].flatten()[0])
                prob = 1 / (1 + np.exp(-raw)) if raw > 1 else raw
                scores.append(prob)

        if not scores:
            return None

        avg_score = sum(scores) / len(scores)
        logger.info(f"[CUSTOM_MODEL] Inference on {len(scores)} frames: avg_fake_prob={avg_score:.3f}")
        return avg_score

    except Exception as e:
        logger.error(f"[CUSTOM_MODEL] Inference failed: {e}")
        return None


# Load model at module import time (cached for lifetime of process)
_model, _model_type = load_model()


def get_custom_deepfake_score(frame_paths: list[str]) -> Optional[float]:
    """Public interface — call this from scoring engine."""
    return score_frames_with_custom_model(frame_paths, _model, _model_type)
```

### 7.3 Plug into scoring engine

In `backend/ml/scoring_engine.py`, update `score_deepfake()` to incorporate the custom model:

```python
from ml.custom_model import get_custom_deepfake_score

def score_deepfake(self, constraint_values: dict, frame_paths: list[str] = None) -> AgentScore:
    # ... existing constraint scoring ...
    constraint_score = self._compute_constraint_score(constraint_values, DEEPFAKE_CONSTRAINTS)

    # Use custom trained model if available
    ml_score = None
    if frame_paths:
        custom_prob = get_custom_deepfake_score(frame_paths)
        if custom_prob is not None:
            # custom_prob is 0-1 fake probability; invert for "realness" score
            ml_score = (1.0 - custom_prob) * 100
            logger.info(f"[SCORING] Custom model ML score: {ml_score:.1f} (fake_prob={custom_prob:.3f})")

    if ml_score is None:
        ml_score = self._deterministic_ml_score()   # existing fallback

    final_score = (0.60 * constraint_score) + (0.40 * ml_score)
    return self._build_agent_score("deepfake", final_score, constraint_score, ml_score)
```

### 7.4 Drop the model weights

Place your friend's model file(s) at: `backend/ml/weights/custom_deepfake_detector/`

Supported structures:
```
backend/ml/weights/custom_deepfake_detector/
├── model.onnx          ← preferred
├── model.pt            ← PyTorch
├── model.pkl           ← sklearn
└── model.joblib        ← sklearn (alternative)
```

Add to `.gitignore`:
```
backend/ml/weights/
```

---

## SECTION 8 — UI FIXES

**SCOPE:** Frontend components. Primarily `VerdictCard.tsx`, `AgentPanel.tsx`, and whatever component renders the source result.

**COMMIT:** `fix: UI corrections — flag formatting, source confidence labeling, location card color, share button`

### 8.1 Never show raw API error strings as flags

In `VerdictCard.tsx` (or wherever key_flags are rendered), add a filter:

```typescript
const FLAG_DISPLAY_MAP: Record<string, string> = {
  "API_RESPONSE_ERROR_CONTEXT_ANALYSER": "⚠️ Context verification incomplete",
  "API_RESPONSE_ERROR_SOURCE_HUNTER":    "⚠️ Source tracing incomplete",
  "API_RESPONSE_ERROR_DEEPFAKE":         "⚠️ Deepfake analysis incomplete",
};

const displayFlags = (flags: string[]) =>
  flags
    .filter(Boolean)
    .map(f => FLAG_DISPLAY_MAP[f] ?? f);
```

Apply `displayFlags(keyFlags)` everywhere flags are rendered.

### 8.2 Fix source result zero-state label

When `source_result.score === 0` AND `source_result.findings_count <= 2`, do NOT render "0% AUTHENTIC". That reads as "definitely fake." Instead render:

```typescript
const getSourceLabel = (score: number, findingsCount: number) => {
  if (findingsCount <= 2 && score === 0) return "INSUFFICIENT DATA";
  if (score < 30) return "LOW CONFIDENCE";
  if (score < 70) return "PARTIAL CONFIDENCE";
  return `${score}% AUTHENTIC`;
};
```

### 8.3 Fix location card color

The `ACTUAL LOCATION` card uses red/destructive background which reads as "warning" even when the verdict is REAL. Change to neutral-info styling:

```typescript
// Before:
<div className="bg-destructive/10 border-destructive text-destructive">

// After:
<div className="bg-muted border-border text-foreground">
```

Location is informational, not alarming. Reserve red exclusively for flagged/fake verdicts.

### 8.4 Add new UI panels for new data

Add these three collapsible panels to the analysis page, rendered after the existing three agent panels:

**Uploader Intelligence panel** — shows `uploader_intelligence.trust_score` as a ring, `uploader_intelligence.uploader_summary` as text, and `red_flags` / `trust_signals` as badge lists. Header: "SOURCE INTELLIGENCE".

**Reverse Search panel** — shows `reverse_search_result.prior_appearances_count`, `temporal_displacement_risk` as a color-coded badge (green/yellow/red), and `matching_pages` as a list of linked URLs. Header: "REVERSE SEARCH".

**Comment Intelligence panel** — shows `comment_intelligence.community_verdict` as a badge, `consensus_summary` as text, and `notable_comment` in a blockquote. Only render if `comments_raw.length > 0`. Header: "COMMUNITY INTELLIGENCE".

All three panels should be collapsed by default and expand on click — keeping the UI clean while making the data accessible.

### 8.5 Wire ANALYSIS.SHAREREPORT button

The share button must:
1. Copy `https://vigilens.app/v/{job_id}` to clipboard
2. Show a brief "Link copied!" toast (use your existing sonner/toast)
3. If `job_id` is missing, show "Share unavailable — analysis in progress"

```typescript
const handleShare = async () => {
  if (!jobId) {
    toast.error("Share unavailable — analysis still in progress");
    return;
  }
  const shareUrl = `${window.location.origin}/v/${jobId}`;
  await navigator.clipboard.writeText(shareUrl);
  toast.success("Analysis link copied to clipboard");
};
```

Ensure the `/v/[jobId]` route exists and fetches from `GET /status/{job_id}` — a job must be persisted in Supabase/DB for this link to survive a server restart.

---

## SECTION 9 — RESPONSE MODEL UPDATES

**SCOPE:** `backend/api/models.py`, `backend/api/routes/analyze.py` (or wherever `AnalyzeResponse` is built).

**COMMIT:** `feat: extend AnalyzeResponse to include uploader intelligence, comments, and reverse search`

### 9.1 Add new fields to AnalyzeResponse

```python
class UploaderIntelligence(BaseModel):
    trust_score:          int
    uploader_summary:     str
    account_age_signal:   str
    red_flags:            list[str] = []
    trust_signals:        list[str] = []
    temporal_note:        Optional[str] = None
    platform_notes:       Optional[str] = None

class ReverseSearchResult(BaseModel):
    status:                     str
    prior_appearances_count:    int = 0
    temporal_displacement_risk: str = "low"
    best_guess_labels:          list[str] = []
    matching_pages:             list[dict] = []
    earliest_known_page:        Optional[dict] = None

class CommentIntelligence(BaseModel):
    community_verdict:     str
    consensus_summary:     str
    original_source_claims: list[str] = []
    location_corrections:  list[str] = []
    date_corrections:      list[str] = []
    debunk_signals:        list[str] = []
    confirm_signals:       list[str] = []
    notable_comment:       Optional[str] = None

class AnalyzeResponse(BaseModel):
    # ... all existing fields ...
    uploader_intelligence: Optional[UploaderIntelligence] = None
    reverse_search:        Optional[ReverseSearchResult] = None
    comment_intelligence:  Optional[CommentIntelligence] = None
    platform_metadata:     Optional[dict] = None
    reddit_metadata:       Optional[dict] = None
```

### 9.2 Populate in response builder

In the function that builds `AnalyzeResponse` from `final_state`, map the new state fields:

```python
uploader_intelligence=(
    UploaderIntelligence(**final_state["uploader_intelligence"])
    if final_state.get("uploader_intelligence") else None
),
reverse_search=(
    ReverseSearchResult(**final_state["reverse_search_result"])
    if final_state.get("reverse_search_result") else None
),
comment_intelligence=(
    CommentIntelligence(**final_state["comment_intelligence"])
    if final_state.get("comment_intelligence") else None
),
platform_metadata=final_state.get("platform_metadata"),
reddit_metadata=final_state.get("reddit_metadata"),
```

---

## SECTION 10 — ENVIRONMENT & DEPENDENCY SUMMARY

**SCOPE:** `backend/.env.example`, `backend/requirements.txt`

**COMMIT:** `chore: update env example and requirements for patch features`

### 10.1 New env vars

Add to `backend/.env.example`:

```env
# ── GOOGLE CLOUD (for Vision Web Detection reverse search) ─────────────────────
GOOGLE_APPLICATION_CREDENTIALS=./gcloud-service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id

# ── TELEGRAM ALERTS (optional — leave blank to disable) ────────────────────────
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_ID=@vigilens_alerts

# ── CUSTOM MODEL (optional — place weights in backend/ml/weights/) ──────────────
CUSTOM_MODEL_ENABLED=true
```

### 10.2 New Python dependencies

Add to `backend/requirements.txt`:

```
google-cloud-vision>=3.7.0
onnxruntime>=1.18.0
Pillow>=10.0.0
httpx>=0.27.0          # likely already present
```

---

## SECTION 11 — FINAL CHECKLIST

Before considering this patch complete, verify each item:

- [ ] `transcript` is no longer `None` on videos with speech — check logs for `[WHISPER] Transcription success`
- [ ] `ocr_text` contains on-screen text (e.g. channel names visible in frames) — check logs for `[OCR] Frame`
- [ ] `API_RESPONSE_ERROR_CONTEXT_ANALYSER` no longer appears as a raw flag in frontend
- [ ] `source_result` panel shows "INSUFFICIENT DATA" rather than "0% AUTHENTIC" when data is sparse
- [ ] `ACTUAL LOCATION` card uses neutral (not red) styling
- [ ] New "SOURCE INTELLIGENCE" panel renders with trust score and uploader summary
- [ ] New "REVERSE SEARCH" panel renders with prior appearances count and temporal risk badge
- [ ] New "COMMUNITY INTELLIGENCE" panel renders when Reddit comments are available
- [ ] `ANALYSIS.SHAREREPORT` button copies a valid URL and shows toast confirmation
- [ ] Telegram bot receives an alert when a test video with low credibility is submitted
- [ ] Custom model loads on startup if weights are present — check for `[CUSTOM_MODEL] Loaded` log line
- [ ] No regression on existing test videos — pipeline still completes in < 60s
- [ ] All `key_flags` with `API_RESPONSE_ERROR` prefix are mapped to human-readable strings before reaching the frontend

---

*Vigilens Patch v1.5 — Engineering Truth, One Frame at a Time.*
