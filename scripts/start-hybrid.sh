#!/usr/bin/env bash
# ============================================================
# Vigilens — Hybrid Mode (Docker infra + local app)
#
# Reads INFERENCE_MODE from .env in the project root:
#   INFERENCE_MODE=online  → Groq cloud mode  (no Docker needed)
#   INFERENCE_MODE=offline → Local Docker mode (Ollama + DeepSafe)
#
# Run from the project root:
#   bash scripts/start-hybrid.sh
# ============================================================
set -e

# ── Colours ──────────────────────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔════════════════════════════════════════════╗"
echo "  ║           VIGILENS — Hybrid Mode           ║"
echo "  ╚════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Read .env ─────────────────────────────────────────────────────────────────
INFERENCE_MODE="offline"
WHISPER_USE_GROQ="false"
GROQ_API_KEY=""
GROQ_WHISPER_MODEL="whisper-large-v3-turbo"

if [ ! -f ".env" ]; then
  echo -e "${YELLOW}[WARN]${NC} No .env file found in project root."
  echo "       Copy backend/.env.example to .env and fill in your values."
  echo "       Defaulting to INFERENCE_MODE=offline."
  echo
else
  # Parse .env: skip comments (#) and blank lines, export key=value pairs
  while IFS='=' read -r key value; do
    # Skip comments and blank lines
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$key" ]] && continue
    # Trim leading/trailing whitespace from key
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    # Strip inline comments from value (everything after ' #')
    value="${value%%[[:space:]]#*}"
    # Strip surrounding quotes from value if present
    value="${value#\"}"
    value="${value%\"}"
    value="${value#\'}"
    value="${value%\'}"
    case "$key" in
      INFERENCE_MODE)    INFERENCE_MODE="$value" ;;
      WHISPER_USE_GROQ)  WHISPER_USE_GROQ="$value" ;;
      GROQ_API_KEY)      GROQ_API_KEY="$value" ;;
      GROQ_WHISPER_MODEL) GROQ_WHISPER_MODEL="$value" ;;
    esac
  done < ".env"
fi

echo -e "${BOLD}[INFO]${NC} Detected INFERENCE_MODE=${CYAN}${INFERENCE_MODE}${NC}"
echo

# ── Route to correct mode ─────────────────────────────────────────────────────
case "${INFERENCE_MODE,,}" in
  online)  goto_mode="groq" ;;
  offline) goto_mode="docker" ;;
  *)
    echo -e "${YELLOW}[WARN]${NC} Unrecognised INFERENCE_MODE='${INFERENCE_MODE}' in .env"
    echo "       Supported values: online, offline. Defaulting to offline."
    goto_mode="docker"
    INFERENCE_MODE="offline"
    ;;
esac


# ══════════════════════════════════════════════════════════════════════════════
# OFFLINE MODE — Ollama + DeepSafe via Docker
# ══════════════════════════════════════════════════════════════════════════════
if [ "$goto_mode" = "docker" ]; then
  echo -e "${YELLOW}[MODE]${NC} OFFLINE — Starting Docker infrastructure (Ollama + DeepSafe)"
  echo

  # Check Docker is installed
  if ! command -v docker &>/dev/null; then
    echo -e "${RED}[ERROR]${NC} Docker is not installed or not in PATH."
    echo "        Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
  fi

  # Check Docker daemon is running
  if ! docker info &>/dev/null; then
    echo -e "${RED}[ERROR]${NC} Docker daemon is not running."
    echo "        Please start Docker Desktop (or the Docker service) and try again."
    exit 1
  fi

  # 1/4 — Start Docker infra
  echo -e "${YELLOW}[1/4]${NC} Starting Docker containers (Ollama + DeepSafe)..."
  docker compose up -d ollama deepsafe
  echo "      Containers started."
  echo

  # 2/4 — Pull Ollama model if needed
  echo -e "${YELLOW}[2/4]${NC} Ensuring Ollama model (gemma4:e4b) is ready..."
  echo "      This may take several minutes on first run (model download)."
  docker exec openloop-ol08-ollama-1 ollama pull gemma4:e4b || {
    echo -e "${YELLOW}[WARN]${NC} Could not pull Ollama model — container may still be starting."
    echo "       If the backend fails, run: docker exec openloop-ol08-ollama-1 ollama pull gemma4:e4b"
  }
  echo
fi


# ══════════════════════════════════════════════════════════════════════════════
# ONLINE / GROQ MODE — no Docker needed
# ══════════════════════════════════════════════════════════════════════════════
if [ "$goto_mode" = "groq" ]; then
  echo -e "${GREEN}[MODE]${NC} ONLINE (Groq) — Docker ${BOLD}NOT${NC} required. Skipping Ollama + DeepSafe."
  echo

  # Validate GROQ_API_KEY
  if [ -z "$GROQ_API_KEY" ]; then
    echo -e "${RED}[ERROR]${NC} INFERENCE_MODE=online but GROQ_API_KEY is not set in .env"
    echo "        Add your key:  GROQ_API_KEY=gsk_..."
    echo "        Get a free key at https://console.groq.com"
    exit 1
  fi

  # Show masked key (first 7 chars only)
  KEY_PREVIEW="${GROQ_API_KEY:0:7}"
  echo -e "${GREEN}[OK]${NC}   GROQ_API_KEY is set (starts with: ${KEY_PREVIEW}...)"

  # Warn if Groq Whisper not enabled
  if [ "${WHISPER_USE_GROQ,,}" = "true" ]; then
    echo -e "${GREEN}[OK]${NC}   WHISPER_USE_GROQ=true — transcription uses Groq Whisper API (${GROQ_WHISPER_MODEL})"
  else
    echo -e "${YELLOW}[WARN]${NC} WHISPER_USE_GROQ is not 'true' in .env"
    echo "       Transcription will fall back to the local Whisper model (slow on first run)"
    echo "       Add  WHISPER_USE_GROQ=true  to .env to use Groq Whisper instead."
  fi
  echo

  echo -e "${CYAN}[1/4]${NC} Skipping Docker — Groq cloud handles LLM + Whisper."
  echo -e "${CYAN}[2/4]${NC} Skipping Ollama model pull — not needed in Groq mode."
  echo
fi


# ══════════════════════════════════════════════════════════════════════════════
# COMMON — Start Backend + Frontend locally
# ══════════════════════════════════════════════════════════════════════════════

# 3/4 — Backend
echo -e "${YELLOW}[3/4]${NC} Starting Backend (local venv)..."

PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
if [ -z "$PYTHON" ]; then
  echo -e "${RED}[ERROR]${NC} Python not found. Install Python 3.10+ and try again."
  exit 1
fi

if [ ! -d "backend/.venv" ]; then
  echo "       Virtual environment not found — creating one now..."
  "$PYTHON" -m venv backend/.venv
fi

(
  cd backend
  source .venv/bin/activate
  echo "[BACKEND] Installing / verifying dependencies..."
  pip install -r requirements.txt -q
  echo "[BACKEND] Starting uvicorn on port 8888 (INFERENCE_MODE=${INFERENCE_MODE})..."
  python -m uvicorn api.main:app --host 127.0.0.1 --port 8888 --reload
) &
BACKEND_PID=$!

echo "      Backend started (PID: ${BACKEND_PID}). Waiting 6 seconds to initialize..."
sleep 6
echo

# 4/4 — Frontend
echo -e "${YELLOW}[4/4]${NC} Starting Frontend (Next.js)..."

if [ ! -d "frontend/node_modules" ]; then
  echo "       node_modules not found — running npm install..."
  (cd frontend && npm install -q)
fi

(
  cd frontend
  echo "[FRONTEND] Starting Next.js dev server..."
  npm run dev
) &
FRONTEND_PID=$!

echo "      Frontend started (PID: ${FRONTEND_PID}). Waiting 5 seconds to boot..."
sleep 5
echo


# ══════════════════════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════════════════════
echo -e "${GREEN}"
echo "  ╔════════════════════════════════════════════╗"
echo "  ║        Vigilens is booting up!             ║"
echo "  ╚════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  Mode     : ${CYAN}${INFERENCE_MODE}${NC}"
echo "  Frontend : http://localhost:3000"
echo "  Backend  : http://127.0.0.1:8888"

if [ "$INFERENCE_MODE" = "offline" ]; then
  echo "  Ollama   : http://localhost:11434"
  echo "  DeepSafe : http://localhost:8001"
  echo
  echo "  To stop Docker containers: docker compose down"
else
  echo "  LLM      : Groq cloud (${GROQ_ORCHESTRATOR_MODEL:-llama-3.3-70b-versatile})"
  echo "  Whisper  : Groq cloud (${GROQ_WHISPER_MODEL:-whisper-large-v3-turbo})"
  echo
  echo "  No Docker containers to stop."
fi

echo
echo "  Backend logs  → PID ${BACKEND_PID}"
echo "  Frontend logs → PID ${FRONTEND_PID}"
echo "  Press Ctrl+C to stop all processes."
echo

# Open browser if xdg-open / open is available
sleep 3
if command -v xdg-open &>/dev/null; then
  xdg-open http://localhost:3000 &>/dev/null || true
elif command -v open &>/dev/null; then
  open http://localhost:3000 || true
fi

# Wait for either process to exit; clean up both on Ctrl+C
trap "echo; echo 'Stopping Vigilens...'; kill ${BACKEND_PID} ${FRONTEND_PID} 2>/dev/null || true; exit 0" SIGINT SIGTERM
wait ${FRONTEND_PID}
