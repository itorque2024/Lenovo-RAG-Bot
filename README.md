# Lenovo AI Multi-Agent RAG Assistant

A production-grade, multi-agent RAG chatbot powered by **Google Gemini** and **LangGraph**. This system features a pure Python architecture for maximum stability and easy cloud deployment.

## 🌟 Features

### 1. Multi-Agent Intelligence (LangGraph)
- **Product Specialist**: Expert on laptop/PC specs and prices.
- **Tech Specialist**: Handles troubleshooting and repair guides.
- **Policy Specialist**: Manages shipping, returns, and warranty info.
- **Brave Search Specialist**: Live web search fallback.
- **Finance Specialist**: Real-time currency converter (USD to SGD).

### 2. Cross-Platform Interfaces
- **Web/Mobile UI**: Responsive Chat interface built with **Gradio**.
- **Telegram Bot**: Native integration via `python-telegram-bot` running inside the backend.

### 3. Security
- **X-API-KEY**: All cloud endpoints are protected.
- **Isolated Environment**: Full Conda support for local development.

## 🏗️ Architecture
- **Backend**: FastAPI + LangGraph + Gemini (Hosted on Render).
- **Frontend**: Gradio (Hosted on Hugging Face).

## 📁 Repository Structure
```text
.
├── backend/
│   ├── agent.py            # LangGraph logic (The Brain)
│   ├── server.py           # FastAPI + Telegram (The Body)
│   └── requirements.txt    # Python dependencies
├── product/                # Data files
├── tech/                   # Data files
├── policy/                 # Data files
├── app.py                  # Gradio UI
└── README.md               # This guide
```

## 🚀 Deployment

1.  **Push to GitHub**: This repo is ready for a private GitHub repository.
2.  **Deploy to Render**: Connect your repo to Render and choose the **Python** runtime.
3.  **Secrets**: Set the following in Render:
    - `GEMINI_API_KEY`
    - `BRAVE_API_KEY`
    - `TELEGRAM_BOT_TOKEN`
    - `INTERNAL_API_KEY` (Your secret key)
4.  **Hugging Face**: Upload `app.py` and set `BACKEND_API_URL` to your Render address.
