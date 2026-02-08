# Flare AI DeFAI — BTC Risk Analysis Agent

A **deterministic BTC/USD risk analysis agent** powered by:

- 📈 **Live on-chain prices from Flare FTSOv2**
- 🧮 **Deterministic crash-risk & regime models** (no LLM math)
- 💬 **Natural-language chat interface** for querying risk profiles
- 🔐 **TEE-ready deployment** with remote attestation support

This project demonstrates how **on-chain oracle data (Flare)**, **off-chain market history**, and **AI interfaces** can be combined safely — with a strict separation between **math** and **language models**.

---

## 🚀 What This Project Does

### Core functionality

- Fetches **live BTC/USD prices** from **Flare Time Series Oracle (FTSOv2)**
- Runs **deterministic risk models** over historical 15-minute BTC data:
  - Crash probability
  - Market regime (Calm / Volatile / Stress)
  - LCVI (liquidity-adjusted volatility)
  - VaR / Expected Shortfall
  - Exposure recommendations
- Exposes results via:
  - 📄 a **snapshot JSON** (`shared/latest_update.json`)
  - 💬 a **chat interface** where users can say:
    - “I’m low risk, horizon 72h”
    - “I hold 0.5 BTC, medium risk”
    - “What should I watch if volatility spikes?”

---

## 🧠 AI Safety Model (Important)

### What the AI *does*

✅ Parses **user intent** (risk appetite, horizon, position size)  
✅ Formats **numerical results** into readable explanations  

### What the AI *does NOT do*

❌ Compute prices  
❌ Compute risk metrics  
❌ Invent market data  
❌ Give financial advice  

All market math lives in the **RiskEngine** and is **fully deterministic**.

---

## 🧩 Architecture Overview

```text
User Message
   ↓
LLM (intent parsing only)
   ↓
Deterministic RiskEngine
   ↓
Flare FTSO (live BTC price)
   ↓
Snapshot JSON + Chat Response
