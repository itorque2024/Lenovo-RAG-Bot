# Lenovo AI Multi-Agent Assistant

A production-ready, multi-agent RAG chatbot for Lenovo customer support. Built with **Groq (Llama 3.3 70B)** and **LangGraph**, accessible via a **Gradio web UI** and **Telegram bot**.

---

## What the App Does

A user asks a question — simple or multi-part — and the right agent automatically answers it. Each agent is a specialist that only handles its domain. If a question touches multiple topics, the app splits it and routes each part to the correct agent, then combines all answers into one response.

**Example:**
> "What is the price of the ThinkPad X1 Carbon, what is the return policy, and convert 1499 USD to SGD?"

The app splits this into three sub-questions and routes them in sequence:
- **Product Agent** answers the price question
- **Policy Agent** answers the return policy question
- **Finance Agent** converts the currency

Each answer is clearly labelled with which agent answered it.

---

## The 6 Agents

| Agent | Handles | Tools Available |
|---|---|---|
| **Product Agent** | Laptop specs, prices, models — ThinkPad, IdeaPad, Legion, Yoga | Local RAG → Brave Search fallback |
| **Tech Agent** | Troubleshooting, drivers, repairs, how-to guides | Local RAG → Brave Search fallback |
| **Policy Agent** | Delivery, returns, refunds, warranty policy, payment | Local RAG → Brave Search fallback |
| **Finance Agent** | Live currency conversion (USD, SGD, EUR, and more) | Live exchange rate API |
| **Search Agent** | Real-time web search for latest news or info not in local data | Brave Search API |
| **General Agent** | Greetings, small talk, general questions not covered above | Brave Search (optional) |

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
     ├──► Product Agent  ──► ReAct loop: LLM decides → local RAG and/or Brave Search
     ├──► Tech Agent     ──► ReAct loop: LLM decides → local RAG and/or Brave Search
     ├──► Policy Agent   ──► ReAct loop: LLM decides → local RAG and/or Brave Search
     ├──► Finance Agent  ──► live exchange rate API
     ├──► Search Agent   ──► Brave Search API
     └──► General Agent  ──► LLM directly, Brave Search if needed
     │
     ▼
 Combined response with agent labels shown
```

Each RAG agent uses a **ReAct loop** — the LLM reads the local search results and decides whether they are sufficient, or whether to also call Brave Search for more complete information.

---

## Access Channels

| Channel | Platform | How |
|---|---|---|
| Web chatbot | Hugging Face Spaces | Gradio UI, public URL |
| Telegram | Telegram app | Message the bot directly |

Both channels connect to the same Railway backend — same agents, same answers.

---

## Technology Choices and Why

### LLM — Groq (Llama 3.3 70B)
Groq provides free API access to Llama 3.3 70B with 14,400 requests/day on the free tier. It is significantly faster than most hosted LLMs. Gemini was used initially but its free quota was consumed quickly because it was also being used for embeddings. Groq is used for reasoning only (router + agent responses), which keeps usage low.

### Embeddings — FastEmbed (ONNX, local)
FastEmbed runs the `BAAI/bge-small-en-v1.5` model locally using ONNX Runtime — no GPU, no external API, no quota. It replaces Google's embedding API (which was burning Gemini quota on every query) and `sentence-transformers` (which pulled in PyTorch and made the Docker image 5.7GB, exceeding Railway's 4GB free tier limit). FastEmbed is ~80MB total.

### Vector Store — FAISS (local)
FAISS runs in-process with no external database needed. Since the knowledge base is small (a few text files), a hosted vector database would be unnecessary overhead. FAISS is fast enough and free.

### Agent Framework — LangGraph + create_react_agent
LangGraph defines the overall flow as an explicit graph — Router → Agent nodes → END. Within each RAG agent, `create_react_agent` gives the LLM control over which tools to call. The LLM reads local RAG results and decides whether to supplement with Brave Search, rather than having the code make that decision blindly.

### Telegram — Webhook mode (not polling)
Polling keeps a long-lived outbound connection open, which cloud platforms like Railway drop after a timeout. Webhook mode flips the direction — Telegram calls the backend when a message arrives. This works reliably on any cloud platform with a public URL.

### Backend — FastAPI on Railway
FastAPI is lightweight and async, matching the async LangGraph execution. Railway provides a free tier with automatic GitHub deployment — every push to `main` triggers a redeploy.

### Frontend — Gradio on Hugging Face Spaces
Gradio is purpose-built for AI demos and runs natively on Hugging Face Spaces for free. The frontend is a thin client — it only sends the message to the Railway backend and displays the response. HuggingFace Spaces forces its own Gradio version so no pinning is needed. The app uses `gr.Blocks` instead of `gr.ChatInterface` to avoid HuggingFace's automatic OAuth injection which blocks unauthenticated users.

---

## Architecture

```
┌──────────────────────────┐        ┌──────────────────────────────────┐
│  Hugging Face Spaces      │        │  Railway (Backend)                │
│  Gradio (gr.Blocks)       │──────► │  FastAPI + LangGraph              │
│  (Web UI)                 │  POST  │  Groq LLM + FastEmbed + FAISS     │
└──────────────────────────┘  /chat  │  Telegram Webhook                 │
                                     └──────────────────────────────────┘
┌──────────────────────────┐                    ▲
│  Telegram                 │────────────────────┘
│  (Mobile / Desktop)       │  POST /telegram/webhook
└──────────────────────────┘
```

**All free. No paid services required.**

---

## Repository Structure

```
.
├── backend/
│   ├── agent.py          # LangGraph multi-agent graph (Router + 6 agents + ReAct tools)
│   └── server.py         # FastAPI server + Telegram webhook
├── product/              # Lenovo product catalog (txt)
├── tech/                 # Tech support knowledge base (txt)
├── policy/               # Delivery, returns, warranty policies (txt)
├── app.py                # Gradio frontend (deployed to HuggingFace Spaces manually)
├── requirements.txt      # Backend dependencies (Railway — auto-deployed via GitHub)
├── requirements-gradio.txt  # Frontend dependencies reference (see HF Spaces setup below)
├── Procfile              # Railway start command
└── render.yaml           # Render deployment config (alternative to Railway)
```

---

## Deployment

### Backend (Railway) — Auto-deploys on every git push

1. Connect this GitHub repo to Railway
2. Every push to `main` triggers a redeploy automatically
3. Set these environment variables in Railway → Variables:

| Variable | Where to get it |
|---|---|
| `GROQ_API_KEY` | console.groq.com (free) |
| `BRAVE_API_KEY` | brave.com/search/api (free tier) |
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram |
| `WEBHOOK_URL` | Your Railway public URL e.g. `https://web-production-xxxx.up.railway.app` (no trailing slash) |

---

### Frontend (Hugging Face Spaces) — Manual setup and updates

> ⚠️ The HuggingFace Space has its **own separate repository** and is **not linked to GitHub**. Any change to `app.py` in this repo must be manually copied to the Space.

#### First-time setup

1. Go to **huggingface.co** → New Space → SDK: **Gradio** → Visibility: **Public**
2. In the Space → **Files** tab → upload or create these two files:

**`app.py`** — copy the contents of `app.py` from this repo

**`requirements.txt`** — create with exactly this content:
```
requests
python-dotenv
```
> Do not add `gradio` — HuggingFace installs its own version automatically.

3. In the Space → **Settings** → **Variables and Secrets** → add a **Secret**:

| Name | Value |
|---|---|
| `BACKEND_API_URL` | `https://your-railway-url.up.railway.app/chat` |

4. The Space builds automatically. Once status shows **Running**, the chatbot is live.

#### Updating the frontend

Whenever `app.py` changes in this repo:
1. Go to the Space → **Files** tab
2. Click `app.py` → edit icon
3. Replace the contents with the updated `app.py` from this repo
4. Commit — Space rebuilds automatically

---

## Local Development

```bash
conda create -n lenovo-rag python=3.10
conda activate lenovo-rag
pip install -r requirements.txt

# Copy and fill in environment variables
cp backend/.env.example .env
# Add GROQ_API_KEY, BRAVE_API_KEY, TELEGRAM_BOT_TOKEN to .env

# Run backend (terminal 1)
PYTHONPATH=. uvicorn backend.server:app --host 0.0.0.0 --port 10000

# Run frontend (terminal 2)
pip install gradio requests python-dotenv
python app.py
```

The Gradio UI will be available at `http://localhost:7860` and will connect to the backend at `http://localhost:10000`.
