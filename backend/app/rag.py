"""
LangGraph RAG agent.

Graph flow:  retrieve → generate

Clients are initialised lazily on first use so the module can be imported
safely even if environment variables are not yet loaded.
"""

import os
import logging
from typing import TypedDict, Annotated
import operator
from functools import lru_cache

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from .gemini_embeddings import GeminiEmbeddings
from langgraph.graph import StateGraph, END
from google.api_core.exceptions import ResourceExhausted
from supabase import create_client
from typing import Any, Dict, List, Optional

from .tutorials import tutorial_image_url


load_dotenv()

# ─── Lazy singletons ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _embeddings():
    return GeminiEmbeddings(
        model="gemini-embedding-001",
        api_key=os.environ["GOOGLE_AI_API_KEY"],
    )


@lru_cache(maxsize=1)
def _supabase():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


@lru_cache(maxsize=1)
def _llm():
    return ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        temperature=0,
        google_api_key=os.environ["GOOGLE_AI_API_KEY"],
    )


# ─── System prompt ────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    company = os.environ.get("COMPANY_NAME", "AdminIE")
    support_email = os.environ.get("ESCALATION_EMAIL_TO", "success@adminie.com")
    return f"""You are {company}, the intelligent AI support assistant for {company}.

You help users understand {company} software modules.

Rules:
- Answer using the provided context as your primary source. You may summarise or infer from the context, but do not invent facts not supported by it.
- The context is assembled from multiple sources and may mix real instructions with bare question lists (e.g. a table of contents) that repeat the same heading with no answer beneath it. Ignore those bare headings and answer from whichever part of the context actually has the instructions. Only fall back to "I don't have enough information" if NONE of the context contains real instructions for the question — never invent steps to fill a gap.
- Do NOT include source citations, page numbers, or references like "Sources: [HR, page 8]" in your response. Just answer naturally.
- If the context truly has no relevant information — including the bare-heading case above — say: "I don't have enough information on that. I can notify our support team and have them follow up with you by email — just let me know if you'd like me to do that. You can also reach them directly at {support_email}."
- Keep answers clear, concise, and professional.
- If the user seems frustrated, acknowledge it empathetically before answering.

Context:
{{context}}
"""

_SYSTEM = _build_system_prompt()

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("placeholder", "{history}"),
    ("human", "{question}"),
])

# ─── LangGraph state ──────────────────────────────────────────────────────────

class AgentState(TypedDict):
    question:  str
    history:   Annotated[list[BaseMessage], operator.add]
    context:   str
    answer:    str
    tutorial:  Optional[Dict[str, Any]]


# ─── Graph nodes ──────────────────────────────────────────────────────────────

def retrieve(state: AgentState) -> dict:
    try:
        vec = _embeddings().embed_query(state["question"])
        threshold = float(os.environ.get("RAG_MATCH_THRESHOLD", "0.1"))
        rows = _supabase().rpc("match_documents", {
            "query_embedding": vec,
            "match_count": 8,
            "match_threshold": threshold,
        }).execute().data or []
        logger.info("RAG retrieved %d docs (threshold=%.2f) for: %s",
                    len(rows), threshold, state["question"][:60])
    except Exception as e:
        logger.warning("Retrieval failed: %s — returning empty context.", e)
        return {"context": "", "tutorial": None}

    from langchain_core.documents import Document
    docs = [Document(page_content=r["content"], metadata=r.get("metadata", {})) for r in rows]
    context_parts = [doc.page_content for doc in docs]

    # Only check the single best match: scanning further down into lower-ranked
    # chunks surfaces irrelevant pages (e.g. a table-of-contents page) once the
    # top match is genuinely the best answer but happens to have no image.
    #
    # Google Doc Q&A chunks carry their own "image_url" (the real screenshot
    # that followed that question in the doc — see gdoc_ingest.py). PDF chunks
    # have no "image_url" but carry "page", which maps to a rendered PDF page.
    tutorial = None
    if docs:
        metadata = docs[0].metadata
        if "image_url" in metadata:
            tutorial = {
                "module": metadata.get("module"),
                "image_url": metadata["image_url"],
            }
        elif "page" in metadata:
            tutorial = {
                "module": metadata["module"],
                "page": metadata["page"],
                "image_url": tutorial_image_url(metadata["source"], metadata["page"]),
            }

    return {"context": "\n\n---\n\n".join(context_parts), "tutorial": tutorial}


def generate(state: AgentState) -> dict:
    try:
        answer = (_PROMPT | _llm()).invoke({
            "context": state["context"],
            "history": state["history"],
            "question": state["question"],
        }).content
    except ResourceExhausted:
        logger.warning("LLM rate limit hit — returning friendly message.")
        answer = (
            "I'm experiencing high demand right now and couldn't generate a response. "
            "Please try again in a moment."
        )
    return {"answer": answer}


# ─── Build graph ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _graph():
    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()


# ─── Public interface ─────────────────────────────────────────────────────────

def run_rag(question: str, history: list[BaseMessage] | None = None) -> dict:
    """Run the RAG graph and return {"answer": str, "tutorial": dict | None}."""
    result = _graph().invoke({
        "question": question,
        "history":  history or [],
        "context":  "",
        "answer":   "",
        "tutorial": None,
    })
    return {"answer": result["answer"], "tutorial": result["tutorial"]}
