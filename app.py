import gradio as gr
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("BACKEND_API_URL", "http://localhost:10000/chat")

def respond(message, history):
    if not message.strip():
        return history, ""
    try:
        response = requests.post(
            API_URL,
            json={"message": message},
            timeout=90
        )
        response.raise_for_status()
        bot_reply = response.json().get("output", "Error: No response from agent.")
    except Exception as e:
        bot_reply = f"⚠️ **Error connecting to backend:** {e}"

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": bot_reply}
    ]
    return history, ""

with gr.Blocks(title="Lenovo AI Assistant") as demo:
    gr.Markdown("# Lenovo AI Multi-Agent Assistant")
    gr.Markdown("Powered by **Groq + LangGraph** · Ask about products, tech support, policies, or pricing.")

    chatbot = gr.Chatbot(height=500)

    with gr.Row():
        msg_box = gr.Textbox(
            placeholder="Ask me anything about Lenovo...",
            label="",
            scale=9,
            autofocus=True
        )
        send_btn = gr.Button("Send", scale=1, variant="primary")

    gr.Examples(
        examples=[
            "What are the specs of the ThinkPad X1 Carbon?",
            "How much is the Yoga 7i in SGD?",
            "What is the return policy?",
            "My ThinkPad won't boot, how do I fix it?",
            "What is the X1 Carbon price and what is the return policy?",
        ],
        inputs=msg_box,
        label="Example questions"
    )

    clear_btn = gr.Button("Clear chat", variant="secondary")

    msg_box.submit(respond, [msg_box, chatbot], [chatbot, msg_box])
    send_btn.click(respond, [msg_box, chatbot], [chatbot, msg_box])
    clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg_box])

if __name__ == "__main__":
    demo.launch()
