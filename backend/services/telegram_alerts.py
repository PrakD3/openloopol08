"""Telegram alert service for high-risk Vigilens verdicts."""

import logging

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

# Alert thresholds
ALERT_CREDIBILITY_THRESHOLD = 40  # credibility below this triggers alert
ALERT_PANIC_THRESHOLD = 60  # panic index above this triggers alert

VERDICT_EMOJI = {
    "fake": "🔴",
    "misleading": "🟠",
    "real": "🟢",
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
    key_flags: list | None = None,
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
        logger.debug(
            f"[TELEGRAM] No alert needed for job {job_id[:8]} (verdict={verdict}, cred={credibility_score})"
        )
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
