from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import FileResponse, JSONResponse
import os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from backend.agent import get_agent_response

app = FastAPI(title="Lenovo Multi-Agent RAG API")

# --- Security ---
API_KEY = os.getenv("INTERNAL_API_KEY", "default_secret_key")
api_key_header = APIKeyHeader(name="X-API-KEY")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY: return api_key_header
    raise HTTPException(status_code=403, detail="Unauthorized")

# --- Endpoints ---
@app.post("/chat", dependencies=[Depends(get_api_key)])
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        message = data.get("message")
        if not message: return JSONResponse({"error": "No message"}, status_code=400)
        response = await get_agent_response(message)
        return {"output": response}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/health")
async def health(): return {"status": "healthy"}

# --- Telegram Bot ---
async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    response_text = await get_agent_response(update.message.text)
    await update.message.reply_text(response_text)

async def start_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or os.getenv("RUN_TELEGRAM") != "true":
        print("ℹ️ Telegram bot disabled.")
        return
    try:
        application = Application.builder().token(token).build()
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        print("🚀 Telegram Bot is online.")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

@app.on_event("startup")
async def startup():
    asyncio.create_task(start_telegram())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
