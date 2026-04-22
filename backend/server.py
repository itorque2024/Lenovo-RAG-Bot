from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import FileResponse, JSONResponse
import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from backend.agent import get_agent_response

app = FastAPI(title="Lenovo Multi-Agent RAG API")

# --- Security ---
API_KEY = os.getenv("INTERNAL_API_KEY", "default_secret_key")
api_key_header = APIKeyHeader(name="X-API-KEY")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Unauthorized")

# --- Endpoints ---
@app.post("/chat", dependencies=[Depends(get_api_key)])
async def chat_endpoint(request: Request):
    data = await request.json()
    message = data.get("message")
    if not message:
        return JSONResponse({"error": "No message"}, status_code=400)
    
    response = await get_agent_response(message)
    return {"output": response}

# --- Telegram Bot ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return
    response_text = await get_agent_response(user_text)
    await update.message.reply_text(response_text)

async def start_telegram():
    if not TELEGRAM_TOKEN:
        print("⚠️ TELEGRAM_BOT_TOKEN not found. Telegram bot disabled.")
        return
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        print("🚀 Telegram Bot is polling...")
    except Exception as e:
        print(f"❌ CRITICAL ERROR starting Telegram bot: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_telegram())

# Existing file serving routes (simplified)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
@app.get("/files/{folder}/{filename}")
async def get_file(folder: str, filename: str):
    file_path = os.path.join(BASE_DIR, folder, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
