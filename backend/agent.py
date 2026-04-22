import os
from typing import Annotated, List, Union
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
import requests

# --- Global State for Persistence ---
_app_agent = None

@tool("currency_converter")
def currency_converter(amount: float, from_currency: str = "USD", to_currency: str = "SGD"):
    """Converts money from one currency to another using live rates."""
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
        data = requests.get(url).json()
        rate = data["rates"][to_currency.upper()]
        converted = round(amount * rate, 2)
        return f"[Finance Agent]: {amount} {from_currency} is approximately {converted} {to_currency} (Rate: {rate})"
    except Exception as e:
        return f"Error converting currency: {e}"

@tool("brave_search")
def brave_search(query: str):
    """Search the live web using Brave Search for current news or info not in local files."""
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return "[Search Agent]: Brave API key is missing."
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    try:
        response = requests.get(url, headers=headers, params={"q": query, "count": 3})
        data = response.json()
        results = data.get("web", {}).get("results", [])
        formatted = "\n".join([f"- {r['title']}: {r['description']} ({r['url']})" for r in results])
        return f"[Search Agent]: Found on web via Brave:\n{formatted}"
    except Exception as e:
        return f"[Search Agent]: Error with Brave Search: {e}"

def create_rag_tool(folder: str, agent_name: str, google_api_key: str):
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_path = os.path.join(base_path, folder)
        
        docs = []
        if os.path.exists(data_path):
            for f in os.listdir(data_path):
                if f.endswith(".txt"):
                    loader = TextLoader(os.path.join(data_path, f))
                    docs.extend(loader.load())
        
        if not docs:
            raise ValueError(f"No documents in {folder}")

        # Explicitly use v1 API for stable production access
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key=google_api_key
        )
        vectorstore = FAISS.from_documents(docs, embeddings)
        retriever = vectorstore.as_retriever()

        @tool(f"search_{folder}")
        def rag_tool(query: str):
            """Useful for answering Lenovo specific questions."""
            results = retriever.invoke(query)
            content = "\n".join([d.page_content for d in results])
            return f"[{agent_name}]: {content}"
        return rag_tool
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize {agent_name}: {e}")
        @tool(f"search_{folder}")
        def fallback_tool(query: str):
            """Fallback when local data is unavailable."""
            return f"[{agent_name}]: Local {folder} data is currently unavailable."
        return fallback_tool

def initialize_agent():
    global _app_agent
    if _app_agent: return _app_agent

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY environment variable.")

    all_tools = [
        create_rag_tool("product", "Product Agent", api_key),
        create_rag_tool("tech", "Tech Agent", api_key),
        create_rag_tool("policy", "Policy Agent", api_key),
        currency_converter,
        brave_search
    ]

    class AgentState(TypedDict):
        messages: Annotated[List[BaseMessage], lambda x, y: x + y]

    # Use standard production model name
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        google_api_key=api_key
    )
    model_with_tools = model.bind_tools(all_tools)

    def call_model(state):
        sys_msg = SystemMessage(content="You are the Lenovo Multi-Agent Assistant. Answer using tools. Prefix EVERY part of your answer with the agent name in brackets, e.g. [Product Agent].")
        return {"messages": [model_with_tools.invoke([sys_msg] + state['messages'])]}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(all_tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", lambda x: "tools" if x['messages'][-1].tool_calls else END)
    workflow.add_edge("tools", "agent")
    
    _app_agent = workflow.compile()
    return _app_agent

async def get_agent_response(user_input: str):
    agent = initialize_agent()
    result = await agent.ainvoke({"messages": [HumanMessage(content=user_input)]})
    return result["messages"][-1].content
