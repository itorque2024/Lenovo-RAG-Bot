from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from backend.agent import get_agent_response, initialize_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_FOLDERS = {"product", "tech", "policy"}

# ─── Telegram ─────────────────────────────────────────────────────────────────

async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    logger.info(f"Telegram message: {update.message.text}")
    response_text = await get_agent_response(update.message.text)
    await update.message.reply_text(response_text)


async def start_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    is_cloud = "PORT" in os.environ or "RAILWAY_STATIC_URL" in os.environ

    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN missing — Telegram bot disabled.")
        return
    if not is_cloud:
        logger.info("Local environment — Telegram bot skipped to avoid conflicts.")
        return

    try:
        application = Application.builder().token(token).build()
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message)
        )
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram Bot is ONLINE.")
    except Exception as e:
        logger.error(f"Telegram error: {e}")

# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing agent and pre-loading retrievers...")
    initialize_agent()
    logger.info("Agent ready.")
    asyncio.create_task(start_telegram())
    yield

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


@app.get("/files/{folder}/{filename}")
async def get_file(folder: str, filename: str):
    # Restrict to known folders and block path traversal
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
