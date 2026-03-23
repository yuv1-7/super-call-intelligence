# data/knowledge.py — Knowledge & Compliance search via Azure AI Search
# All knowledge content lives in `docs for embedding/` and is indexed in Azure AI Search.
# This module handles vector + full-text hybrid search against that index,
# with OData filtering by insurance_type to prevent cross-domain contamination.

import os
import logging
import functools
from typing import Optional

logger = logging.getLogger("call-intelligence")

# ─── Configuration ─── #
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
INDEX_NAME = "knowledge-base-index"

EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"
TARGET_DIMENSION = 1536

# Minimum hybrid search score to consider a result relevant.
# Results below this are discarded to prevent low-quality matches.
MIN_SEARCH_SCORE = 0.01

# ─── Module-level singletons ─── #
_search_client = None
_embedding_model = None
_embedding_cache: dict[str, list[float]] = {}  # In-memory cache for query embeddings

# ─── Insurance Type Filter Mapping ─── #
# Maps the claim_type from intent classification to the insurance_type values
# stored in the Azure index + any cross-cutting types that should always be included.
CLAIM_TYPE_TO_FILTER: dict[str, list[str]] = {
    "car_insurance": ["auto", "compliance", "general"],
    "car_accident": ["auto", "compliance", "general"],
    "life_insurance": ["life", "compliance", "general"],
    "medical_insurance": ["medical", "compliance", "general"],
    "health_insurance": ["medical", "compliance", "general"],
}


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
    """Embed a single query string using the local BGE model, padded to TARGET_DIMENSION.
    Results are cached in-memory to avoid re-computing embeddings for repeated queries."""
    if text in _embedding_cache:
        return _embedding_cache[text]

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

    result = embedding[0].cpu().numpy().tolist()

    # Cache the result (cap cache size to prevent unbounded memory growth)
    if len(_embedding_cache) < 64:
        _embedding_cache[text] = result

    return result


def _build_insurance_type_filter(claim_type: str | None) -> str | None:
    """Build an OData filter expression for insurance_type.

    Uses Azure AI Search's built-in OData $filter to restrict results
    to only the relevant insurance domain + cross-cutting types.
    Returns None if no filtering should be applied.
    """
    if not claim_type:
        return None

    # Look up which insurance_types are relevant for this claim_type
    allowed_types = CLAIM_TYPE_TO_FILTER.get(claim_type)
    if not allowed_types:
        # Fallback: try to infer from the claim_type string
        if "car" in claim_type or "auto" in claim_type or "vehicle" in claim_type:
            allowed_types = ["auto", "compliance", "general"]
        elif "life" in claim_type or "death" in claim_type:
            allowed_types = ["life", "compliance", "general"]
        elif "medical" in claim_type or "health" in claim_type or "hospital" in claim_type:
            allowed_types = ["medical", "compliance", "general"]
        else:
            return None  # Unknown claim type — don't filter

    # Build OData filter: insurance_type eq 'auto' or insurance_type eq 'compliance' or ...
    clauses = [f"insurance_type eq '{t}'" for t in allowed_types]
    return " or ".join(clauses)


def _deduplicate_by_document(docs: list[dict], max_per_doc: int = 2) -> list[dict]:
    """Keep at most `max_per_doc` chunks per source document.

    This prevents a single document from dominating all result slots,
    ensuring broader coverage across the knowledge base.
    Results are assumed to be pre-sorted by score (highest first).
    """
    doc_counts: dict[str, int] = {}
    deduped = []
    for doc in docs:
        source = doc.get("source_document", "unknown")
        count = doc_counts.get(source, 0)
        if count < max_per_doc:
            deduped.append(doc)
            doc_counts[source] = count + 1
    return deduped


# ══════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════

def search_knowledge(
    query: str,
    claim_type: str | None = None,
    top_k: int = 5,
    category: str | None = None,
) -> list[dict]:
    """
    Hybrid search — combines vector similarity with full-text BM25 on Azure AI Search.
    Filters by insurance_type using Azure's built-in OData $filter to prevent
    cross-domain contamination (e.g., car accident query returning life insurance docs).

    Args:
        query: The search query text.
        claim_type: The detected claim type (e.g., 'car_insurance', 'life_insurance').
                    Used to build insurance_type OData filter.
        top_k: Maximum number of results to return.
        category: Legacy category filter (still supported for backward compat).
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
            k_nearest_neighbors=top_k * 2,  # Fetch more candidates for post-filtering
            fields="content_vector",
        )

        # Build OData filter — insurance_type is the primary filter
        filter_expr = _build_insurance_type_filter(claim_type)

        # Fallback to legacy category filter if no insurance_type filter was built
        if not filter_expr and category:
            category_map = {
                "car_insurance": "claims",
                "life_insurance": "claims",
                "medical_insurance": "claims",
                "general": "general",
            }
            mapped = category_map.get(category, category)
            filter_expr = f"category eq '{mapped}' or category eq 'general'"

        logger.info(f"🔍 KB search: query='{query[:60]}', claim_type={claim_type}, filter={filter_expr}")

        results = client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=filter_expr,
            top=top_k * 2,  # Fetch extra for dedup + score filtering
            select=[
                "title", "content", "category", "section_heading",
                "document_id", "insurance_type", "source_document",
            ],
        )

        docs = []
        for result in results:
            score = result.get("@search.score", 0)

            # Score threshold — skip truly irrelevant low-scoring matches
            if score < MIN_SEARCH_SCORE:
                continue

            docs.append({
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "category": result.get("category", ""),
                "section_heading": result.get("section_heading", ""),
                "document_id": result.get("document_id", ""),
                "insurance_type": result.get("insurance_type", ""),
                "source_document": result.get("source_document", ""),
                "score": score,
            })

        # Deduplicate — max 2 chunks per source document
        docs = _deduplicate_by_document(docs, max_per_doc=2)

        # Trim to requested top_k
        docs = docs[:top_k]

        logger.info(
            f"📚 Knowledge search for '{query[:50]}...' returned {len(docs)} results "
            f"(types: {set(d.get('insurance_type', '?') for d in docs)})"
        )
        return docs

    except Exception as e:
        logger.error(f"Azure Search failed: {e}")
        return []


def get_compliance_alerts(intent: str, transcript: str) -> list[dict]:
    """
    Search for compliance rules relevant to the current call.
    Uses Azure AI Search filtered to 'compliance' insurance_type.
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

        # Filter to compliance docs only using the new insurance_type field
        filter_expr = "insurance_type eq 'compliance'"

        results = client.search(
            search_text=search_query,
            vector_queries=[vector_query],
            filter=filter_expr,
            top=5,
            select=["title", "content", "section_heading", "document_id", "insurance_type", "source_document"],
        )

        alerts = []
        for result in results:
            score = result.get("@search.score", 0)
            if score < MIN_SEARCH_SCORE:
                continue

            alerts.append({
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "section_heading": result.get("section_heading", ""),
                "severity": "HIGH",
                "document_id": result.get("document_id", ""),
                "source_document": result.get("source_document", ""),
            })

        logger.info(f"Compliance check for '{intent}' returned {len(alerts)} alerts")
        return alerts

    except Exception as e:
        logger.error(f"Azure compliance search failed: {e}")
        return []
