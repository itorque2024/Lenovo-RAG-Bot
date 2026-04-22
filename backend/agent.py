import os
from typing import Annotated, List, Union
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
import requests

# --- Global State ---
_app_agent = None

@tool("currency_converter")
def currency_converter(amount: float, from_currency: str = "USD", to_currency: str = "SGD"):
    """Converts money from one currency to another."""
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
        data = requests.get(url).json()
        rate = data["rates"][to_currency.upper()]
        return f"[Finance Agent]: {amount} {from_currency} is ~{round(amount * rate, 2)} {to_currency}"
    except:
        return "Error converting currency."

@tool("brave_search")
def brave_search(query: str):
    """Search the live web using Brave Search."""
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key: return "Brave API key missing."
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    try:
        data = requests.get(url, headers=headers, params={"q": query, "count": 2}).json()
        results = data.get("web", {}).get("results", [])
        return "\n".join([f"- {r['title']}: {r['description']}" for r in results])
    except:
        return "Search failed."

def create_rag_tool(folder: str, agent_name: str, google_api_key: str):
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), folder)
        docs = []
        if os.path.exists(path):
            for f in os.listdir(path):
                if f.endswith(".txt"):
                    loader = TextLoader(os.path.join(path, f))
                    docs.extend(loader.load())
        if not docs: raise ValueError()
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=google_api_key)
        vectorstore = FAISS.from_documents(docs, embeddings)
        retriever = vectorstore.as_retriever()

        @tool(f"search_{folder}")
        def rag_tool(query: str):
            """Useful for Lenovo specific info."""
            results = retriever.invoke(query)
            return f"[{agent_name}]: " + "\n".join([d.page_content for d in results])
        return rag_tool
    except:
        @tool(f"search_{folder}")
        def fallback_tool(query: str):
            """Fallback if files missing."""
            return f"[{agent_name}]: Local data unavailable. Please use search."
        return fallback_tool

def initialize_agent():
    global _app_agent
    if _app_agent: return _app_agent
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key: raise ValueError("GEMINI_API_KEY MISSING")

    all_tools = [
        create_rag_tool("product", "Product Agent", api_key),
        create_rag_tool("tech", "Tech Agent", api_key),
        create_rag_tool("policy", "Policy Agent", api_key),
        currency_converter,
        brave_search
    ]

    class AgentState(TypedDict):
        messages: Annotated[List[BaseMessage], lambda x, y: x + y]

    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
    model_with_tools = model.bind_tools(all_tools)

    def call_model(state):
        sys_msg = HumanMessage(content="You are the Lenovo Assistant. Answer accurately using local data if available. Prefix answers with [Agent Name].")
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
    try:
        agent = initialize_agent()
        result = await agent.ainvoke({"messages": [HumanMessage(content=user_input)]})
        return result["messages"][-1].content
    except Exception as e:
        return f"❌ Error: {e}"
