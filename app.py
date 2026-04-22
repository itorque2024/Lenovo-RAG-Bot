import gradio as gr
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("BACKEND_API_URL", "http://localhost:10000/chat")

def chat_with_agent(message, history):
    try:
        response = requests.post(
            API_URL,
            json={"message": message},
            timeout=90
        )
        response.raise_for_status()
        return response.json().get("output", "Error: No response from agent.")
    except Exception as e:
        return f"⚠️ **Error connecting to backend:** {e}"

view = gr.ChatInterface(
    fn=chat_with_agent,
    title="Lenovo AI Multi-Agent Assistant",
    description="### Powered by Groq + LangGraph\nAsk me about Lenovo products, tech support, policies, or pricing.",
    examples=[
        "What are the specs of the ThinkPad X1 Carbon?",
        "How much is the Yoga 7i in SGD?",
        "What is the return policy?",
        "My ThinkPad won't boot, how do I fix it?",
        "What is the price of the X1 Carbon and what is the return policy?",
    ],
    cache_examples=False,
)

if __name__ == "__main__":
    view.launch()
