# data/knowledge.py — Knowledge & Compliance search via Azure AI Search (Vector DB)

import os
import re
import logging
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from sentence_transformers import SentenceTransformer
import torch
import torch.nn.functional as F

logger = logging.getLogger("call-intelligence")

# ─── Configuration ─── #
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
INDEX_NAME = "knowledge-base-index"

EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"
TARGET_DIMENSION = 1536

# ─── Module-level singletons (initialized lazily) ─── #
_search_client: SearchClient | None = None
_embedding_model: SentenceTransformer | None = None


def _get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def _get_embedding_model() -> SentenceTransformer:
    """Lazy-load the embedding model once at first use."""
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(f"Embedding model loaded on {_get_device()}")
    return _embedding_model


def _get_search_client() -> SearchClient:
    """Lazy-load the Azure Search client once at first use."""
    global _search_client
    if _search_client is None:
        if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
            raise RuntimeError(
                "AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set in environment variables."
            )
        credential = AzureKeyCredential(AZURE_SEARCH_KEY)
        _search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=INDEX_NAME,
            credential=credential,
        )
        logger.info(f"Azure Search client initialized for index '{INDEX_NAME}'")
    return _search_client


def warmup():
    """Pre-load embedding model and search client at server startup.
    Call this from the FastAPI lifespan handler to avoid first-request latency."""
    logger.info("🔥 Warming up knowledge module...")
    _get_embedding_model()
    _get_search_client()
    logger.info("✅ Knowledge module ready (model + search client loaded)")


def _embed_query(text: str) -> list[float]:
    """Embed a single query string using the local BGE model, padded to TARGET_DIMENSION."""
    model = _get_embedding_model()
    embedding = model.encode([text], convert_to_tensor=True, device=_get_device())

    # Pad to 1536d to match indexed documents
    current_dim = embedding.shape[1]
    if current_dim < TARGET_DIMENSION:
        embedding = F.pad(embedding, (0, TARGET_DIMENSION - current_dim), "constant", 0)
    elif current_dim > TARGET_DIMENSION:
        embedding = embedding[:, :TARGET_DIMENSION]

    # Re-normalize for cosine similarity
    embedding = F.normalize(embedding, p=2, dim=1)

    return embedding[0].cpu().numpy().tolist()


def search_knowledge(
    query: str, category: str | None = None, top_k: int = 3
) -> list[dict]:
    """
    Hybrid search over Azure AI Search — combines vector similarity with full-text BM25.
    Optionally filters by category (e.g. 'claims', 'compliance', 'policy').
    Returns top_k results as dicts with: title, content, category, section_heading, document_id.
    """
    client = _get_search_client()
    query_vector = _embed_query(query)

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="content_vector",
    )

    # Build OData filter for category if provided
    filter_expr = None
    if category:
        # Map claim_type values to index category values
        category_map = {
            "car_insurance": "claims",
            "life_insurance": "claims",
            "general": "general",
        }
        mapped = category_map.get(category, category)
        # Include 'general' docs alongside category-specific ones
        filter_expr = f"category eq '{mapped}' or category eq 'general'"

    results = client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=filter_expr,
        top=top_k,
        select=["title", "content", "category", "section_heading", "document_id"],
    )

    docs = []
    for result in results:
        docs.append({
            "title": result.get("title", ""),
            "content": result.get("content", ""),
            "category": result.get("category", ""),
            "section_heading": result.get("section_heading", ""),
            "document_id": result.get("document_id", ""),
            "score": result.get("@search.score", 0),
        })

    logger.info(f"Knowledge search for '{query[:50]}...' returned {len(docs)} results")
    return docs


def get_compliance_alerts(intent: str, transcript: str) -> list[dict]:
    """
    Search for compliance rules and alerts relevant to the current call.
    Queries the Azure index filtered to the 'compliance' category.
    Returns matched compliance documents as alerts.
    """
    client = _get_search_client()

    # Build a targeted compliance query from intent + key transcript phrases
    search_query = f"{intent} compliance guidelines regulations"
    query_vector = _embed_query(search_query)

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=5,
        fields="content_vector",
    )

    results = client.search(
        search_text=search_query,
        vector_queries=[vector_query],
        filter="category eq 'compliance'",
        top=5,
        select=["title", "content", "section_heading", "document_id"],
    )

    alerts = []
    for result in results:
        alerts.append({
            "title": result.get("title", ""),
            "content": result.get("content", ""),
            "section_heading": result.get("section_heading", ""),
            "severity": "HIGH",  # Default severity; can be refined with metadata later
            "document_id": result.get("document_id", ""),
        })

    logger.info(f"Compliance check for '{intent}' returned {len(alerts)} alerts")
    return alerts
