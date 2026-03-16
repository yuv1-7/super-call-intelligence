# data/knowledge.py — Knowledge & Compliance search via Azure AI Search
# All knowledge content lives in `docs for embedding/` and is indexed in Azure AI Search.
# This module handles vector + full-text hybrid search against that index.

import os
import logging
from typing import Optional

logger = logging.getLogger("call-intelligence")

# ─── Configuration ─── #
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
INDEX_NAME = "knowledge-base-index"

EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"
TARGET_DIMENSION = 1536

# ─── Module-level singletons ─── #
_search_client = None
_embedding_model = None


def _azure_available() -> bool:
    """Check if Azure Search credentials are configured."""
    return bool(AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY)


# ══════════════════════════════════════════════════════
# AZURE AI SEARCH — primary (and only) search backend
# ══════════════════════════════════════════════════════

def _get_device() -> str:
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(f"Embedding model loaded on {_get_device()}")
    return _embedding_model


def _get_search_client():
    global _search_client
    if _search_client is None:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        if not _azure_available():
            raise RuntimeError(
                "AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set in environment variables. "
                "All knowledge content is served via Azure AI Search — see 'docs for embedding/' for source documents."
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
    """Pre-load resources at server startup."""
    logger.info("🔥 Warming up knowledge module...")
    if _azure_available():
        try:
            _get_embedding_model()
            _get_search_client()
            logger.info("✅ Knowledge module ready (Azure Search + embedding model)")
        except Exception as e:
            logger.warning(f"⚠️ Azure Search warmup failed: {e}")
    else:
        logger.warning(
            "⚠️ Azure Search not configured (AZURE_SEARCH_ENDPOINT / AZURE_SEARCH_KEY not set). "
            "Knowledge and compliance search will not be available."
        )
    logger.info("✅ Knowledge module warmup complete")


def _embed_query(text: str) -> list[float]:
    """Embed a single query string using the local BGE model, padded to TARGET_DIMENSION."""
    import torch
    import torch.nn.functional as F

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


# ══════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════

def search_knowledge(
    query: str, category: str | None = None, top_k: int = 3
) -> list[dict]:
    """
    Hybrid search — combines vector similarity with full-text BM25 on Azure AI Search.
    All knowledge documents are indexed from the `docs for embedding/` directory.
    """
    if not _azure_available():
        logger.warning("Azure Search not configured — returning empty results")
        return []

    try:
        from azure.search.documents.models import VectorizedQuery

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
            category_map = {
                "car_insurance": "claims",
                "life_insurance": "claims",
                "medical_insurance": "claims",
                "general": "general",
            }
            mapped = category_map.get(category, category)
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

    except Exception as e:
        logger.error(f"Azure Search failed: {e}")
        return []


def get_compliance_alerts(intent: str, transcript: str) -> list[dict]:
    """
    Search for compliance rules relevant to the current call.
    Uses Azure AI Search filtered to 'compliance' category.
    """
    if not _azure_available():
        logger.warning("Azure Search not configured — returning empty compliance alerts")
        return []

    try:
        from azure.search.documents.models import VectorizedQuery

        client = _get_search_client()
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
                "severity": "HIGH",
                "document_id": result.get("document_id", ""),
            })

        logger.info(f"Compliance check for '{intent}' returned {len(alerts)} alerts")
        return alerts

    except Exception as e:
        logger.error(f"Azure compliance search failed: {e}")
        return []
