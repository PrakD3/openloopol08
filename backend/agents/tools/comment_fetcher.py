"""Reddit comment fetcher and intelligence analyser."""

import json
import logging

import httpx

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Vigilens/1.0 (disaster video verification)"}


async def fetch_top_comments(url: str, limit: int = 15) -> list:
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
            comments.append(
                {
                    "author": cdata.get("author", "[deleted]"),
                    "body": body[:400],  # cap length
                    "score": cdata.get("score", 0),
                    "is_op": cdata.get("is_submitter", False),
                }
            )

        comments.sort(key=lambda c: c["score"], reverse=True)
        logger.info(f"[COMMENTS] Fetched {len(comments)} comments from Reddit post")
        return comments[:10]  # top 10 by score

    except Exception as e:
        logger.warning(f"[COMMENTS] Failed to fetch comments: {e}")
        return []


async def analyse_comments_for_intelligence(
    comments: list,
    groq_client,
    model: str,
) -> dict | None:
    """
    Ask Groq to extract intelligence from comment section:
    - Community consensus on authenticity
    - Any original source citations in comments
    - Location or date corrections
    - Debunk or confirmation signals
    """
    if not comments:
        return None

    comment_text = "\n".join([f"[Score:{c['score']}] {c['body']}" for c in comments])

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
        content = response.choices[0].message.content
        if content:
            return dict(json.loads(content))
        return None
    except Exception as e:
        logger.error(f"[COMMENTS] Groq analysis failed: {e}")
        return None
