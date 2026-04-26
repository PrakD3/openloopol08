# Vigilens 🛡️

**AI-powered disaster video misinformation detection.**

Vigilens analyses disaster videos in real time — detecting deepfakes, tracing the original source, and cross-referencing with global disaster databases — to produce a definitive verification verdict. Built for the **OpenLoop OL08 Hackathon**, Vigilens addresses the critical need for verifiable information during humanitarian crises.

## Key Features

- **Multi-Agent Forensics**: Orchestrates four specialized AI agents using LangGraph for deep video analysis.
- **Deepfake Detection**: Hybrid scoring using Vertex AI, Groq Vision, and pixel-variance heuristics.
- **Source Hunting**: Provenance tracing via Google Vision, TinEye, and the Wayback Machine.
- **Context Verification**: Cross-references findings with real-world weather (Open-Meteo) and disaster (GDACS) data.
- **Real-time SMS Alerts**: Automated notifications for high-priority incidents via Twilio integration.

---

## Tech Stack

- **Language**: Python 3.11+, TypeScript
- **Backend Framework**: FastAPI with LangGraph
- **Frontend Framework**: Next.js 14+ (App Router) with Tailwind CSS
- **Orchestration**: LangGraph, LangChain
- **AI Models**: Google Vertex AI (Gemini 1.5), Groq (Llama 3.3), OpenAI Whisper
- **Data/Tracing**: Supabase (PostgreSQL), LangSmith
- **Tooling**: FFmpeg, OpenCV, EasyOCR, yt-dlp, Playwright

---

## Prerequisites

- **Python 3.11** or higher
- **Node.js 18** or higher
- **FFmpeg** (Required for video processing)
  - Windows: `choco install ffmpeg` or [Download Here](https://ffmpeg.org/download.html)
  - macOS: `brew install ffmpeg`
- **Groq API Key** (Required for the Orchestrator)
- **Google Cloud API Key** (Highly recommended for Gemini and Vision)

---

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/PrakD3/openloop-OL08.git
cd openloop-OL08
```

### 2. Rapid Installation (Windows)
Run the automated installation script to download FFmpeg, set up virtual environments, and install all dependencies:
```bat
install.bat
```

### 3. Environment Setup
Copy the example environment files:
```bash
# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.local.example frontend/.env.local
```

Configure your API keys in `backend/.env`. At minimum, you need `GROQ_API_KEY`.

### 4. Start Development Servers
**Windows (One Command):**
```bat
scripts\start-online.bat
```

**Manual Start:**
- **Backend:** `cd backend && source .venv/bin/activate && uvicorn api.main:app --reload`
- **Frontend:** `cd frontend && npm run dev`

Open [http://localhost:3000](http://localhost:3000) to view the application.

---

## Architecture

### Directory Structure
```
├── backend/
│   ├── agents/            # LangGraph logic and agent nodes
│   │   ├── nodes/         # Individual agent implementations
│   │   ├── tools/         # FFmpeg, vision, and scraper utilities
│   │   └── graph.py       # Pipeline definition (StateGraph)
│   ├── api/               # FastAPI endpoints and job management
│   ├── ml/                # Custom scoring engine and disaster models
│   └── config/            # Pydantic settings and env management
├── frontend/
│   ├── src/
│   │   ├── app/           # Analysis, incidents, and bulletin pages
│   │   ├── components/    # Custom UI components and analysis panels
│   │   └── lib/           # Utility functions and demo configuration
├── scripts/               # Startup and automation scripts
└── install.bat            # Full dependency installer
```

### The Request Lifecycle (VIGILENS-OS-ALPHA)
1. **Ingestion**: The user submits a video URL (YouTube, Twitter, etc.).
2. **Preprocessing**: FFmpeg extracts keyframes and audio; `yt-dlp` harvests platform metadata.
3. **Parallel Analysis**: LangGraph launches four concurrent nodes:
   - **Deepfake Detector**: Scans keyframes for GAN/AI artifacts.
   - **Source Hunter**: Traces visual content history via Google Vision and TinEye.
   - **Context Analyser**: Verifies weather, language, and disaster database matches.
   - **Geolocation Hunter**: Matches architecture and terrain to coordinates.
4. **Scoring Engine**: A custom ML engine (`scoring_engine.py`) blends agent findings with disaster-specific susceptibility weights.
5. **Orchestration**: The Orchestrator node (Llama 3.3) synthesizes all raw data into a final public verdict.
6. **Delivery**: The verdict is displayed on the frontend and high-priority alerts are sent via Twilio.

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Description | Requirement |
|---|---|---|
| `GROQ_API_KEY` | Key for Llama 3.3 orchestration | **Required** |
| `GOOGLE_API_KEY` | Gemini 1.5 / Vertex AI integration | Recommended |
| `OPENAI_API_KEY` | Whisper transcription API | Optional |
| `GOOGLE_VISION_API_KEY`| Reverse image search provenance | Optional |
| `TWILIO_ACCOUNT_SID` | SMS alert credentials | Optional |

### Frontend (`frontend/.env.local`)
| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_BACKEND_URL`| Backend API endpoint | `http://localhost:8000` |
| `NEXT_PUBLIC_APP_MODE` | `demo` or `real` mode | `real` |

---

## Available Scripts

| Command | Description |
|---|---|
| `install.bat` | Full project setup (FFmpeg + venv + npm) |
| `scripts\start-online.bat`| Starts backend and frontend in online mode |
| `pytest backend/tests/` | Runs backend test suite |
| `npm run lint` | Runs frontend code quality checks |

---

## Testing

Backend verification is handled by `pytest`:
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```
Tests validate node transitions, FFmpeg stability, and scoring engine determinism.

---

## Deployment

### Frontend (Vercel)
Optimized for Vercel. Connect your repository and configure `NEXT_PUBLIC_BACKEND_URL`.

### Backend (Docker/Render)
The backend requires FFmpeg. Use the provided `docker/Dockerfile.backend` for a production-ready containerized deployment.

---

## Troubleshooting

- **FFmpeg missing**: Ensure `ffmpeg` is in your PATH. Run `install.bat` to automate the installation if on Windows.
- **Slow Analysis**: Vision LLMs can take 10-15 seconds per video. Check LangSmith for detailed node-by-node timing.
- **CORS Errors**: Ensure `NEXT_PUBLIC_BACKEND_URL` in the frontend matches the actual backend host.

---

## License
Apache-2.0 — see [LICENSE](LICENSE)