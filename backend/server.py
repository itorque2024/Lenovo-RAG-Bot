from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from backend.agent import get_agent_response, initialize_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_FOLDERS = {"product", "tech", "policy"}

# ─── Telegram setup ───────────────────────────────────────────────────────────

_telegram_app: Application | None = None


async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    logger.info(f"Telegram message: {update.message.text}")
    response_text = await get_agent_response(update.message.text)
    await update.message.reply_text(response_text)


async def setup_telegram_webhook(application: Application, webhook_url: str):
    await application.bot.set_webhook(
        url=f"{webhook_url}/telegram/webhook",
        drop_pending_updates=True
    )
    logger.info(f"Telegram webhook set → {webhook_url}/telegram/webhook")

# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _telegram_app

    logger.info("Initializing agent and pre-loading retrievers...")
    initialize_agent()
    logger.info("Agent ready.")

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    webhook_url = os.getenv("WEBHOOK_URL") or os.getenv("RAILWAY_STATIC_URL")

    if token and webhook_url:
        # Webhook mode — reliable on cloud (Telegram calls us, we don't poll)
        webhook_url = webhook_url.rstrip("/")
        _telegram_app = Application.builder().token(token).updater(None).build()
        _telegram_app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message)
        )
        await _telegram_app.initialize()
        await _telegram_app.start()
        await setup_telegram_webhook(_telegram_app, webhook_url)
    elif token:
        logger.warning(
            "TELEGRAM_BOT_TOKEN set but WEBHOOK_URL is missing — Telegram disabled. "
            "Set WEBHOOK_URL to your Railway public URL."
        )
    else:
        logger.info("No TELEGRAM_BOT_TOKEN — Telegram bot disabled.")

    yield

    if _telegram_app:
        await _telegram_app.stop()

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Lenovo AI Assistant", lifespan=lifespan)

# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        message = data.get("message")
        if not message:
            return JSONResponse({"error": "No message"}, status_code=400)
        logger.info(f"Query: {message}")
        response = await get_agent_response(message)
        return {"output": response}
    except Exception as e:
        logger.error(f"Error in /chat: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Telegram calls this endpoint when a user sends a message."""
    if _telegram_app is None:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    data = await request.json()
    update = Update.de_json(data, _telegram_app.bot)
    await _telegram_app.process_update(update)
    return {"ok": True}


@app.get("/files/{folder}/{filename}")
async def get_file(folder: str, filename: str):
    if folder not in ALLOWED_FOLDERS:
        raise HTTPException(status_code=403, detail="Forbidden")
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(BASE_DIR, folder, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404)
    return FileResponse(file_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
