"""RAG over the question bank: chunking, embeddings (MiniLM) and ChromaDB retrieval."""
from __future__ import annotations

import re
from pathlib import Path

from core import config

EMBED_MODEL = "all-MiniLM-L6-v2"
COLLECTION = "question_bank"
SKILL_KEYWORDS = [
    "python", "sql", "machine learning", "statistics", "pandas", "data analysis", "tableau", "power bi",
    "excel", "system design", "api", "docker", "aws", "cloud", "leadership", "communication", "teamwork",
    "deep learning", "etl", "dashboard", "a/b testing", "scalability", "database", "behavioral",
]


def chunk_text(text: str, max_chars: int = 700) -> list[str]:
    """Split text into chunks of whole paragraphs, each up to ``max_chars`` characters."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


def skills_query(job_description: str) -> str:
    """Build a retrieval query from the skills mentioned in a job description."""
    lowered = job_description.lower()
    found = [k for k in SKILL_KEYWORDS if k in lowered]
    return " ".join(found) if found else job_description[:600]


def load_question_bank(directory: Path | None = None) -> list[tuple[str, str]]:
    """Return (source_file, chunk) pairs from every .txt/.md file in the question bank."""
    directory = directory or config.QUESTION_BANK_DIR
    items: list[tuple[str, str]] = []
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() in {".txt", ".md"}:
            for chunk in chunk_text(path.read_text(encoding="utf-8")):
                items.append((path.stem, chunk))
    return items


@config.cached_resource
def _embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


@config.cached_resource
def _collection():
    import chromadb

    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def _embed(texts: list[str]) -> list[list[float]]:
    return _embedder().encode(texts, normalize_embeddings=True).tolist()


def build_index(force: bool = False) -> int:
    """Index the question bank. Rebuilds only if the collection is empty (or ``force``). Returns chunk count."""
    col = _collection()
    if force and col.count():
        existing = col.get()
        if existing["ids"]:
            col.delete(ids=existing["ids"])
    if col.count() > 0:
        return col.count()
    items = load_question_bank()
    if not items:
        return 0
    docs = [c for _, c in items]
    col.add(
        ids=[f"{src}-{i}" for i, (src, _) in enumerate(items)],
        documents=docs,
        embeddings=_embed(docs),
        metadatas=[{"source": src} for src, _ in items],
    )
    return col.count()


def retrieve(query: str, k: int = 3) -> list[str]:
    """Return the top-k most relevant question-bank chunks for ``query`` (empty list on any failure)."""
    try:
        build_index()
        col = _collection()
        if col.count() == 0 or not query.strip():
            return []
        res = col.query(query_embeddings=_embed([query]), n_results=min(k, col.count()))
        return list(res["documents"][0])
    except Exception:
        return []


def format_context(chunks: list[str]) -> str:
    """Join retrieved chunks for inclusion in a prompt."""
    return "\n---\n".join(chunks)
