import gradio as gr
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Backend API URL
API_URL = os.getenv("BACKEND_API_URL", "http://localhost:10000/chat")

def chat_with_agent(message, history):
    try:
        payload = {
            "message": message,
            "source": "web_ui",
            "history": history
        }
        
        # Security removed for immediate connection fix
        response = requests.post(API_URL, json=payload, timeout=90)
        response.raise_for_status()
        
        data = response.json()
        return data.get("output", "Error: No response from agent.")
            
    except Exception as e:
        return f"⚠️ **Error connecting to AI backend:** {e}\n\n*Check if your Railway URL is correct in your .env file.*"

# Build Gradio Chat Interface
view = gr.ChatInterface(
    fn=chat_with_agent,
    title="Lenovo AI Multi-Agent Assistant",
    description="### 🤖 Powered by Gemini + LangGraph\nAsk me about Lenovo products, support, or policies.",
    examples=[
        "What are the specs of the ThinkPad X1 Carbon?",
        "How much is the Yoga 7i in SGD?",
        "What is the return policy?"
    ],
    cache_examples=False,
)

if __name__ == "__main__":
    view.launch(share=True)
