#!/bin/bash

# Activate the project environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate lenovo-rag

echo "🚀 Starting Lenovo Data Server on port 8000..."
python server.py &
SERVER_PID=$!

echo "🚀 Starting Gradio UI (Web/Mobile)..."
python app.py &
GRADIO_PID=$!

echo "---------------------------------------------------"
echo "✅ Both servers are running!"
echo "- Data Server: http://localhost:8000"
echo "- Gradio UI: Check the terminal for the .gradio.live link"
echo "- n8n: Ensure n8n is running and its webhook is active."
echo "---------------------------------------------------"
echo "Press Ctrl+C to stop both servers."

# Trap Ctrl+C to kill both background processes
trap "kill $SERVER_PID $GRADIO_PID; exit" INT

wait
