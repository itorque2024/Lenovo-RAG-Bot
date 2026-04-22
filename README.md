# Lenovo RAG Multi-Agent Assistant

A lightweight, multi-agent RAG chatbot powered by **Google Gemini**, orchestrated by **n8n**, and accessible via **Telegram** and a **Web/Mobile UI (Gradio)**.

## 🚀 Features
- **Multi-Agent Architecture**: Specialized agents for Products, Tech Support, and Policies.
- **Dynamic Routing**: Uses Gemini to route complex, multi-part queries to the correct specialists.
- **RAG Capability**: Retrieves grounded information from local Markdown files.
- **Web Search Fallback**: Automatically searches DuckDuckGo if local data is insufficient.
- **Cross-Platform**: Accessible via a Gradio Web/Mobile link and Telegram.
- **Agent Attribution**: Responses clearly show which agent provided which part of the answer.

## 📁 Project Structure
- `tech/`, `policy/`, `product/`: Local knowledge base (Markdown content in `.txt` files).
- `app.py`: Gradio chat interface.
- `server.py`: FastAPI server that exposes local files to n8n.
- `download_data.py`: Script to refresh/scrape the latest Lenovo data.
- `n8n_workflow_guide.md`: Step-by-step blueprint for the n8n orchestration.
- `start_all.sh`: One-click script to start the UI and Data Server.

## 🛠️ Quick Start

### 1. Prerequisites
- [Conda](https://docs.conda.io/en/latest/miniconda.html) installed.
- [n8n](https://n8n.io/) installed (Local or Cloud).
- A **Google Gemini API Key** and a **Telegram Bot Token**.

### 2. Setup Environment
```bash
# The project uses a dedicated conda environment
conda activate lenovo-rag
```

### 3. Fetch Data
```bash
python download_data.py
```

### 4. Configure n8n
Follow the instructions in **`n8n_workflow_guide.md`** to set up your agents and tools. Make sure to use the **Gemini** model and connect the **DuckDuckGo** search node.

### 5. Launch the Chatbot
```bash
chmod +x start_all.sh
./start_all.sh
```
- Open the `.gradio.live` link provided in the terminal to access the Web UI.
- Open your Telegram bot to start messaging!

## 🌐 Deployment
- **Frontend (Gradio)**: Deploy to [Hugging Face Spaces](https://huggingface.co/spaces) using `requirements-gradio.txt`.
- **Backend (n8n)**: Deploy to [Render](https://render.com/) using the provided `render.yaml`.

## ⚙️ Configuration
Copy `.env.example` to `.env` and fill in your keys:
- `GEMINI_API_KEY`: Your Google AI Studio key.
- `TELEGRAM_BOT_TOKEN`: From @BotFather.
- `N8N_WEBHOOK_URL`: Your active n8n production webhook.
