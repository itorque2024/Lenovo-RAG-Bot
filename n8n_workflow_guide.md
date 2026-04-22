# n8n Multi-Agent RAG Setup Guide

To reach your 3-hour target, follow these steps to build the n8n workflow.

## 1. Trigger Nodes
*   **Webhook Node**: 
    - HTTP Method: `POST`
    - Path: `lenovo-chat`
    - Respond: `Immediately`
*   **Telegram Trigger**:
    - Connect your `TELEGRAM_BOT_TOKEN`.
    - Updates: `Message`.

## 2. AI Orchestration
*   **AI Agent Node**: This is the "Supervisor".
    - **Model**: Google Gemini (`gemini-pro`).
    - **Prompt**: 
      > "You are the Lenovo Multi-Agent Orchestrator. You have access to three specialist agents (Product, Tech, Policy) and a Web Search tool.
      >
      > **RULES**:
      > 1. If a query has multiple parts, call the relevant specialists for each part.
      > 2. Each response part MUST be prefixed with the agent name in brackets, e.g., '[Product Agent]: ...'.
      > 3. If information is missing from local files, use the 'Web Search' tool and prefix with '[Search Agent]'.
      > 4. Combine all specialist answers into a single, cohesive response."

## 3. Specialized Tools (The Agents)
Add these as "Tools" to your AI Agent node:

### A. File Retrieval Tool (Local API)
- **Node Type**: `HTTP Request`.
- **URL**: `http://localhost:8000/files/{{$node["Supervisor"].json["folder"]}}/{{$node["Supervisor"].json["file"]}}`
- **Description**: "Fetches the content of the Lenovo Markdown files from the local server."

### B. Currency Converter (New Tool)
- **Node Type**: `HTTP Request`.
- **URL**: `https://api.exchangerate-api.com/v4/latest/USD`
- **Description**: "Use this tool to convert Lenovo USD prices into local currency (SGD, etc.)."

### C. Serial Number Validator (New Tool)
- **Node Type**: `Code Node` (Python or JS).
- **Description**: "Validates the format of a Lenovo Serial Number (usually 8 characters, alphanumeric)."

### B. Tech Support Agent (Local RAG)
- **Node Type**: `Vector Store Tool`.
- **Data Source**: Document Loader pointing to `tech/tech_support.txt`.
- **Description**: "Use this tool for troubleshooting, finding serial numbers, and hardware repair procedures."

### C. Policy Agent (Local RAG)
- **Node Type**: `Vector Store Tool`.
- **Data Source**: Document Loader pointing to `policy/delivery.txt`, `policy/warranty.txt`, and `policy/returns & refund.txt`.
- **Description**: "Use this tool for shipping times, return windows, refunds, and warranty terms."

### D. Search Agent (DuckDuckGo)
- **Node Type**: `DuckDuckGo Search`.
- **Description**: "Use this tool ONLY if the other specialist agents do not have the information in their files (e.g., current news or external reviews)."

## 4. Response
- **Webhook Response**: Send the AI Agent's output back to the Webhook.
- **Telegram Send Message**: Send the AI Agent's output back to the user's Chat ID.
