import os
from typing import Annotated, List, Union
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
import requests

# 1. Define Tools
@tool
def currency_converter(amount: float, from_currency: str = "USD", to_currency: str = "SGD"):
    """Converts money from one currency to another using live rates."""
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
        response = requests.get(url)
        data = response.json()
        rate = data["rates"][to_currency.upper()]
        converted = round(amount * rate, 2)
        return f"[Finance Agent]: {amount} {from_currency} is approximately {converted} {to_currency} (Rate: {rate})"
    except Exception as e:
        return f"Error converting currency: {e}"

@tool
def brave_search(query: str):
    """Search the live web using Brave Search for current news or info not in local files."""
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return "[Search Agent]: Brave API key is missing."
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {"q": query, "count": 3}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        results = data.get("web", {}).get("results", [])
        formatted = "\n".join([f"- {r['title']}: {r['description']} ({r['url']})" for r in results])
        return f"[Search Agent]: Found on web via Brave:\n{formatted}"
    except Exception as e:
        return f"[Search Agent]: Error with Brave Search: {e}"

# 2. RAG Tools (Product, Tech, Policy)
def create_rag_tool(folder: str, agent_name: str):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), folder)
    print(f"📂 Searching for data in: {path}")
    docs = []
    if os.path.exists(path):
        for f in os.listdir(path):
            if f.endswith(".txt"):
                print(f"📄 Loading: {f}")
                loader = TextLoader(os.path.join(path, f))
                docs.extend(loader.load())
    
    if not docs:
        print(f"⚠️ Warning: No documents found for {agent_name}")
        @tool(name=f"search_{folder}")
        def empty_tool(query: str):
            """Returns a warning that no data is available."""
            return f"[{agent_name}]: No data files found for {folder} on the server."
        return empty_tool

    # Using Google API embeddings (fast and lightweight)
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )
    vectorstore = FAISS.from_documents(docs, embeddings)
    retriever = vectorstore.as_retriever()

    @tool(name=f"search_{folder}")
    def rag_tool(query: str):
        """Useful for answering questions about Lenovo categories."""
        results = retriever.invoke(query)
        content = "\n".join([d.page_content for d in results])
        return f"[{agent_name}]: Based on local files: {content}"
    
    return rag_tool

product_tool = create_rag_tool("product", "Product Agent")
tech_tool = create_rag_tool("tech", "Tech Agent")
policy_tool = create_rag_tool("policy", "Policy Agent")

tools = [product_tool, tech_tool, policy_tool, currency_converter, brave_search]

# 3. Define the Graph
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]

model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", streaming=True)
model_with_tools = model.bind_tools(tools)

def call_model(state: AgentState):
    messages = state['messages']
    system_prompt = HumanMessage(content=(
        "You are the Lenovo Multi-Agent Assistant. "
        "Use specialists for specific tasks. "
        "ALWAYS prefix your final answer parts with the agent name in brackets, e.g. [Product Agent]. "
        "Answer all parts of complex queries."
    ))
    response = model_with_tools.invoke([system_prompt] + messages)
    return {"messages": [response]}

# 4. Build the Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))
workflow.set_entry_point("agent")

def should_continue(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

app_agent = workflow.compile()

async def get_agent_response(user_input: str):
    inputs = {"messages": [HumanMessage(content=user_input)]}
    config = {"configurable": {"thread_id": "1"}}
    final_output = ""
    async for event in app_agent.astream(inputs, config=config):
        for value in event.values():
            if "messages" in value:
                final_output = value["messages"][-1].content
    return final_output
