from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from backend.agent import get_agent_response

# Set up logging to help us see exactly what's happening in Railway
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Lenovo AI Assistant")

# --- Endpoints (Security REMOVED for immediate fix) ---
@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        message = data.get("message")
        if not message:
            return JSONResponse({"error": "No message"}, status_code=400)
        
        logger.info(f"Received query: {message}")
        response = await get_agent_response(message)
        return {"output": response}
    except Exception as e:
        logger.error(f"Error in /chat: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/health")
async def health():
    return {"status": "healthy"}

# --- Telegram Bot ---
async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    logger.info(f"Telegram message: {update.message.text}")
    response_text = await get_agent_response(update.message.text)
    await update.message.reply_text(response_text)

async def start_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    # In cloud environments, PORT is usually defined. 
    # We use this to detect if we are in production.
    is_cloud = "PORT" in os.environ or "RAILWAY_STATIC_URL" in os.environ
    
    if not token:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN missing.")
        return

    if not is_cloud:
        logger.info("ℹ️ Local environment detected. Skipping Telegram bot to avoid conflicts.")
        return

    try:
        application = Application.builder().token(token).build()
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))
        
        await application.initialize()
        await application.start()
        # drop_pending_updates=True is the cure for "Conflict" errors
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("🚀 Telegram Bot is ONLINE and Polling.")
    except Exception as e:
        logger.error(f"❌ Telegram Error: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_telegram())

# File serving
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
@app.get("/files/{folder}/{filename}")
async def get_file(folder: str, filename: str):
    file_path = os.path.join(BASE_DIR, folder, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
