import os
import requests
from typing import List, TypedDict

from langchain_groq import ChatGroq
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langgraph.graph import StateGraph, END

# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    query: str
    agents_to_call: List[str]
    responses: List[dict]   # [{"agent": str, "text": str}]
    debug_log: str

# ─── Singletons ───────────────────────────────────────────────────────────────

_llm = None
_embeddings = None
_retrievers: dict = {}
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
        # ONNX-based local embeddings — no PyTorch, no API calls, ~80MB total
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

# ─── Router Node ──────────────────────────────────────────────────────────────

def router_node(state: AgentState) -> dict:
    router_prompt = """You are a Router for a Lenovo AI Assistant.

Classify the user query into ONE OR MORE of these agents (comma-separated if multiple are needed):
- product_agent  : product specs, prices, models, ThinkPad, IdeaPad, Legion, Yoga
- tech_agent     : troubleshooting, drivers, repair, how-to, technical support
- policy_agent   : delivery, shipping, returns, refunds, warranty policy, payment
- finance_agent  : currency conversion, price in SGD / USD / EUR or any other currency
- search_agent   : current news, latest releases, real-time info not in local data

Output ONLY the agent name(s) separated by commas. Example: product_agent,policy_agent
If unsure, output: product_agent"""

    res = _get_llm().invoke([
        SystemMessage(content=router_prompt),
        HumanMessage(content=state["query"])
    ])
    raw = res.content.strip().lower()

    valid = {"product_agent", "tech_agent", "policy_agent", "finance_agent", "search_agent"}
    agents = [a.strip() for a in raw.split(",") if a.strip() in valid]
    if not agents:
        agents = ["product_agent"]

    return {
        "agents_to_call": agents,
        "responses": [],
        "debug_log": f"🚦 Router → {', '.join(agents)}"
    }

# ─── Routing logic (shared by router + every agent node) ─────────────────────

def _route_next(state: AgentState) -> str:
    agents = state.get("agents_to_call", [])
    done = len(state.get("responses", []))
    return agents[done] if done < len(agents) else END

# ─── RAG helper ───────────────────────────────────────────────────────────────

def _rag_node(state: AgentState, agent_name: str, folder: str, persona: str) -> dict:
    query = state["query"]
    retriever = _get_retriever(folder)

    context = ""
    doc_count = 0
    if retriever:
        docs = retriever.invoke(query)
        context = "\n\n".join(d.page_content for d in docs)
        doc_count = len(docs)

    system_prompt = f"""You are the {persona} for Lenovo.
Answer using ONLY the context below. If the answer is not in the context, say so clearly.

Context:
{context}"""

    res = _get_llm().invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=query)
    ])

    responses = list(state.get("responses", []))
    responses.append({"agent": agent_name, "text": res.content})
    return {
        "responses": responses,
        "debug_log": state.get("debug_log", "") + f"\n✅ {agent_name}: used {doc_count} docs from '{folder}'"
    }

# ─── Agent Nodes ──────────────────────────────────────────────────────────────

def product_agent_node(state: AgentState) -> dict:
    return _rag_node(state, "Product Agent", "product", "Product Sales Expert")


def tech_agent_node(state: AgentState) -> dict:
    return _rag_node(state, "Tech Agent", "tech", "Technical Support Specialist")


def policy_agent_node(state: AgentState) -> dict:
    return _rag_node(state, "Policy Agent", "policy", "Customer Support Specialist")


def finance_agent_node(state: AgentState) -> dict:
    query = state["query"]
    try:
        parse_res = _get_llm().invoke([
            SystemMessage(content=(
                "Extract from the query: amount (number), from_currency (3-letter ISO code), "
                "to_currency (3-letter ISO code). Reply ONLY as: amount,FROM,TO — e.g. 1499,USD,SGD. "
                "If not specified, default from=USD to=SGD."
            )),
            HumanMessage(content=query)
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
        "debug_log": state.get("debug_log", "") + "\n✅ Finance Agent: currency converted"
    }


def search_agent_node(state: AgentState) -> dict:
    query = state["query"]
    api_key = os.getenv("BRAVE_API_KEY")

    if not api_key:
        text = "Web search is unavailable (Brave API key not configured)."
    else:
        try:
            res = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"Accept": "application/json", "X-Subscription-Token": api_key},
                params={"q": query, "count": 3},
                timeout=10
            )
            results = res.json().get("web", {}).get("results", [])
            text = "\n".join(
                f"- **{r['title']}**: {r.get('description', '')} ({r['url']})"
                for r in results
            ) or "No results found."
        except Exception as e:
            text = f"Search error: {e}"

    responses = list(state.get("responses", []))
    responses.append({"agent": "Search Agent", "text": text})
    return {
        "responses": responses,
        "debug_log": state.get("debug_log", "") + "\n✅ Search Agent: web search done"
    }

# ─── Graph ────────────────────────────────────────────────────────────────────

def initialize_agent():
    global _graph
    if _graph:
        return _graph

    # Pre-load retrievers at startup so first request is not slow
    for folder in ("product", "tech", "policy"):
        _get_retriever(folder)

    wf = StateGraph(AgentState)
    wf.add_node("router", router_node)
    wf.add_node("product_agent", product_agent_node)
    wf.add_node("tech_agent", tech_agent_node)
    wf.add_node("policy_agent", policy_agent_node)
    wf.add_node("finance_agent", finance_agent_node)
    wf.add_node("search_agent", search_agent_node)

    wf.set_entry_point("router")

    # After router → pick first agent
    wf.add_conditional_edges("router", _route_next)

    # After each agent → pick next agent or END
    for node in ("product_agent", "tech_agent", "policy_agent", "finance_agent", "search_agent"):
        wf.add_conditional_edges(node, _route_next)

    _graph = wf.compile()
    return _graph


async def get_agent_response(user_input: str) -> str:
    graph = initialize_agent()
    result = await graph.ainvoke({
        "query": user_input,
        "agents_to_call": [],
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
