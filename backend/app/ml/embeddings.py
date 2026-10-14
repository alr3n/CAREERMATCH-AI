"""Semantic similarity backends.

Two interchangeable backends compute cosine similarity between a candidate
profile document and job documents:

* ``SentenceTransformerBackend`` — pretrained Sentence Transformers model
  (default ``all-MiniLM-L6-v2``). Used when the optional
  ``sentence-transformers`` package is installed and the model can be loaded.
  This is a *pretrained* model; CareerMatch AI does not fine-tune it.
* ``LSABackend`` — local TF-IDF + truncated SVD (latent semantic analysis)
  fitted on the current job corpus. Needs no downloads, so the core workflow
  works offline and without paid APIs.

Every match result records which backend produced its semantic score.
"""

from __future__ import annotations

import logging
import threading
from functools import lru_cache
from typing import Protocol

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class SemanticBackend(Protocol):
    name: str

    def similarities(self, query: str, documents: list[str]) -> np.ndarray: ...


class LSABackend:
    """TF-IDF (word 1–2 grams) reduced with truncated SVD.

    ``k = min(128, n_documents // 2)`` latent dimensions — a heuristic, not a
    tuned value. The corpus is the current job listings plus the profile.
    """

    def __init__(self, max_components: int = 128) -> None:
        self.max_components = max_components
        self.name = "lsa-tfidf-svd (local)"

    def similarities(self, query: str, documents: list[str]) -> np.ndarray:
        if not documents:
            return np.zeros(0)
        corpus = [query, *documents]
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, sublinear_tf=True, stop_words="english", max_features=50_000
        )
        try:
            matrix = vectorizer.fit_transform(corpus)
        except ValueError:  # empty vocabulary
            return np.zeros(len(documents))
        # Keep the latent space well below the corpus size: with k close to the
        # number of documents LSA degenerates into plain TF-IDF cosine.
        n_components = min(self.max_components, matrix.shape[0] // 2, matrix.shape[1] - 1)
        if n_components >= 2:
            svd = TruncatedSVD(n_components=n_components, random_state=42)
            reduced = svd.fit_transform(matrix)
            sims = cosine_similarity(reduced[:1], reduced[1:])[0]
        else:
            sims = cosine_similarity(matrix[:1], matrix[1:])[0]
        return np.clip(sims, 0.0, 1.0)


class SentenceTransformerBackend:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # optional dependency

        self._model = SentenceTransformer(model_name)
        self._lock = threading.Lock()
        self.name = f"sentence-transformers:{model_name.split('/')[-1]}"

    def similarities(self, query: str, documents: list[str]) -> np.ndarray:
        if not documents:
            return np.zeros(0)
        with self._lock:
            vectors = self._model.encode([query, *documents], normalize_embeddings=True, show_progress_bar=False)
        sims = vectors[1:] @ vectors[0]
        return np.clip(sims, 0.0, 1.0)


@lru_cache(maxsize=4)
def _sentence_backend(model_name: str) -> SentenceTransformerBackend | None:
    try:
        return SentenceTransformerBackend(model_name)
    except Exception as exc:  # ImportError, download failure, …
        logger.info("Sentence Transformers backend unavailable (%s); using LSA fallback", type(exc).__name__)
        return None


def get_backend(mode: str = "auto", model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> SemanticBackend:
    if mode in {"auto", "sentence-transformers"}:
        backend = _sentence_backend(model_name)
        if backend is not None:
            return backend
    return LSABackend()
