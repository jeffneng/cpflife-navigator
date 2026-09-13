"""RAG ingestion pipeline — stages 1-3 of 5 (Load -> Split -> Store).

Run this once locally (needs OPENAI_API_KEY) whenever the source research
report changes, to rebuild the persisted Chroma vector store:

    OPENAI_API_KEY=sk-... python3 rag/ingest.py

Production (Streamlit Cloud) never runs this — it only reads the committed
`chroma_db/` directory (see rag/retrieval.py), so there's no runtime
embedding cost or API-key dependency for this step there.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cpf_life import sqlite_shim  # noqa: F401  (must precede any chromadb import)

from embeddings import OpenAIEmbeddingsCompat
from langchain_chroma import Chroma
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

SOURCE_DOC = Path(__file__).parent / "source_documents" / "CPF_LIFE_Deep_Research_Briefing.docx"
PERSIST_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "cpf_life_research"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def ingest():
    # ---- 1. Load ----
    print(f"[1/3] Loading {SOURCE_DOC.name}...")
    documents = Docx2txtLoader(str(SOURCE_DOC)).load()
    total_chars = sum(len(d.page_content) for d in documents)
    print(f"      loaded {len(documents)} document(s), {total_chars:,} characters")

    # ---- 2. Split / chunk ----
    print(f"[2/3] Splitting (chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    for i, chunk in enumerate(chunks):
        chunk.metadata["source"] = "CPF LIFE Deep Research Briefing (Sep 2026)"
        chunk.metadata["chunk_index"] = i
    print(f"      produced {len(chunks)} chunks")

    # ---- 3. Store (embed + persist) ----
    if PERSIST_DIR.exists():
        import shutil
        shutil.rmtree(PERSIST_DIR)
    print(f"[3/3] Embedding and persisting to {PERSIST_DIR}...")
    api_key = os.environ["OPENAI_API_KEY"]
    embeddings = OpenAIEmbeddingsCompat(api_key=api_key)
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(PERSIST_DIR),
    )
    print("Done — commit rag/chroma_db/ so production can read it without re-embedding.")


if __name__ == "__main__":
    ingest()
