"""Reverse frame search using Google Vision Web Detection."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_vision_client():
    """Returns authenticated Google Vision client using application default credentials."""
    from google.cloud import vision

    return vision.ImageAnnotatorClient()


async def reverse_search_keyframes(frame_paths: list, max_frames: int = 3) -> dict:
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
        from google.cloud import vision

        client = _get_vision_client()
    except Exception as e:
        logger.error(f"[REVERSE_SEARCH] Failed to init Vision client: {e}")
        return {
            "status": "client_error",
            "error": str(e),
            "matches": [],
            "prior_appearances_count": 0,
            "temporal_displacement_risk": "low",
        }

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

            from google.cloud import vision

            image = vision.Image(content=content)
            response = client.web_detection(image=image)

            if response.error.message:
                logger.warning(
                    f"[REVERSE_SEARCH] Vision API error on {Path(frame_path).name}: {response.error.message}"
                )
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
        temporal_displacement_risk = "high"  # widely circulated before
    elif len(full_match_urls) > 0:
        temporal_displacement_risk = "medium"

    result = {
        "status": "complete",
        "frames_searched": len(selected),
        "best_guess_labels": best_guess_labels,
        "full_match_urls": full_match_urls,  # exact prior appearances
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
