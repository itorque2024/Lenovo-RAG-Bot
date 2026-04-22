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

class Task(TypedDict):
    agent: str        # which agent handles this
    sub_query: str    # only the portion of the question that agent should answer

class AgentState(TypedDict):
    query: str          # original full user query (kept for reference)
    tasks: List[Task]   # decomposed sub-queries assigned to specific agents
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

Your job is to DECOMPOSE the user query into one or more sub-questions and assign each to the correct agent.

Available agents:
- product_agent  : product specs, prices, models, ThinkPad, IdeaPad, Legion, Yoga
- tech_agent     : troubleshooting, drivers, repair, how-to, technical support
- policy_agent   : delivery, shipping, returns, refunds, warranty policy, payment
- finance_agent  : currency conversion, price in SGD / USD / EUR or any other currency
- search_agent   : current news, latest releases, real-time info not in local data

Rules:
- Split multi-part questions so each agent only receives the portion it should answer
- One line per task, format exactly as: agent_name|sub-question
- Do not add explanation, numbering, or extra text

Example input: "What is the price of the X1 Carbon and what is the return policy?"
Example output:
product_agent|What is the price of the X1 Carbon?
policy_agent|What is the return policy?

Example input: "How do I fix my ThinkPad screen and convert 1500 USD to SGD?"
Example output:
tech_agent|How do I fix my ThinkPad screen?
finance_agent|Convert 1500 USD to SGD"""

    res = _get_llm().invoke([
        SystemMessage(content=router_prompt),
        HumanMessage(content=state["query"])
    ])

    valid = {"product_agent", "tech_agent", "policy_agent", "finance_agent", "search_agent"}
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

    # Fallback if parsing fails
    if not tasks:
        tasks = [{"agent": "product_agent", "sub_query": state["query"]}]

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

# ─── RAG helper ───────────────────────────────────────────────────────────────

def _current_sub_query(state: AgentState) -> str:
    """Returns the sub-query meant for the current agent (not the full query)."""
    done = len(state.get("responses", []))
    tasks = state.get("tasks", [])
    if done < len(tasks):
        return tasks[done]["sub_query"]
    return state["query"]


def _rag_node(state: AgentState, agent_name: str, folder: str, persona: str) -> dict:
    sub_query = _current_sub_query(state)
    retriever = _get_retriever(folder)

    context = ""
    doc_count = 0
    if retriever:
        docs = retriever.invoke(sub_query)
        context = "\n\n".join(d.page_content for d in docs)
        doc_count = len(docs)

    system_prompt = f"""You are the {persona} for Lenovo.
Answer using ONLY the context below. If the answer is not in the context, say so clearly.

Context:
{context}"""

    res = _get_llm().invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=sub_query)
    ])

    responses = list(state.get("responses", []))
    responses.append({"agent": agent_name, "text": res.content})
    return {
        "responses": responses,
        "debug_log": state.get("debug_log", "") + f"\n✅ {agent_name} ← \"{sub_query}\" ({doc_count} docs)"
    }

# ─── Agent Nodes ──────────────────────────────────────────────────────────────

def product_agent_node(state: AgentState) -> dict:
    return _rag_node(state, "Product Agent", "product", "Product Sales Expert")


def tech_agent_node(state: AgentState) -> dict:
    return _rag_node(state, "Tech Agent", "tech", "Technical Support Specialist")


def policy_agent_node(state: AgentState) -> dict:
    return _rag_node(state, "Policy Agent", "policy", "Customer Support Specialist")


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
    api_key = os.getenv("BRAVE_API_KEY")

    if not api_key:
        text = "Web search is unavailable (Brave API key not configured)."
    else:
        try:
            res = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"Accept": "application/json", "X-Subscription-Token": api_key},
                params={"q": sub_query, "count": 3},
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
        "debug_log": state.get("debug_log", "") + f"\n✅ Search Agent ← \"{sub_query}\""
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

    wf.set_entry_point("router")
    wf.add_conditional_edges("router", _route_next)
    for node in ("product_agent", "tech_agent", "policy_agent", "finance_agent", "search_agent"):
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
