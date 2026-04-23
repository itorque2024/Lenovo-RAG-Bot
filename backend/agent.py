import os
import requests
from typing import List, TypedDict

from langchain_groq import ChatGroq
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

# ─── State ────────────────────────────────────────────────────────────────────

class Task(TypedDict):
    agent: str
    sub_query: str

class AgentState(TypedDict):
    query: str
    tasks: List[Task]
    responses: List[dict]
    debug_log: str

# ─── Singletons ───────────────────────────────────────────────────────────────

_llm = None
_embeddings = None
_retrievers: dict = {}
_react_agents: dict = {}
_graph = None


def _get_llm():
    global _llm
    if _llm is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY environment variable.")
        _llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=api_key,
            temperature=0.3
        )
    return _llm


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return _embeddings


def _get_retriever(folder: str):
    if folder in _retrievers:
        return _retrievers[folder]

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, folder)
    docs = []
    if os.path.exists(path):
        for f in os.listdir(path):
            if f.endswith(".txt") or f.endswith(".md"):
                try:
                    docs.extend(TextLoader(os.path.join(path, f)).load())
                except Exception:
                    pass

    if not docs:
        _retrievers[folder] = None
        return None

    store = FAISS.from_documents(docs, _get_embeddings())
    _retrievers[folder] = store.as_retriever()
    return _retrievers[folder]

# ─── Tools ────────────────────────────────────────────────────────────────────

@tool("product_rag_search")
def product_rag_search(query: str) -> str:
    """Search Lenovo internal product catalog for specs, prices, models, and availability."""
    retriever = _get_retriever("product")
    if not retriever:
        return "No local product data available."
    docs = retriever.invoke(query)
    return "\n\n".join(d.page_content for d in docs) if docs else "No matching results in local product data."


@tool("tech_rag_search")
def tech_rag_search(query: str) -> str:
    """Search Lenovo internal technical support documents for troubleshooting and how-to guides."""
    retriever = _get_retriever("tech")
    if not retriever:
        return "No local tech support data available."
    docs = retriever.invoke(query)
    return "\n\n".join(d.page_content for d in docs) if docs else "No matching results in local tech data."


@tool("policy_rag_search")
def policy_rag_search(query: str) -> str:
    """Search Lenovo internal policy documents for delivery, returns, refunds, and warranty info."""
    retriever = _get_retriever("policy")
    if not retriever:
        return "No local policy data available."
    docs = retriever.invoke(query)
    return "\n\n".join(d.page_content for d in docs) if docs else "No matching results in local policy data."


@tool("brave_web_search")
def brave_web_search(query: str) -> str:
    """Search the web for current Lenovo information, news, or anything not found in local data."""
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return "Web search is unavailable (Brave API key not configured)."
    try:
        res = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            params={"q": query, "count": 3},
            timeout=10
        )
        results = res.json().get("web", {}).get("results", [])
        return "\n".join(
            f"- {r['title']}: {r.get('description', '')} ({r['url']})"
            for r in results
        ) or "No web results found."
    except Exception as e:
        return f"Search error: {e}"

# ─── ReAct agent factory ──────────────────────────────────────────────────────

def _get_react_agent(name: str, tools: list, system_prompt: str):
    if name in _react_agents:
        return _react_agents[name]
    agent = create_react_agent(
        _get_llm(),
        tools=tools,
        prompt=system_prompt
    )
    _react_agents[name] = agent
    return agent


def _extract_response(result: dict) -> str:
    """Pull the final text answer out of a create_react_agent result."""
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", []):
            return msg.content
    return "No response generated."

# ─── Router Node ──────────────────────────────────────────────────────────────

def router_node(state: AgentState) -> dict:
    router_prompt = """You are a Router for a Lenovo AI Assistant.

Your job is to DECOMPOSE the user query into one or more sub-questions and assign each to the correct agent.

Available agents:
- product_agent  : product specs, prices, models, ThinkPad, IdeaPad, Legion, Yoga
- tech_agent     : troubleshooting, drivers, repair, how-to, technical support
- policy_agent   : delivery, shipping, returns, refunds, warranty policy, payment
- finance_agent  : currency conversion, price in SGD / USD / EUR or any other currency
- search_agent   : current news, latest releases, real-time info not in local data
- general_agent  : greetings, small talk, general questions, anything not covered above

Rules:
- Split multi-part questions so each agent only receives the portion it should answer
- One line per task, format exactly as: agent_name|sub-question
- Do not add explanation, numbering, or extra text

Example input: "What is the price of the X1 Carbon and what is the return policy?"
Example output:
product_agent|What is the price of the X1 Carbon?
policy_agent|What is the return policy?

Example input: "Hi, how are you?"
Example output:
general_agent|Hi, how are you?"""

    res = _get_llm().invoke([
        SystemMessage(content=router_prompt),
        HumanMessage(content=state["query"])
    ])

    valid = {"product_agent", "tech_agent", "policy_agent", "finance_agent", "search_agent", "general_agent"}
    tasks: List[Task] = []

    for line in res.content.strip().splitlines():
        line = line.strip()
        if "|" not in line:
            continue
        agent, sub_query = line.split("|", 1)
        agent = agent.strip().lower()
        sub_query = sub_query.strip()
        if agent in valid and sub_query:
            tasks.append({"agent": agent, "sub_query": sub_query})

    if not tasks:
        tasks = [{"agent": "general_agent", "sub_query": state["query"]}]

    agents_listed = ", ".join(t["agent"] for t in tasks)
    return {
        "tasks": tasks,
        "responses": [],
        "debug_log": f"🚦 Router decomposed into {len(tasks)} task(s): {agents_listed}"
    }

# ─── Routing logic ────────────────────────────────────────────────────────────

def _route_next(state: AgentState) -> str:
    tasks = state.get("tasks", [])
    done = len(state.get("responses", []))
    return tasks[done]["agent"] if done < len(tasks) else END


def _current_sub_query(state: AgentState) -> str:
    done = len(state.get("responses", []))
    tasks = state.get("tasks", [])
    return tasks[done]["sub_query"] if done < len(tasks) else state["query"]

# ─── Agent Nodes ──────────────────────────────────────────────────────────────

def product_agent_node(state: AgentState) -> dict:
    sub_query = _current_sub_query(state)
    agent = _get_react_agent(
        "product",
        tools=[product_rag_search, brave_web_search],
        system_prompt="""You are the Product Sales Expert for Lenovo.
Answer questions about Lenovo product specs, prices, models, and availability.

Tool usage:
- Use product_rag_search FIRST for any product question
- If the local results are empty or insufficient, use brave_web_search
- You may use both tools to give a complete, accurate answer
- Always base your answer on what the tools return"""
    )
    result = agent.invoke({"messages": [HumanMessage(content=sub_query)]})
    text = _extract_response(result)
    responses = list(state.get("responses", []))
    responses.append({"agent": "Product Agent", "text": text})
    return {
        "responses": responses,
        "debug_log": state.get("debug_log", "") + f"\n✅ Product Agent ← \"{sub_query}\""
    }


def tech_agent_node(state: AgentState) -> dict:
    sub_query = _current_sub_query(state)
    agent = _get_react_agent(
        "tech",
        tools=[tech_rag_search, brave_web_search],
        system_prompt="""You are the Technical Support Specialist for Lenovo.
Answer troubleshooting, repair, driver, and how-to questions.

Tool usage:
- Use tech_rag_search FIRST for any technical question
- If the local results are empty or insufficient, use brave_web_search for updated guides
- You may use both tools for a thorough answer
- Give safe, step-by-step instructions when relevant"""
    )
    result = agent.invoke({"messages": [HumanMessage(content=sub_query)]})
    text = _extract_response(result)
    responses = list(state.get("responses", []))
    responses.append({"agent": "Tech Agent", "text": text})
    return {
        "responses": responses,
        "debug_log": state.get("debug_log", "") + f"\n✅ Tech Agent ← \"{sub_query}\""
    }


def policy_agent_node(state: AgentState) -> dict:
    sub_query = _current_sub_query(state)
    agent = _get_react_agent(
        "policy",
        tools=[policy_rag_search, brave_web_search],
        system_prompt="""You are the Customer Support Specialist for Lenovo.
Answer questions about delivery, returns, refunds, warranty, and payment policies.

Tool usage:
- Use policy_rag_search FIRST for any policy question
- If the local results are empty or insufficient, use brave_web_search
- If policy information cannot be found, clearly say so and advise the user to contact Lenovo support"""
    )
    result = agent.invoke({"messages": [HumanMessage(content=sub_query)]})
    text = _extract_response(result)
    responses = list(state.get("responses", []))
    responses.append({"agent": "Policy Agent", "text": text})
    return {
        "responses": responses,
        "debug_log": state.get("debug_log", "") + f"\n✅ Policy Agent ← \"{sub_query}\""
    }


def finance_agent_node(state: AgentState) -> dict:
    sub_query = _current_sub_query(state)
    try:
        parse_res = _get_llm().invoke([
            SystemMessage(content=(
                "Extract from the query: amount (number), from_currency (3-letter ISO code), "
                "to_currency (3-letter ISO code). Reply ONLY as: amount,FROM,TO — e.g. 1499,USD,SGD. "
                "If not specified, default from=USD to=SGD."
            )),
            HumanMessage(content=sub_query)
        ])
        parts = parse_res.content.strip().split(",")
        amount = float(parts[0].strip())
        from_curr = parts[1].strip().upper()
        to_curr = parts[2].strip().upper()

        data = requests.get(
            f"https://api.exchangerate-api.com/v4/latest/{from_curr}", timeout=5
        ).json()
        rate = data["rates"][to_curr]
        converted = round(amount * rate, 2)
        text = f"{amount} {from_curr} = **{converted} {to_curr}** (Rate: {rate})"
    except Exception as e:
        text = f"Currency conversion failed: {e}"

    responses = list(state.get("responses", []))
    responses.append({"agent": "Finance Agent", "text": text})
    return {
        "responses": responses,
        "debug_log": state.get("debug_log", "") + f"\n✅ Finance Agent ← \"{sub_query}\""
    }


def search_agent_node(state: AgentState) -> dict:
    sub_query = _current_sub_query(state)
    text = brave_web_search.invoke(sub_query)
    responses = list(state.get("responses", []))
    responses.append({"agent": "Search Agent", "text": text})
    return {
        "responses": responses,
        "debug_log": state.get("debug_log", "") + f"\n✅ Search Agent ← \"{sub_query}\""
    }


def general_agent_node(state: AgentState) -> dict:
    sub_query = _current_sub_query(state)
    agent = _get_react_agent(
        "general",
        tools=[brave_web_search],
        system_prompt="""You are a friendly assistant for Lenovo.
Handle greetings, small talk, and general questions helpfully.

Tool usage:
- Use brave_web_search if the question needs current or factual information you are unsure about
- For simple greetings or small talk, answer directly without using tools
- If the question is Lenovo-related, suggest the user ask about products, tech support, or policies"""
    )
    result = agent.invoke({"messages": [HumanMessage(content=sub_query)]})
    text = _extract_response(result)
    responses = list(state.get("responses", []))
    responses.append({"agent": "General Agent", "text": text})
    return {
        "responses": responses,
        "debug_log": state.get("debug_log", "") + f"\n✅ General Agent ← \"{sub_query}\""
    }

# ─── Graph ────────────────────────────────────────────────────────────────────

def initialize_agent():
    global _graph
    if _graph:
        return _graph

    for folder in ("product", "tech", "policy"):
        _get_retriever(folder)

    wf = StateGraph(AgentState)
    wf.add_node("router", router_node)
    wf.add_node("product_agent", product_agent_node)
    wf.add_node("tech_agent", tech_agent_node)
    wf.add_node("policy_agent", policy_agent_node)
    wf.add_node("finance_agent", finance_agent_node)
    wf.add_node("search_agent", search_agent_node)
    wf.add_node("general_agent", general_agent_node)

    wf.set_entry_point("router")
    wf.add_conditional_edges("router", _route_next)
    for node in ("product_agent", "tech_agent", "policy_agent", "finance_agent", "search_agent", "general_agent"):
        wf.add_conditional_edges(node, _route_next)

    _graph = wf.compile()
    return _graph


async def get_agent_response(user_input: str) -> str:
    graph = initialize_agent()
    result = await graph.ainvoke({
        "query": user_input,
        "tasks": [],
        "responses": [],
        "debug_log": ""
    })

    responses: list = result.get("responses", [])
    debug_log: str = result.get("debug_log", "")

    if not responses:
        return "I could not find an answer to your question."

    parts = [f"**[{r['agent']}]**\n{r['text']}" for r in responses]
    body = "\n\n---\n\n".join(parts)

    return (
        f"{body}\n\n"
        f"<details><summary>🧠 Agent Thinking Process</summary>\n\n"
        f"```\n{debug_log}\n```\n</details>"
    )
