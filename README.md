# Vigilens 🛡️

**AI-powered disaster video misinformation detection.**

Vigilens analyses disaster videos in real time — detecting deepfakes, tracing the original source, and cross-referencing with disaster databases — to produce a verdict: `real`, `misleading`, `ai-generated`, or `unverified`.

> Built for the OpenLoop OL08 Hackathon.

---

## Quick Start

Uses free-tier cloud APIs. Groq is the only **required** key — everything else degrades gracefully.

---

## 🌐 Getting Started (Online Mode)

Uses free-tier cloud APIs. Groq is the only **required** key — everything else degrades gracefully.

### Prerequisites

| Tool | Min Version | Download |
|---|---|---|
| Python | 3.11+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| FFmpeg | Any | [Windows](https://ffmpeg.org/download.html) · `brew install ffmpeg` · `apt install ffmpeg` |

### One-command start

**Windows:**
```bat
scripts\start-online.bat
```

**macOS / Linux:**
```bash
bash scripts/start-online.sh
```

The script will:
1. Check prerequisites
2. Create `backend/.env` and `frontend/.env.local` from the examples
3. Open `backend/.env` in your editor so you can add your Groq key
4. Install all Python and npm packages
5. Start both servers

### Manual setup (if you prefer)

```bash
# 1. Clone
git clone https://github.com/PrakD3/openloop-OL08.git
cd openloop-OL08

# 2. Backend
cd backend
cp .env.example .env
# → Edit .env: add your GROQ_API_KEY
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-online.txt
uvicorn api.main:app --reload    # → http://localhost:8000

# 3. Frontend (new terminal)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev                      # → http://localhost:3000
```

### Free API Keys

Get these — all have generous free tiers:

| Service | Free Tier | What It Does | Get Key |
|---|---|---|---|
| **Groq** ⭐ Required | 100K tokens/day | LLM orchestrator | [console.groq.com](https://console.groq.com) |
| **Hive AI** | 100 req/day | Deepfake detection | [thehive.ai](https://thehive.ai) |
| **OpenAI** | Pay-as-you-go | Whisper transcription (cheap) | [platform.openai.com](https://platform.openai.com) |
| **Google Vision** | 1000 req/month | Reverse image search | [console.cloud.google.com](https://console.cloud.google.com) |
| **TinEye** | 150 req/month | Image history search | [services.tineye.com](https://services.tineye.com) |
| **LangSmith** | Free | Pipeline tracing (optional) | [smith.langchain.com](https://smith.langchain.com) |

> **No key? No problem.** Each API has a fallback. Missing Hive AI → pixel-variance heuristic. Missing Whisper → skip transcription. The system degrades gracefully.

---

## 🛠️ Project Structure
```

Windows helper:
```bat
scripts\start-hybrid.bat
```

macOS/Linux helper:
```bash
bash scripts/start-hybrid.sh
```

### Services (Offline Mode)

| Service | URL | What It Does |
|---|---|---|
| Frontend | http://localhost:3000 | Next.js UI |
| Backend | http://localhost:8000 | FastAPI + LangGraph |
| DeepSafe | http://localhost:8001 | Local deepfake detection |
| Ollama | http://localhost:11434 | Local LLM (Gemma 3 4B) |

---

## Environment Reference

### `backend/.env`

```env
# MODE — change this to switch between online/offline
INFERENCE_MODE=online        # online | offline
APP_MODE=real                # real | demo

# Required for online mode (free)
GROQ_API_KEY=gsk_...

# Optional — each degrades gracefully if missing
HIVE_API_KEY=                # Deepfake detection (100/day free)
OPENAI_API_KEY=              # Whisper transcription
GOOGLE_VISION_API_KEY=       # Reverse image search
TINEYE_API_KEY=              # Image history search
YOUTUBE_API_KEY=             # YouTube metadata
LANGSMITH_API_KEY=           # Pipeline tracing (optional)

# SMS alerts (optional — Twilio free trial)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
```

### `frontend/.env.local`

```env
NEXT_PUBLIC_INFERENCE_MODE=online     # online | offline (must match backend)
NEXT_PUBLIC_APP_MODE=real             # real | demo
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## Architecture

```
Next.js Frontend (port 3000)
      │  POST /api/analyze
      ▼
FastAPI Backend (port 8000)
      │  LangGraph StateGraph
      ▼
  [Preprocess]
   FFmpeg → keyframes[] + audio
      │
      ├──────────────────────────────────────────┐──────────────────────────────┐
      ▼                                          ▼                              ▼
[DeepFake Detector]                    [Source Hunter]               [Context Analyser]
 Online:  Hive AI                       Online:  Google Vision        Online:  Whisper API
 Offline: DeepSafe (Docker)             TinEye, yt-dlp               Offline: Local Whisper
 Always:  Pixel-variance heuristic      Wayback Machine               EasyOCR, GDACS DB
      │                                          │                              │
      └──────────────────────────────────────────┴──────────────────────────────┘
                                                 │
                                                 ▼
                                         [Orchestrator]
                                    Online:  Groq (llama-3.3-70b)
                                    Offline: Ollama (gemma3:4b)
                                                 │
                                                 ▼
                                         [Notification Node]
                                    SMS via Twilio (if configured)
                                                 │
                                                 ▼
                              { verdict, credibilityScore, panicIndex,
                                summary, keyFlags, notificationResult }
```

---

## Development

### Switching modes without re-running scripts

Edit `backend/.env`:
```env
INFERENCE_MODE=offline   # Switch to local AI
```

Edit `frontend/.env.local`:
```env
NEXT_PUBLIC_INFERENCE_MODE=offline
```

Then restart both servers.

### Running tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### Code style

```bash
# Backend
ruff check backend/
mypy backend/

# Frontend
cd frontend && npm run lint
```

---

## FAQ

**Q: I don't have a GPU. Can I still run offline mode?**
Yes — it falls back to CPU. Analysis will take 5–15 minutes instead of 30 seconds.

**Q: The deepfake detector says "heuristic fallback". Is that bad?**
It means Hive AI (online) or DeepSafe (offline) wasn't available. The pixel-variance heuristic still works but with ~70% accuracy instead of ~95%.

**Q: How do I get SMS alerts working?**
1. Sign up for [Twilio free trial](https://www.twilio.com/try-twilio) (~$15 credit)
2. Add `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` to `backend/.env`
3. Set `APP_MODE=real` and `NOTIFICATION_ENABLED=true`
4. Users register their location via the "Get Alerts" button on the frontend

**Q: What video URLs does it accept?**
YouTube, Twitter/X, Instagram, TikTok, Facebook, direct video URLs. Powered by yt-dlp.

---

## License

MIT — see [LICENSE](LICENSE)