import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

print("--- Vigilens Backend Smoke Test ---")

try:
    from backend.config.settings import settings
    print("✅ Settings loaded")
except Exception as e:
    print(f"❌ Settings failed: {e}")

try:
    from backend.agents.graph import graph
    print("✅ LangGraph logic loaded")
except Exception as e:
    print(f"❌ LangGraph failed: {e}")

try:
    from backend.services.video_registry import is_analyzed
    print("✅ Video Registry loaded")
except Exception as e:
    print(f"❌ Video Registry failed: {e}")

try:
    from backend.services.social_monitor import start_watcher
    print("✅ Social Monitor loaded")
except Exception as e:
    print(f"❌ Social Monitor failed: {e}")

print("--- Test Complete ---")
