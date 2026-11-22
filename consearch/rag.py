"""Retrieval layer: chunking, embeddings and similarity search."""

from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass
class Chunk:
    text: str
    source_id: int
    position: int


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Split text into overlapping word windows."""
    words = text.split()
    if not words:
        return []
    step = max(1, size - overlap)
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
    return chunks


class TfidfEmbedder:
    """Sparse lexical embeddings. No model download, works offline."""

    name = "tfidf"

    def __init__(self):
        self.vec: TfidfVectorizer | None = None

    def fit_transform(self, texts: list[str]):
        try:
            self.vec = TfidfVectorizer(stop_words="english", sublinear_tf=True)
            return self.vec.fit_transform(texts)
        except ValueError:  # e.g. every token was a stop word
            self.vec = TfidfVectorizer(sublinear_tf=True)
            return self.vec.fit_transform(texts)

    def transform(self, texts: list[str]):
        return self.vec.transform(texts)


class SentenceTransformerEmbedder:
    """Dense semantic embeddings. Requires `pip install sentence-transformers`."""

    name = "sentence-transformers"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def fit_transform(self, texts: list[str]):
        return self.transform(texts)

    def transform(self, texts: list[str]):
        return self.model.encode(texts, normalize_embeddings=True)


def make_embedder(name: str):
    if name == "tfidf":
        return TfidfEmbedder()
    if name == "sentence-transformers":
        return SentenceTransformerEmbedder()
    raise ValueError(f"Unknown embedder: {name}")


def _cosine_scores(query_vec, matrix) -> np.ndarray:
    # Both embedders return L2-normalised vectors, so the dot product is cosine similarity.
    scores = query_vec @ matrix.T
    if hasattr(scores, "toarray"):
        scores = scores.toarray()
    return np.asarray(scores).ravel()


class RAGIndex:
    """In-memory vector index over chunks from all sources in a conversation."""

    def __init__(self, embedder, chunk_words: int = 180, chunk_overlap: int = 30):
        self.embedder = embedder
        self.chunk_words = chunk_words
        self.chunk_overlap = chunk_overlap
        self.chunks: list[Chunk] = []
        self._matrix = None

    def add_text(self, text: str, source_id: int) -> int:
        new = chunk_text(text, self.chunk_words, self.chunk_overlap)
        for pos, piece in enumerate(new):
            self.chunks.append(Chunk(piece, source_id, pos))
        if new:
            self._matrix = None  # invalidate; refit lazily on next search
        return len(new)

    def _ensure_matrix(self):
        if self._matrix is None and self.chunks:
            self._matrix = self.embedder.fit_transform([c.text for c in self.chunks])

    def search(self, query: str, k: int = 5, min_score: float = 0.02) -> list[tuple[Chunk, float]]:
        if not self.chunks:
            return []
        self._ensure_matrix()
        scores = _cosine_scores(self.embedder.transform([query]), self._matrix)
        order = np.argsort(-scores)[:k]
        return [(self.chunks[i], float(scores[i])) for i in order if scores[i] >= min_score]
