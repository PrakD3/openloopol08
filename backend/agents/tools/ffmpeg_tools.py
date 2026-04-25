import asyncio
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import httpx

def _candidate_paths(name: str) -> list[str]:
    root = Path(__file__).resolve().parents[3]
    candidates = [name]

    if name == "ffmpeg":
        candidates.extend(
            [
                str(root / "tools" / "ffmpeg.exe"),
                str(root / "bin" / "ffmpeg-master-latest-win64-gpl" / "bin" / "ffmpeg.exe"),
                str(root / "backend" / ".venv" / "Scripts" / "ffmpeg.exe"),
            ]
        )
    elif name == "yt-dlp":
        candidates.extend(
            [
                str(root / "backend" / ".venv" / "Scripts" / "yt-dlp.exe"),
                str(root / "backend" / ".venv" / "Scripts" / "yt-dlp"),
            ]
        )

    return candidates


def _resolve_binary(name: str) -> Optional[str]:
    for candidate in _candidate_paths(name):
        if Path(candidate).exists():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _is_reddit_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(domain in host for domain in ("reddit.com", "www.reddit.com", "old.reddit.com"))


def _append_json_suffix(url: str) -> str:
    clean = url.split("?")[0].rstrip("/")
    return f"{clean}.json?raw_json=1"


def _score_reddit_candidate(url: str, audio_only: bool) -> int:
    score = 0
    lower = url.lower()

    if "v.redd.it/" in lower:
        score += 100
    if "hlsplaylist.m3u8" in lower:
        score += 80
    if "dashplaylist.mpd" in lower:
        score += 70
    if "fallback_url" in lower:
        score += 40
    if "scrubber" in lower:
        score += 10
    if lower.endswith(".mp4") or ".mp4?" in lower:
        score += 20
    if "preview.redd.it" in lower or "external-preview.redd.it" in lower:
        score -= 80
    if "/comments/" in lower:
        score -= 100

    if audio_only:
        if "hlsplaylist.m3u8" in lower or "dashplaylist.mpd" in lower:
            score += 40
        if lower.endswith(".mp4") or ".mp4?" in lower:
            score -= 30

    return score


def _rank_reddit_candidates(candidates: list[str], audio_only: bool) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return sorted(
        deduped,
        key=lambda candidate: (_score_reddit_candidate(candidate, audio_only), len(candidate)),
        reverse=True,
    )


def _extract_reddit_video_candidates(payload: object) -> list[str]:
    candidates: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            reddit_video = node.get("reddit_video")
            if isinstance(reddit_video, dict):
                for key in ("fallback_url", "hls_url", "dash_url", "scrubber_media_url"):
                    value = reddit_video.get(key)
                    if isinstance(value, str) and value.startswith("http"):
                        candidates.append(value)

            secure_media = node.get("secure_media")
            if isinstance(secure_media, dict):
                reddit_video = secure_media.get("reddit_video")
                if isinstance(reddit_video, dict):
                    for key in ("fallback_url", "hls_url", "dash_url", "scrubber_media_url"):
                        value = reddit_video.get(key)
                        if isinstance(value, str) and value.startswith("http"):
                            candidates.append(value)

            media = node.get("media")
            if isinstance(media, dict):
                reddit_video = media.get("reddit_video")
                if isinstance(reddit_video, dict):
                    for key in ("fallback_url", "hls_url", "dash_url", "scrubber_media_url"):
                        value = reddit_video.get(key)
                        if isinstance(value, str) and value.startswith("http"):
                            candidates.append(value)

            for key in ("url_overridden_by_dest", "url", "src", "permalink"):
                value = node.get(key)
                if isinstance(value, str) and (
                    "v.redd.it/" in value
                    or value.endswith(".mp4")
                    or ".m3u8" in value
                ):
                    candidates.append(value)

            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)

    return candidates


def _extract_reddit_media_from_html(html: str) -> list[str]:
    patterns = [
        r'https://v\.redd\.it/[^"\']+/HLSPlaylist\.m3u8[^"\']*',
        r'https://v\.redd\.it/[^"\']+/DASHPlaylist\.mpd[^"\']*',
        r'https://v\.redd\.it/[^"\']+[^"\']*',
    ]
    candidates: list[str] = []
    for pattern in patterns:
        candidates.extend(re.findall(pattern, html, flags=re.IGNORECASE))
    return candidates


async def _resolve_reddit_media_url(url: str, audio_only: bool = False) -> Optional[str]:
    json_url = _append_json_suffix(url)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }
    print(f"[PREPROCESS/Reddit] Fetching Reddit JSON: {json_url}", flush=True)
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(json_url, headers=headers, timeout=30.0)
            if response.status_code != 200:
                print(
                    f"[PREPROCESS/Reddit] JSON fetch failed with HTTP {response.status_code}",
                    flush=True,
                )
                return None

            payload = response.json()
    except Exception as exc:
        print(f"[PREPROCESS/Reddit] JSON fetch failed: {exc}", flush=True)
        payload = None

    candidates: list[str] = []
    if payload is not None:
        candidates.extend(_extract_reddit_video_candidates(payload))

    # Fallback: scrape the actual Reddit page HTML for v.redd.it playback URLs.
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            html_response = await client.get(url, headers=headers, timeout=30.0)
            if html_response.status_code == 200:
                html_candidates = _extract_reddit_media_from_html(html_response.text)
                if html_candidates:
                    print(
                        f"[PREPROCESS/Reddit] Found {len(html_candidates)} HTML media candidate(s).",
                        flush=True,
                    )
                    candidates.extend(html_candidates)
    except Exception as exc:
        print(f"[PREPROCESS/Reddit] HTML scrape failed: {exc}", flush=True)

    if not candidates:
        print("[PREPROCESS/Reddit] No media candidates found in Reddit JSON or HTML.", flush=True)
        return None

    ranked = _rank_reddit_candidates(candidates, audio_only=audio_only)
    print(
        f"[PREPROCESS/Reddit] Ranked candidates: "
        f"{[candidate[:120] for candidate in ranked[:5]]}",
        flush=True,
    )
    chosen = ranked[0]
    print(
        f"[PREPROCESS/Reddit] Resolved {'audio' if audio_only else 'video'} candidate: {chosen}",
        flush=True,
    )
    return chosen


async def _run_subprocess(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")


async def _resolve_url(url: str, audio_only: bool = False) -> str:
    """
    Use yt-dlp to get a direct stream URL if the source is a web URL.
    """
    if not url.startswith(("http://", "https://")):
        return url

    if _is_reddit_url(url):
        reddit_media = await _resolve_reddit_media_url(url, audio_only=audio_only)
        if reddit_media:
            return reddit_media

    ytdlp = _resolve_binary("yt-dlp")
    if not ytdlp:
        print("[PREPROCESS] [WARNING] yt-dlp not found; using original URL directly.", flush=True)
        return url

    if audio_only:
        fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio"
        stream_label = "audio"
    else:
        fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        stream_label = "video"

    print(
        f"[PREPROCESS] Resolving {stream_label} URL with yt-dlp binary={ytdlp!r}: {url}",
        flush=True,
    )
    try:
        cmd = [
            ytdlp,
            "-g",
            "-f",
            fmt,
            "--user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--no-check-certificates",
            url,
        ]
        returncode, stdout, stderr = await _run_subprocess(cmd, timeout=60)
        if returncode == 0:
            lines = [l for l in stdout.strip().split("\n") if l.strip()]
            if not lines:
                print(
                    f"[PREPROCESS] [FAILURE] yt-dlp resolved {stream_label} with empty stdout; "
                    "falling back to original URL.",
                    flush=True,
                )
                return url
            resolved = lines[-1] if audio_only else lines[0]
            print(
                f"[PREPROCESS] [SUCCESS] {stream_label} URL resolved to stream: {resolved[:120]}",
                flush=True,
            )
            return resolved

        print(f"[PREPROCESS] [FAILURE] yt-dlp could not resolve {stream_label} URL.", flush=True)
        print(f"[PREPROCESS] [REASON] {stderr.strip() or 'Empty stderr/Process crashed'}", flush=True)
        return url
    except Exception as exc:
        print(f"[PREPROCESS] [FAILURE] Exception during yt-dlp resolution: {exc}", flush=True)
        return url


async def _download_video_locally(url: str) -> Optional[str]:
    """Download a local analysis copy when direct stream reading fails."""
    ytdlp = _resolve_binary("yt-dlp")
    if not ytdlp:
        print("[PREPROCESS] [WARNING] yt-dlp not found; local download fallback unavailable.", flush=True)
        return None

    download_dir = tempfile.mkdtemp(prefix="vigilens_video_")
    output_template = os.path.join(download_dir, "source.%(ext)s")
    cmd = [
        ytdlp,
        "--no-playlist",
        "--no-check-certificates",
        "--user-agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-f",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o",
        output_template,
        url,
    ]
    print(f"[PREPROCESS] Downloading local fallback copy with yt-dlp: {url}", flush=True)
    try:
        returncode, stdout, stderr = await _run_subprocess(cmd, timeout=180)
        if returncode != 0:
            print("[PREPROCESS] [FAILURE] yt-dlp local download failed.", flush=True)
            print(f"[PREPROCESS] [REASON] {stderr.strip() or stdout.strip() or 'No output'}", flush=True)
            return None

        files = sorted(Path(download_dir).glob("source.*"))
        if not files:
            print(
                "[PREPROCESS] [FAILURE] yt-dlp reported success but no local file was created.",
                flush=True,
            )
            return None

        local_path = str(files[0])
        print(f"[PREPROCESS] [SUCCESS] Local analysis copy ready: {local_path}", flush=True)
        return local_path
    except Exception as exc:
        print(f"[PREPROCESS] [FAILURE] Exception during local download fallback: {exc}", flush=True)
        return None


async def _extract_keyframes_opencv(
    source: str, output_dir: str, interval_seconds: int, max_frames: int
) -> List[str]:
    import cv2

    extracted_files: list[str] = []
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[PREPROCESS/OpenCV] Could not open source: {source}", flush=True)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    interval_frames = max(1, int(fps * interval_seconds))
    print(
        f"[PREPROCESS/OpenCV] Opened source. fps={fps:.2f} interval_frames={interval_frames}",
        flush=True,
    )

    count = 0
    saved_count = 0
    while saved_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if count % interval_frames == 0:
            frame_filename = os.path.join(output_dir, f"frame_{saved_count:04d}.jpg")
            ok = cv2.imwrite(frame_filename, frame)
            if ok and Path(frame_filename).exists():
                extracted_files.append(frame_filename)
                saved_count += 1
        count += 1

    cap.release()
    print(
        f"[PREPROCESS/OpenCV] Extraction finished. frames_read={count} frames_saved={len(extracted_files)}",
        flush=True,
    )
    return extracted_files


async def _extract_keyframes_ffmpeg(
    source: str, output_dir: str, interval_seconds: int, max_frames: int
) -> List[str]:
    ffmpeg = _resolve_binary("ffmpeg")
    if not ffmpeg:
        print("[PREPROCESS/FFmpeg] ffmpeg binary not found; fallback unavailable.", flush=True)
        return []

    output_pattern = os.path.join(output_dir, "frame_%04d.jpg")
    fps = 1 / max(interval_seconds, 1)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        source,
        "-vf",
        f"fps={fps}",
        "-frames:v",
        str(max_frames),
        output_pattern,
        "-loglevel",
        "error",
    ]
    print(f"[PREPROCESS/FFmpeg] Extracting keyframes with binary={ffmpeg!r} source={source}", flush=True)
    try:
        returncode, _, stderr = await _run_subprocess(cmd, timeout=120)
        if returncode != 0:
            print("[PREPROCESS/FFmpeg] Keyframe extraction failed.", flush=True)
            print(f"[PREPROCESS/FFmpeg] [REASON] {stderr.strip() or 'No stderr'}", flush=True)
            return []

        files = sorted(str(p) for p in Path(output_dir).glob("frame_*.jpg"))
        print(f"[PREPROCESS/FFmpeg] Extracted {len(files)} frame(s).", flush=True)
        return files
    except Exception as exc:
        print(f"[PREPROCESS/FFmpeg] Exception during keyframe extraction: {exc}", flush=True)
        return []


async def extract_keyframes(
    source: str, interval_seconds: int = 2, max_frames: int = 10
) -> List[str]:
    """
    Extract keyframes from a video file or URL.
    Strategy:
      1. Resolve the best video stream via yt-dlp
      2. Try OpenCV on the resolved stream
      3. Fallback to ffmpeg on the resolved stream
      4. For troublesome platforms (e.g. Reddit), download a local copy and retry
    """
    if not source:
        return []

    source = source.strip()
    resolved_source = await _resolve_url(source)
    print(
        f"[PREPROCESS] Extracting keyframes from source={source[:120]!r} "
        f"resolved={resolved_source[:120]!r}",
        flush=True,
    )

    output_dir = tempfile.mkdtemp(prefix="vigilens_frames_")
    frames = await _extract_keyframes_opencv(
        resolved_source, output_dir, interval_seconds, max_frames
    )
    if frames:
        return frames

    print("[PREPROCESS] OpenCV could not extract frames; trying ffmpeg on resolved source.", flush=True)
    frames = await _extract_keyframes_ffmpeg(
        resolved_source, output_dir, interval_seconds, max_frames
    )
    if frames:
        return frames

    if source.startswith(("http://", "https://")):
        local_copy = await _download_video_locally(source)
        if local_copy:
            print("[PREPROCESS] Retrying keyframe extraction on local downloaded copy.", flush=True)
            local_output_dir = tempfile.mkdtemp(prefix="vigilens_frames_local_")
            frames = await _extract_keyframes_opencv(
                local_copy, local_output_dir, interval_seconds, max_frames
            )
            if frames:
                return frames

            frames = await _extract_keyframes_ffmpeg(
                local_copy, local_output_dir, interval_seconds, max_frames
            )
            if frames:
                return frames

    print("[PREPROCESS] [FAILURE] All keyframe extraction strategies failed.", flush=True)
    return []


async def extract_audio(source: str) -> Optional[str]:
    """
    Extract audio track from a video file or URL.
    """
    if not source:
        return None

    ffmpeg = _resolve_binary("ffmpeg")
    if not ffmpeg:
        print("[PREPROCESS] [WARNING] ffmpeg binary not found; audio extraction unavailable.", flush=True)
        return None

    source = source.strip()
    resolved_source = await _resolve_url(source, audio_only=True)
    output_file = os.path.join(tempfile.mkdtemp(prefix="vigilens_audio_"), "audio.wav")

    print(
        f"[PREPROCESS] Extracting audio with binary={ffmpeg!r} "
        f"resolved_source={resolved_source[:120]!r}",
        flush=True,
    )
    cmd = [
        ffmpeg,
        "-i",
        resolved_source,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        output_file,
        "-y",
        "-loglevel",
        "error",
    ]

    try:
        returncode, _, stderr = await _run_subprocess(cmd, timeout=90)
        if returncode != 0:
            stderr_text = stderr.strip()
            if (
                "does not contain any stream" in stderr_text
                or "Invalid argument" in stderr_text
                or "Stream map" in stderr_text
            ):
                print(
                    "[PREPROCESS] [INFO] No usable audio stream found; audio analysis will be skipped.",
                    flush=True,
                )
            else:
                print("[PREPROCESS] [FAILURE] FFmpeg audio extraction failed.", flush=True)
                print(f"[PREPROCESS] [REASON] {stderr_text or 'No stderr'}", flush=True)
            return None

        if Path(output_file).exists():
            print(f"[PREPROCESS] [SUCCESS] Audio extracted to: {output_file}", flush=True)
            return output_file

        print("[PREPROCESS] [FAILURE] FFmpeg returned success but no audio file was created.", flush=True)
        return None
    except Exception as exc:
        print(f"[PREPROCESS] [WARNING] Audio extraction skipped: {exc}", flush=True)
        return None
