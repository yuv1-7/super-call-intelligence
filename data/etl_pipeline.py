import os
import re
from typing import List, Dict, Any
from langchain_text_splitters import MarkdownHeaderTextSplitter
from sentence_transformers import SentenceTransformer
import torch
import torch.nn.functional as F
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)

# --- Configuration ---
DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs for embedding")
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "https://<your-service-name>.search.windows.net")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "<your-admin-key>")
INDEX_NAME = "knowledge-base-index"

# We use a strong local embedding model and pad to 1536 dimensions
# so the schema remains compatible if you switch to OpenAI later.
EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"  # Outputs 1024d
TARGET_DIMENSION = 1536

# ─── Insurance Type Detection Rules ─── #
# Maps document ID prefixes and department keywords to insurance types.
# Order matters: first match wins.
DOC_ID_PREFIX_TO_TYPE = {
    "SOP-FNOL": "auto",
    "KB-CAR": "auto",
    "POL-AUTO": "auto",
    "KB-ESP": "auto",
    "KB-GLS": "auto",
    "POL-ADDON": "auto",      # Add-ons are auto-specific in this KB
    "KB-LIFE": "life",
    "SOP-MED": "medical",
    "KB-MED": "medical",
    "COMP-": "compliance",
    "FRAUD-": "compliance",
}

DEPARTMENT_KEYWORDS_TO_TYPE = {
    "auto": "auto",
    "vehicle": "auto",
    "car": "auto",
    "life": "life",
    "medical": "medical",
    "hospitalization": "medical",
    "compliance": "compliance",
    "risk": "compliance",
    "fraud": "compliance",
    "legal": "compliance",
}


# --- Helper Functions ---

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def embed_texts(texts: List[str], model: SentenceTransformer) -> List[List[float]]:
    """Embeds texts using the local model and pads them to TARGET_DIMENSION (1536)."""
    embeddings = model.encode(texts, convert_to_tensor=True, device=get_device())

    current_dim = embeddings.shape[1]
    if current_dim < TARGET_DIMENSION:
        padding_size = TARGET_DIMENSION - current_dim
        embeddings = F.pad(embeddings, (0, padding_size), "constant", 0)
    elif current_dim > TARGET_DIMENSION:
        embeddings = embeddings[:, :TARGET_DIMENSION]

    # Re-normalize to ensure cosine similarity still works optimally
    embeddings = F.normalize(embeddings, p=2, dim=1)

    return embeddings.cpu().numpy().tolist()


def extract_metadata(content: str) -> Dict[str, str]:
    """Extracts bolded metadata key-value pairs from the top of the markdown."""
    metadata = {}
    lines = content.split('\n')
    for line in lines[:15]:
        match = re.match(r"\*\*(.+?):\*\*\s*(.+)", line.strip())
        if match:
            key = match.group(1).strip()
            safe_key = re.sub(r'[^a-zA-Z0-9_]', '_', key).lower()
            val = match.group(2).strip()
            metadata[safe_key] = val
    return metadata


def detect_insurance_type(doc_id: str, department: str, filename: str) -> str:
    """Determine the insurance_type for a document using its metadata.

    Priority:
    1. Document ID prefix (most reliable — IDs are structured)
    2. Department field keyword matching
    3. Filename keyword matching
    4. Default to 'general'
    """
    # 1. Check document ID prefix
    doc_id_upper = doc_id.upper()
    for prefix, ins_type in DOC_ID_PREFIX_TO_TYPE.items():
        if doc_id_upper.startswith(prefix):
            return ins_type

    # 2. Check department keywords
    dept_lower = department.lower()
    for keyword, ins_type in DEPARTMENT_KEYWORDS_TO_TYPE.items():
        if keyword in dept_lower:
            return ins_type

    # 3. Check filename keywords
    fname_lower = filename.lower()
    for keyword, ins_type in DEPARTMENT_KEYWORDS_TO_TYPE.items():
        if keyword in fname_lower:
            return ins_type

    return "general"


def extract_keywords(content: str, metadata: Dict[str, str]) -> str:
    """Build a keywords string from document metadata for BM25 text matching boost.

    Combines document ID, department, topic, and title into a single searchable string.
    """
    parts = []
    for key in ("document_id", "department", "topic", "applies_to", "system_role"):
        val = metadata.get(key)
        if val and val != "Unknown":
            parts.append(val)
    # Add the H1 title if present
    for line in content.split('\n')[:5]:
        line = line.strip()
        if line.startswith('# '):
            clean = re.sub(r'[*\\]', '', line[2:]).strip()
            parts.append(clean)
            break
    return " | ".join(parts)


def build_contextual_text(title: str, insurance_type: str, section_heading: str, content: str) -> str:
    """Build a context-enriched text for embedding.

    Prepending document-level context to the chunk content before embedding
    significantly improves retrieval precision. Without this, a generic chunk
    like 'Required Documents' matches across all insurance types.
    """
    type_label = {
        "auto": "Auto Insurance",
        "life": "Life Insurance",
        "medical": "Medical Insurance",
        "compliance": "Insurance Compliance",
        "general": "General Insurance",
    }.get(insurance_type, "Insurance")

    return f"[{type_label} — {title} — Section: {section_heading}]\n{content}"


def setup_azure_index():
    """Creates the Azure AI Search index (deletes and recreates if it exists)."""
    print(f"Setting up index '{INDEX_NAME}' at {AZURE_SEARCH_ENDPOINT}")
    credential = AzureKeyCredential(AZURE_SEARCH_KEY)
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="title", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SearchableField(name="document_id", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="department", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        # ── New fields for precision filtering ──
        SimpleField(name="insurance_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="source_document", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="keywords", type=SearchFieldDataType.String),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, sortable=True),
        SimpleField(name="total_chunks", type=SearchFieldDataType.Int32),
        # ──────────────────────────────────────
        SearchableField(name="section_heading", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        # 1536 Dimensions — Ready for text-embedding-ada-002 or 3-small
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=TARGET_DIMENSION,
            vector_search_profile_name="myHnswProfile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="myHnsw")
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw",
            )
        ],
    )

    index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)

    try:
        print(f"Clearing existing index '{INDEX_NAME}' if it exists...")
        index_client.delete_index(INDEX_NAME)
        print("Existing index deleted.")
    except Exception:
        pass  # Index might not exist yet

    try:
        result = index_client.create_or_update_index(index)
        print(f"Index created successfully: {result.name}")
    except Exception as e:
        print(f"Failed to create index. Ensure your endpoint and key are set. Error: {e}")
        return False
    return True


# --- Main Pipeline ---

def main():
    print(f"Using device: {get_device()}")

    # 1. Initialize local embedding model
    print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    # 2. Set up Markdown Header Splitter
    headers_to_split_on = [
        ("#", "title"),
        ("##", "section_heading_1"),
        ("###", "section_heading_2"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    all_chunks = []

    # 3. Process each Markdown file
    for filename in os.listdir(DOCS_DIR):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(DOCS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract global file metadata (Document ID, Department, etc.)
        file_metadata = extract_metadata(content)

        # Detect the insurance type from metadata + filename
        doc_id = file_metadata.get("document_id", "")
        department = file_metadata.get("department", "")
        insurance_type = detect_insurance_type(doc_id, department, filename)

        # Determine a broad category based on filename or metadata (kept for backward compat)
        topic_or_filename = file_metadata.get("topic", filename).lower()
        category = "general"
        if "fnol" in topic_or_filename or "claim" in topic_or_filename:
            category = "claims"
        elif "compliance" in topic_or_filename or "guideline" in topic_or_filename:
            category = "compliance"
        elif "policy" in topic_or_filename or "coverage" in topic_or_filename:
            category = "policy"

        # Build keywords string for BM25 boost
        keywords = extract_keywords(content, file_metadata)

        # The source_document is the clean filename without extension
        source_document = filename.replace(".md", "")

        # Split the document
        splits = markdown_splitter.split_text(content)
        total_chunks = len(splits)

        print(f"  📄 {filename}: {total_chunks} chunks, insurance_type={insurance_type}, category={category}")

        for i, split in enumerate(splits):
            # Combine header logic to get the most specific section heading
            heading = split.metadata.get("section_heading_2", split.metadata.get("section_heading_1", "General"))
            title = split.metadata.get("title", file_metadata.get("document_id", filename))

            # Construct a safe, unique ID
            chunk_id = f"{filename.replace(' ', '_').replace('.md', '')}_chunk_{i}"
            chunk_id = re.sub(r'[^a-zA-Z0-9_\-]', '', chunk_id)

            chunk_data = {
                "id": chunk_id,
                "title": title,
                "document_id": file_metadata.get("document_id", "Unknown"),
                "department": file_metadata.get("department", "Unknown"),
                "category": category,
                "insurance_type": insurance_type,
                "source_document": source_document,
                "keywords": keywords,
                "chunk_index": i,
                "total_chunks": total_chunks,
                "section_heading": heading,
                "content": split.page_content,
                # content_vector populated below after embedding
            }
            all_chunks.append(chunk_data)

    print(f"\nGenerated {len(all_chunks)} semantic chunks. Embedding now...")

    # 4. Generate Embeddings — with contextual prefix for precision
    #    Instead of embedding raw chunk content, we prepend document-level context
    #    so the embedding model understands the domain.
    texts_to_embed = [
        build_contextual_text(
            title=chunk["title"],
            insurance_type=chunk["insurance_type"],
            section_heading=chunk["section_heading"],
            content=chunk["content"],
        )
        for chunk in all_chunks
    ]

    vectors = embed_texts(texts_to_embed, model)

    for chunk, vector in zip(all_chunks, vectors):
        chunk["content_vector"] = vector

    print("Embedding complete. Indexing into Azure AI Search...")

    # 5. Upload to Azure AI Search
    if setup_azure_index():
        credential = AzureKeyCredential(AZURE_SEARCH_KEY)
        search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)

        try:
            result = search_client.upload_documents(documents=all_chunks)
            print(f"Successfully uploaded {len(result)} documents to Azure AI Search.")
        except Exception as e:
            print(f"Failed to upload documents. Error: {e}")

    # Print summary
    type_counts: dict[str, int] = {}
    for chunk in all_chunks:
        t = chunk["insurance_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    print("\n── Index Summary ──")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count} chunks")


if __name__ == "__main__":
    main()
