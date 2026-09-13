"""RAG retrieval — stage 4 of 5 (Retrieve).

Loads the persisted Chroma store built by rag/ingest.py and, for a given
question, returns the top-k most relevant chunks by embedding similarity.
Read-only at runtime: this module never re-embeds or rebuilds the index.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cpf_life import sqlite_shim  # noqa: F401  (must precede any chromadb import)

import streamlit as st
from embeddings import OpenAIEmbeddingsCompat
from langchain_chroma import Chroma

PERSIST_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "cpf_life_research"


@st.cache_resource(show_spinner=False)
def _get_vectorstore(api_key: str) -> "Chroma":
    embeddings = OpenAIEmbeddingsCompat(api_key=api_key)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(PERSIST_DIR),
    )


def index_exists() -> bool:
    return PERSIST_DIR.exists() and any(PERSIST_DIR.iterdir())


def retrieve_chunks(query: str, api_key: str, k: int = 4) -> list[dict]:
    """Returns up to k relevant chunks as
    {"text": str, "source": str, "chunk_index": int}, or [] if no index
    has been built yet (see rag/ingest.py) or retrieval fails."""
    if not index_exists():
        return []
    try:
        vectorstore = _get_vectorstore(api_key)
        results = vectorstore.similarity_search(query, k=k)
    except Exception:
        return []
    return [
        {
            "text": r.page_content,
            "source": r.metadata.get("source", "CPF LIFE Deep Research Briefing"),
            "chunk_index": r.metadata.get("chunk_index"),
        }
        for r in results
    ]
