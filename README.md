# Vigilens 🛡️

**AI-powered disaster video misinformation detection.**

Vigilens analyses disaster videos in real time — detecting deepfakes, tracing the original source, and cross-referencing with disaster databases — to produce a verdict: `real`, `misleading`, `ai-generated`, or `unverified`.

> Built for the OpenLoop OL08 Hackathon.

---

## 🌐 Quick Start (Online Mode)

Vigilens is now strictly online-only for maximum performance and zero local overhead. It uses free-tier cloud APIs (Groq, Hive AI, Google Vision).

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

### Manual setup

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
pip install -r requirements.txt
uvicorn api.main:app --reload    # → http://localhost:8000

# 3. Frontend (new terminal)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev                      # → http://localhost:3000
```

### Required API Keys

Get these — all have generous free tiers:

| Service | Free Tier | What It Does | Get Key |
|---|---|---|---|
| **Groq** ⭐ Required | 100K tokens/day | LLM orchestrator & Whisper | [console.groq.com](https://console.groq.com) |
| **Hive AI** | 100 req/day | Deepfake detection | [thehive.ai](https://thehive.ai) |
| **Google Vision** | 1000 req/month | Reverse image search | [console.cloud.google.com](https://console.cloud.google.com) |

---

## 🚀 Deployment

### Backend (Railway / Heroku)
The backend is ready for deployment with a `Procfile`.
1. Link your repo to Railway.
2. Set `GROQ_API_KEY` and other environment variables.
3. Railway will automatically pick up the `Procfile`.

### Frontend (Vercel)
1. Link your repo to Vercel.
2. Set `NEXT_PUBLIC_BACKEND_URL` to your production backend URL.
3. Deploy.

---

## Architecture

Vigilens uses a LangGraph-powered agentic pipeline:
1. **Preprocess**: FFmpeg extracts keyframes and audio.
2. **DeepFake Detector**: Hive AI analyzes frames for synthetic manipulation.
3. **Source Hunter**: Google Vision & TinEye find the earliest occurrence of the video.
4. **Context Analyser**: Groq Whisper transcribes audio; Groq Vision performs OCR; GDACS DB cross-references events.
5. **Orchestrator**: Groq (Llama 3.3 70B) synthesizes all findings into a final verdict.

---

## License

<<<<<<< ours
MIT — see [LICENSE](LICENSE)
=======
MIT — see [LICENSE](LICENSE)
>>>>>>> theirs
