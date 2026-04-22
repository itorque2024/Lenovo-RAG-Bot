# Lenovo AI Multi-Agent Assistant

A production-ready, multi-agent RAG chatbot for Lenovo customer support. Built with **Groq (Llama 3.3 70B)** and **LangGraph**, accessible via a **Gradio web UI** and **Telegram bot**.

---

## What the App Does

A user asks a question — simple or multi-part — and the right agent automatically answers it. Each agent is a specialist that only handles its domain. If a question touches multiple topics, the app splits it and routes each part to the correct agent, then combines all answers into one response.

**Example:**
> "What is the price of the ThinkPad X1 Carbon, what is the return policy, and convert 1499 USD to SGD?"

The app splits this into three sub-questions and routes them simultaneously:
- **Product Agent** answers the price question
- **Policy Agent** answers the return policy question
- **Finance Agent** converts the currency

Each answer is clearly labelled with which agent answered it.

---

## The 5 Agents

| Agent | Handles |
|---|---|
| **Product Agent** | Laptop specs, prices, models — ThinkPad, IdeaPad, Legion, Yoga |
| **Tech Agent** | Troubleshooting, drivers, repairs, how-to guides |
| **Policy Agent** | Delivery, returns, refunds, warranty policy, payment |
| **Finance Agent** | Live currency conversion (USD, SGD, EUR, and more) |
| **Search Agent** | Real-time web search for latest news or info not in local data |

---

## How It Works

```
User message
     │
     ▼
 Router (LLM)
 Decomposes the question into sub-queries,
 assigns each to the right agent
     │
     ├──► Product Agent  (RAG on product data)
     ├──► Tech Agent     (RAG on tech support data)
     ├──► Policy Agent   (RAG on policy data)
     ├──► Finance Agent  (live exchange rate API)
     └──► Search Agent   (Brave Search API)
     │
     ▼
 Combined response with agent labels shown
```

Each RAG agent searches its own local knowledge base (FAISS vector store) and answers only its assigned sub-question — not the full query.

---

## Access Channels

| Channel | Platform | How |
|---|---|---|
| Web chatbot | Hugging Face Spaces | Gradio UI, public URL |
| Telegram | Telegram app | Message the bot directly |

Both channels connect to the same backend — same agents, same answers.

---

## Technology Choices and Why

### LLM — Groq (Llama 3.3 70B)
Groq provides free API access to Llama 3.3 70B with 14,400 requests/day on the free tier. It is significantly faster than most hosted LLMs. Gemini was used initially but its free quota was consumed quickly because it was also being used for embeddings. Groq is used for reasoning only (router + agent responses), which keeps usage low.

### Embeddings — FastEmbed (ONNX, local)
FastEmbed runs the `BAAI/bge-small-en-v1.5` model locally using ONNX Runtime — no GPU, no external API, no quota. It replaces Google's embedding API (which was burning Gemini quota on every query) and `sentence-transformers` (which pulled in PyTorch and made the Docker image 5.7GB, exceeding Railway's 4GB free tier limit). FastEmbed is ~80MB total.

### Vector Store — FAISS (local)
FAISS runs in-process with no external database needed. Since the knowledge base is small (a few text files), a hosted vector database would be unnecessary overhead. FAISS is fast enough and free.

### Agent Framework — LangGraph
LangGraph allows defining the agent flow as an explicit graph — Router node → Agent nodes → END. This gives full control over routing logic, state, and which agent runs next. It matches the multi-agent pattern from the reference design: a Router classifies the query, separate agent nodes handle their specific domain, and state carries sub-queries and responses through the graph.

### Telegram — Webhook mode (not polling)
Polling keeps a long-lived outbound connection open, which cloud platforms like Railway drop after a timeout. Webhook mode flips the direction — Telegram calls the backend when a message arrives. This works reliably on any cloud platform with a public URL.

### Backend — FastAPI on Railway
FastAPI is lightweight and async, matching the async LangGraph execution. Railway provides a free tier with automatic GitHub deployment — every push to main triggers a redeploy.

### Frontend — Gradio on Hugging Face Spaces
Gradio is purpose-built for AI demos and runs natively on Hugging Face Spaces for free. The frontend is a thin client — it only sends the message to the Railway backend and displays the response. Gradio is pinned to version 4.44.1 because Gradio 5.x on HF Spaces auto-injects HuggingFace OAuth into ChatInterface, blocking unauthenticated users even on public Spaces.

---

## Architecture

```
┌─────────────────────────┐        ┌──────────────────────────────────┐
│  Hugging Face Spaces     │        │  Railway (Backend)                │
│  Gradio 4.44.1           │──────► │  FastAPI + LangGraph              │
│  (Web UI)                │  POST  │  Groq LLM + FastEmbed + FAISS     │
└─────────────────────────┘  /chat  │  Telegram Webhook                 │
                                    └──────────────────────────────────┘
┌─────────────────────────┐                    ▲
│  Telegram               │────────────────────┘
│  (Mobile / Desktop)     │  POST /telegram/webhook
└─────────────────────────┘
```

**All free. No paid services required.**

---

## Repository Structure

```
.
├── backend/
│   ├── agent.py          # LangGraph multi-agent graph (Router + 5 agents)
│   └── server.py         # FastAPI server + Telegram webhook
├── product/              # Lenovo product catalog (txt)
├── tech/                 # Tech support knowledge base (txt)
├── policy/               # Delivery, returns, warranty policies (txt)
├── app.py                # Gradio frontend
├── requirements.txt      # Backend dependencies (Railway)
├── requirements-gradio.txt  # Frontend dependencies (HF Spaces)
├── Procfile              # Railway start command
└── render.yaml           # Render deployment config (alternative)
```

---

## Deployment

### Backend (Railway)
1. Connect GitHub repo to Railway
2. Railway auto-deploys on every push to `main`
3. Set these environment variables in Railway:
   - `GROQ_API_KEY` — from console.groq.com (free)
   - `BRAVE_API_KEY` — from brave.com/search/api (free tier)
   - `TELEGRAM_BOT_TOKEN` — from @BotFather on Telegram
   - `WEBHOOK_URL` — your Railway public URL (e.g. `https://web-production-xxxx.up.railway.app`)

### Frontend (Hugging Face Spaces)
1. Create a new Space on huggingface.co → SDK: Gradio
2. Upload `app.py` and `requirements-gradio.txt` (rename to `requirements.txt`)
3. Add a secret: `BACKEND_API_URL` = `https://your-railway-url.up.railway.app/chat`
4. Space builds automatically — no further configuration needed

---

## Local Development

```bash
conda create -n lenovo-rag python=3.10
conda activate lenovo-rag
pip install -r requirements.txt
pip install -r requirements-gradio.txt

# Set env vars in .env
cp backend/.env.example .env

# Run backend
PYTHONPATH=. uvicorn backend.server:app --host 0.0.0.0 --port 10000

# Run frontend (separate terminal)
python app.py
```
