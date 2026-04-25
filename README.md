# Vigilens 🛡️

**AI-powered disaster video misinformation detection.**

Vigilens analyses disaster videos in real time — detecting deepfakes, tracing the original source, and cross-referencing with disaster databases — to produce a verdict: `Real`, `Misleading`, or `Unverified`.

> Built for the OpenLoop OL08 Hackathon.

---

## 🌐 Quick Start

### Prerequisites

| Tool | Min Version | Download |
|---|---|---|
| Python | 3.11+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| FFmpeg | Any | [Windows](https://ffmpeg.org/download.html) · `brew install ffmpeg` · `apt install ffmpeg` |

### Manual Setup

```bash
# 1. Clone
git clone https://github.com/PrakD3/openloop-OL08.git
cd openloop-OL08

# 2. Backend
cd vigilens-backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload   # → http://localhost:8000/docs

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev                      # → http://localhost:3000
```

### Required API Keys (for production)

| Service | Free Tier | What It Does | Get Key |
|---|---|---|---|
| **Groq** ⭐ Required | 100K tokens/day | LLM orchestrator & Whisper | [console.groq.com](https://console.groq.com) |
| **Hive AI** | 100 req/day | Deepfake detection | [thehive.ai](https://thehive.ai) |
| **Google Vision** | 1000 req/month | Reverse image search | [console.cloud.google.com](https://console.cloud.google.com) |

---

## 🏗️ Architecture

Vigilens uses a modular async pipeline with parallel agent execution:

```
POST /api/analyze
        │
        ▼
   [Preprocess]
   extract_keyframes + extract_audio
        │
        ▼
   [Agent Layer] ← runs in parallel via asyncio.gather
   ┌──────────────┬──────────────┬──────────────┬──────────────┐
   │   Deepfake   │    Source    │   Context    │   Temporal   │
   │   Agent      │   Agent      │   Agent      │   Agent      │
   └──────────────┴──────────────┴──────────────┴──────────────┘
        │
        ▼
   [Orchestrator] ← weighted scoring system
   verdict: Real / Unverified / Misleading
        │
        ▼
   Background Job → stored in-memory
```

### Orchestrator Scoring

| Agent | Condition | Score |
|---|---|---|
| Deepfake | `label == "fake"` | +40 |
| Deepfake | `label == "suspicious"` | +20 |
| Source | `credibility == "low"` | +25 |
| Source | `credibility == "unknown"` | +10 |
| Context | `consistency == "questionable"` | +20 |
| Temporal | `label == "temporal_mismatch"` | +30 |

**Verdict thresholds:** `< 30` → Real · `< 60` → Unverified · `≥ 60` → Misleading

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/analyze` | Submit video for analysis → returns `job_id` |
| `GET` | `/api/status/{job_id}` | Check job status |
| `GET` | `/api/result/{job_id}` | Fetch final analysis result |
| `GET` | `/api/analyze/stream?video_url=...` | Real-time SSE streaming updates |

**Interactive docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🚀 Deployment

### Backend (Railway / Heroku)
1. Link your repo to Railway.
2. Set `GROQ_API_KEY` and other environment variables.
3. Railway will automatically pick up the `Procfile`.

### Frontend (Vercel)
1. Link your repo to Vercel.
2. Set `NEXT_PUBLIC_BACKEND_URL` to your production backend URL.
3. Deploy.

---

## License

MIT — see [LICENSE](LICENSE)
