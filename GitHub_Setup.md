# Final GitHub & Cloud Deployment Steps

## 1. Push to Private GitHub Repo
If you haven't yet, create a private repo on GitHub and run:
```bash
git remote add origin https://github.com/YOUR_USERNAME/Lenovo-RAG-Bot.git
git branch -M main
git push -u origin main
```

## 2. Deploy Backend to Render (Free)
1. Go to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** > **Blueprint**.
3. Connect your `Lenovo-RAG-Bot` repo.
4. **Environment Variables** (Under Settings > Env Vars):
   - `GEMINI_API_KEY`: Your key from Google AI Studio.
   - `TELEGRAM_BOT_TOKEN`: From @BotFather.
   - `INTERNAL_API_KEY`: A secret string (e.g., `lenovo-secret-2026`).
5. Render will deploy **n8n** and the **Data API** automatically.

## 3. Deploy Frontend to Hugging Face (Free)
1. Create a new **Space** on [huggingface.co/new-space](https://huggingface.co/new-space).
2. Select **Gradio** SDK.
3. Upload your `app.py` and `requirements-gradio.txt`.
4. Add the `N8N_WEBHOOK_URL` as a secret in the Space settings.

## 4. Final n8n Import
1. Open your new n8n cloud URL.
2. Drag and drop `lenovo-n8n-workflow.json` into the canvas.
3. **Important**: In the `File_Tool` node, update the URL to your Render Data API URL and set the `X-API-KEY` header to match your `INTERNAL_API_KEY`.

---
**Congratulations!** You've built a full-stack, multi-agent RAG chatbot in under 3 hours. It's secure, cloud-hosted, and supports both Web and Telegram.
