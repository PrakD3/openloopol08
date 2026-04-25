import asyncio
import subprocess
import json
from datetime import datetime
from config.settings import settings
from agents.graph import graph
from services.video_registry import is_analyzed, mark_analyzed

async def poll_social_media():
    """
    Background loop that polls YouTube/X/Instagram for new uploads.
    """
    print("[Watcher] Social Media Monitoring started...")
    
    # Targets across different platforms
    monitored_targets = [
        "https://www.youtube.com/@Guardian/videos",      # YouTube
        "https://x.com/BBCBreaking",                      # X (Twitter)
        "https://www.instagram.com/aljazeeraenglish/reels/", # Instagram Reels
        "https://www.tiktok.com/@ndtv",                   # TikTok
    ]

    while True:
        try:
            for target in monitored_targets:
                # Use yt-dlp to get the latest 5 videos without downloading
                # --playlist-end 5 ensures we only look at the most recent
                cmd = [
                    "yt-dlp",
                    "--dump-json",
                    "--flat-playlist",
                    "--playlist-end", "5",
                    target
                ]
                
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(cmd, capture_output=True, text=True)
                )

                if result.returncode != 0:
                    continue

                for line in result.stdout.strip().split("\n"):
                    if not line: continue
                    video_data = json.loads(line)
                    video_id = video_data.get("id")
                    video_url = video_data.get("url") or f"https://www.youtube.com/watch?v={video_id}"

                    if video_id and not is_analyzed(video_id):
                        print(f"[Watcher] New video detected: {video_id}. Starting analysis...")
                        
                        # Trigger analysis graph
                        initial_state = {
                            "video_url": video_url,
                            "keyframes": [],
                            "audio_path": None,
                            "deepfake_result": None,
                            "source_result": None,
                            "context_result": None,
                            "verdict": "unverified",
                            "metadata": {"video_id": video_id}
                        }
                        
                        # Run the graph
                        result_state = await graph.ainvoke(initial_state)
                        
                        # Mark as analyzed and store verdict
                        verdict_data = {
                            "video_id": video_id,
                            "url": video_url,
                            "verdict": result_state.get("verdict"),
                            "score": result_state.get("credibility_score"),
                            "summary": result_state.get("summary"),
                            "timestamp": datetime.now().isoformat()
                        }
                        mark_analyzed(video_id, verdict_data)
                        print(f"[Watcher] Analysis complete for {video_id}: {verdict_data['verdict']}")

        except Exception as e:
            print(f"[Watcher] Error in monitoring loop: {e}")
        
        # Poll every 60 seconds
        await asyncio.sleep(60)

def start_watcher():
    """Entry point to start the background task."""
    loop = asyncio.get_event_loop()
    loop.create_task(poll_social_media())
