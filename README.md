Flare AI DeFAI — BTC Risk Analysis Agent

A deterministic BTC/USD risk analysis agent powered by:

📈 Live on-chain prices from Flare FTSOv2

🧮 Deterministic crash-risk & regime models (no LLM math)

💬 Natural-language chat interface for querying risk profiles

🔐 TEE-ready deployment with remote attestation support

This project demonstrates how on-chain oracle data (Flare), off-chain market history, and AI interfaces can be combined safely — with a strict separation between math and language models.

🚀 What This Project Does
Core functionality

Fetches live BTC/USD prices from Flare Time Series Oracle (FTSOv2)

Runs deterministic risk models over historical 15-minute BTC data:

Crash probability

Market regime (Calm / Volatile / Stress)

LCVI (liquidity-adjusted volatility)

VaR / Expected Shortfall

Exposure recommendations

Exposes results via:

📄 a snapshot JSON (shared/latest_update.json)

💬 a chat interface where users can say:

“I’m low risk, horizon 72h”

“I hold 0.5 BTC, medium risk”

“What should I watch if volatility spikes?”

What the AI does and does not do

✅ LLM is allowed to:

Parse user intent (risk appetite, horizon, position size)

Format numerical outputs into readable explanations

❌ LLM is NOT allowed to:

Compute prices

Compute risk metrics

Invent market data

Give financial advice

All math lives in the RiskEngine and is fully deterministic.

🧠 Architecture Overview
User Message
   ↓
LLM (intent parsing only)
   ↓
Deterministic RiskEngine
   ↓
Flare FTSO (live BTC price)
   ↓
Snapshot JSON + Chat Response

🔑 Environment Variables

This project uses a .env file for configuration.

Required (core functionality)
WEB3_PROVIDER_URL=https://coston2-api.flare.network/ext/C/rpc


Used to fetch live BTC/USD prices from Flare FTSOv2.

Optional (chat & AI features)
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash


Used for:

Parsing user risk preferences

Formatting responses in natural language

If GEMINI_API_KEY is not set:

✅ Risk engine + snapshot still work

❌ Chat intent parsing will be limited

🎯 Getting Started

You can run the project locally with Docker (recommended) or manually.

Environment setup

Copy the environment file:

cp .env.example .env


Edit .env and set at least:

WEB3_PROVIDER_URL=...

🐳 Build & Run with Docker (Recommended)

The Docker setup mimics a TEE-style environment, running:

Backend (FastAPI + RiskEngine)

Frontend (Chat UI)

Nginx + Supervisor

Build the image
docker build -t flare-ai-defai .

Run the container
docker run -p 80:80 -it --env-file .env flare-ai-defai

Open the app

Navigate to:
👉 http://localhost:80

🛠 Manual Setup (Advanced)
Backend
uv sync --all-extras
uv run start-backend


Runs on:

http://0.0.0.0:8080

Frontend
cd chat-ui
npm install
npm start


For local testing, update:

const BACKEND_ROUTE = "http://localhost:8080/api/routes/chat/";

📁 Repo Structure (Relevant Parts)
src/flare_ai_defai/
├── crash_detection_system/     # Deterministic risk models
│   ├── engine/                # RiskEngine, HMM regimes
│   ├── models/                # Crash probability, LCVI
│   └── data/                  # BTC 15m OHLCV CSV
├── flare/
│   └── flare_price.py         # Live BTC price via FTSOv2
├── api/routes/
│   └── chat.py                # ChatRouter (intent → risk)
├── ai/
│   └── gemini.py              # LLM (intent + formatting only)
├── settings.py
└── main.py

📄 Snapshot Output

Each run produces:

shared/latest_update.json


Example:

{
  "asset": "BTC-USD",
  "price": 70533.74,
  "price_source": "flare-ftso-v2",
  "risk": {
    "crash_prob": 0.56,
    "regime": "Volatile",
    "recommended_exposure": 0.6
  }
}


This file is:

written by a single script

safe to consume by dashboards, bots, or UIs

🚀 Deploy on TEE (Unchanged)

All Confidential Space / AMD SEV instructions below remain valid.

(Your existing deployment section can remain as-is — it already fits well.)

💡 What This Project Is Good For

🔗 Demonstrating Flare oracle integration (FTSOv2)

🧠 Showing safe AI + finance separation

📊 Building risk dashboards or alerting systems

🧪 Hackathon / research demos

🧩 Foundation for multi-asset risk engines

⚠️ Disclaimer

This project is for educational and demonstration purposes only.
It does not provide financial advice.
