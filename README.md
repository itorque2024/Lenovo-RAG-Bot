# Lenovo RAG Multi-Agent Assistant (Production)

A secure, full-stack, multi-agent Retrieval-Augmented Generation (RAG) chatbot system. Powered by **Google Gemini**, orchestrated by **n8n**, and deployed on a distributed cloud architecture.

## 🌟 Features

### 1. Multi-Agent Intelligence
- **Supervisor Agent (Gemini)**: Routes queries to specific specialists based on intent.
- **Product Specialist**: Provides specs and pricing from the `product/` knowledge base.
- **Tech Specialist**: Handles troubleshooting and repairs using the `tech/` knowledge base.
- **Policy Specialist**: Manages inquiries about shipping, warranty, and returns from `policy/`.
- **Search Specialist (DuckDuckGo)**: Fallback for current news or data not found locally.

### 2. Specialized Capabilities (Tools)
- **RAG Engine**: Dynamic retrieval from local Markdown files (`.txt` extension).
- **Serial Number Validator**: Validates Lenovo SN formats (8 alphanumeric chars).
- **Currency Converter**: Converts Lenovo USD pricing to SGD (or other local currencies).
- **Query Logger**: Persistent server-side logging of all user interactions in `queries.log`.

### 3. Cross-Platform Interfaces
- **Web/Mobile UI**: Responsive Chat interface built with **Gradio**.
- **Telegram Bot**: Full integration via n8n for mobile messaging.

## 🛡️ Security & Integrity

- **Environment Isolation**: The entire stack is contained within a dedicated `lenovo-rag` Conda environment.
- **Data Protection**: 
  - **X-API-KEY**: All cloud-hosted Data API endpoints are protected by a mandatory secret header.
  - **Local Binding**: Local development server binds only to `127.0.0.1` to prevent unauthorized network access.
- **Source Control**: Robust `.gitignore` prevents API keys, `.env` files, and local logs from being exposed on GitHub.
- **n8n Security**: Configured for mandatory Basic Authentication.

## 🏗️ Architecture

1.  **Data API (FastAPI)**: Serves the knowledge base and tools (Hosted on Render).
2.  **Orchestrator (n8n)**: The multi-agent brain that connects Gemini, Tools, and Triggers (Hosted on Render).
3.  **Frontend (Gradio)**: The user interface that communicates with the n8n webhook (Hosted on Hugging Face).

## 📁 Repository Structure
```text
.
├── backend/
│   ├── server.py           # FastAPI server (Data & Tools)
│   ├── download_data.py    # Lenovo US scraper
│   ├── scraper.py          # Category-based scraper
│   └── .env.example        # Template for credentials
├── product/                # Product knowledge base
├── tech/                   # Tech Support knowledge base
├── policy/                 # Policies knowledge base
├── app.py                  # Gradio Web UI
├── n8n_workflow_guide.md   # Step-by-step logic guide
├── lenovo-n8n-workflow.json # Importable n8n logic
├── render.yaml             # Blueprint for Render deployment
├── n8n.Dockerfile          # Container for cloud n8n
├── start_all.sh            # Unified server launcher
└── README.md               # This document
```

## 🚀 Quick Start (GCP/Cloud Ready)

1.  **Initialize Environment**:
    `conda activate lenovo-rag`
2.  **Start Services**:
    `./start_all.sh`
3.  **Deploy Backend**:
    Push this repo to a **Private** GitHub repository and connect it to **Render** using the "Blueprint" feature.
4.  **Import Workflow**:
    Copy the contents of `lenovo-n8n-workflow.json` and paste them into your n8n cloud dashboard.
5.  **Set Secrets**:
    Configure `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, and `INTERNAL_API_KEY` in your cloud dashboard.

## 🛠️ Maintenance
To refresh the local knowledge base with the latest Lenovo US data, run:
`python backend/download_data.py`
