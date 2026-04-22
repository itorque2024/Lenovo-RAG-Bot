import gradio as gr
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# n8n Webhook URL - Replace this with your actual n8n webhook URL
# If running locally, you might need to use ngrok to expose it
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/lenovo-chat")

def chat_with_n8n(message, history):
    try:
        payload = {
            "message": message,
            "source": "web_ui",
            "history": history # Sending history to n8n for context
        }
        
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different potential n8n response formats
        # We expect a string or an object with an 'output' field
        # The output should ideally look like "[Agent Name]: ... \n\n [Agent Name]: ..."
        if isinstance(data, list) and len(data) > 0:
            output = data[0].get("output", str(data[0]))
        elif isinstance(data, dict):
            output = data.get("output", str(data))
        else:
            output = str(data)
            
        return output
            
    except Exception as e:
        return f"⚠️ **Error connecting to n8n backend:** {e}\n\n*Make sure your n8n workflow is active and the webhook URL is correct.*"

# Build Gradio Chat Interface with a more modern look
view = gr.ChatInterface(
    fn=chat_with_n8n,
    title="Lenovo Multi-Agent Assistant",
    description="### 🤖 Powered by Gemini + n8n RAG\nI can answer questions about products, tech support, and policies. If I don't know the answer, I'll search the web!",
    examples=[
        "What are the specs of the ThinkPad X1 Carbon and what is the return policy?",
        "How do I find my serial number?",
        "Is there a warranty for the laptop battery?"
    ],
    cache_examples=False,
)

if __name__ == "__main__":
    view.launch(share=True) # share=True gives you a temporary public URL
