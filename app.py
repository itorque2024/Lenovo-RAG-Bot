import gradio as gr
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Backend API URL - Replace this with your actual Render/Railway API URL
API_URL = os.getenv("BACKEND_API_URL", "http://localhost:10000/chat")
# The secret key set in your environment variables
API_KEY = os.getenv("INTERNAL_API_KEY", "default_secret_key")

def chat_with_agent(message, history):
    try:
        payload = {
            "message": message,
            "source": "web_ui",
            "history": history
        }
        
        # WE MUST SEND THE API KEY IN THE HEADERS
        headers = {
            "X-API-KEY": API_KEY
        }
        
        response = requests.post(API_URL, json=payload, headers=headers, timeout=90)
        response.raise_for_status()
        
        data = response.json()
        return data.get("output", "Error: No response from agent.")
            
    except Exception as e:
        return f"⚠️ **Error connecting to AI backend:** {e}\n\n*Make sure your backend is active and the URL is correct.*"

# Build Gradio Chat Interface
view = gr.ChatInterface(
    fn=chat_with_agent,
    title="Lenovo AI Multi-Agent Assistant",
    description="### 🤖 Powered by Gemini + LangGraph\nI can answer questions about products, tech support, and policies. If I don't know the answer, I'll search the web!",
    examples=[
        "What are the specs of the ThinkPad X1 Carbon and what is the return policy?",
        "How much is the Yoga 7i in SGD?",
        "How do I find my serial number?"
    ],
    cache_examples=False,
)

if __name__ == "__main__":
    view.launch(share=True)
