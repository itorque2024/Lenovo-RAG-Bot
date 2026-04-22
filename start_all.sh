#!/bin/bash

# Get the absolute path of the project directory
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

# Activate the project environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate lenovo-rag

echo "🚀 Starting Lenovo Data Server (API & Bot) on port 8000..."
# We use port 10000 locally to match the .env expected by Gradio
PYTHONPATH=$PYTHONPATH:. python backend/server.py &
SERVER_PID=$!

# Wait a few seconds for the server to wake up
sleep 5

echo "🚀 Starting Gradio UI (Web/Mobile)..."
python app.py &
GRADIO_PID=$!

echo "---------------------------------------------------"
echo "✅ Everything is running!"
echo "- API Backend: http://localhost:10000"
echo "- Gradio UI: Check the terminal for the .gradio.live link"
echo "- Telegram: Check your bot on Telegram"
echo "---------------------------------------------------"
echo "Press Ctrl+C to stop both servers."

# Trap Ctrl+C to kill both background processes
trap "kill $SERVER_PID $GRADIO_PID; exit" INT

wait
