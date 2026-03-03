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

# OpenAI's text-embedding-3-small uses 1536 dimensions.
# We'll use a strong, general-purpose local embedding model and pad/project it
# to 1536 dimensions so the schema remains compatible if you switch to OpenAI later.
EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5" # Outputs 1024d
TARGET_DIMENSION = 1536

# --- Helper Functions ---

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

def embed_texts(texts: List[str], model: SentenceTransformer) -> List[List[float]]:
    """Embeds texts using the local model and pads them to TARGET_DIMENSION (1536)."""
    # 1. Generate embeddings using the local model (e.g., 1024 dimensions)
    embeddings = model.encode(texts, convert_to_tensor=True, device=get_device())
    
    # 2. Pad to 1536 dimensions so the Azure index schema perfectly matches OpenAI
    current_dim = embeddings.shape[1]
    if current_dim < TARGET_DIMENSION:
        padding_size = TARGET_DIMENSION - current_dim
        # Pad with zeros at the end
        embeddings = F.pad(embeddings, (0, padding_size), "constant", 0)
    elif current_dim > TARGET_DIMENSION:
        # Truncate if necessary (though bge-large is 1024)
        embeddings = embeddings[:, :TARGET_DIMENSION]
        
    # 3. Re-normalize to ensure cosine similarity still works optimally
    embeddings = F.normalize(embeddings, p=2, dim=1)
    
    return embeddings.cpu().numpy().tolist()

def extract_metadata(content: str) -> Dict[str, str]:
    """Extracts bolded metadata key-value pairs from the top of the markdown."""
    # Matches patterns like: **Document ID:** SOP-FNOL-NS-001
    metadata = {}
    lines = content.split('\n')
    for line in lines[:15]: # Usually at the top
        match = re.match(r"\*\*(.+?):\*\*\s*(.+)", line.strip())
        if match:
            key = match.group(1).strip()
            # Normalize keys to be valid Azure Search field names (letters, digits, underscores)
            safe_key = re.sub(r'[^a-zA-Z0-9_]', '_', key).lower()
            val = match.group(2).strip()
            metadata[safe_key] = val
    return metadata

def setup_azure_index():
    """Creates the Azure AI Search index if it doesn't exist."""
    print(f"Setting up index '{INDEX_NAME}' at {AZURE_SEARCH_ENDPOINT}")
    credential = AzureKeyCredential(AZURE_SEARCH_KEY)
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)

    # Define the fields matching our previously discussed schema
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="title", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SearchableField(name="document_id", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="department", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="section_heading", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        # 1536 Dimensions - Ready for text-embedding-ada-002 or 3-small
        SearchField(name="content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True, vector_search_dimensions=TARGET_DIMENSION, vector_search_profile_name="myHnswProfile"),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="myHnsw"
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw",
            )
        ]
    )

    index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)
    
    try:
        result = index_client.create_or_update_index(index)
        print(f"Index created/updated successfully: {result.name}")
    except Exception as e:
        print(f"Failed to create/update index. Ensure your endpoint and key are set. Error: {e}")
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
        
        # Determine a broad category based on filename or metadata
        topic_or_filename = file_metadata.get("topic", filename).lower()
        category = "general"
        if "fnol" in topic_or_filename or "claim" in topic_or_filename:
            category = "claims"
        elif "compliance" in topic_or_filename or "guideline" in topic_or_filename:
            category = "compliance"
        elif "policy" in topic_or_filename or "coverage" in topic_or_filename:
            category = "policy"
            
        # Split the document
        splits = markdown_splitter.split_text(content)
        
        for i, split in enumerate(splits):
            # Combine header logic to get the most specific section heading
            heading = split.metadata.get("section_heading_2", split.metadata.get("section_heading_1", "General"))
            title = split.metadata.get("title", file_metadata.get("document_id", filename))
            
            # Construct a safe, unique ID
            chunk_id = f"{filename.replace(' ', '_').replace('.md', '')}_chunk_{i}"
            chunk_id = re.sub(r'[^a-zA-Z0-9_\-]', '', chunk_id) # Azure IDs must only contain letters, numbers, dashes, underscores
            
            chunk_data = {
                "id": chunk_id,
                "title": title,
                "document_id": file_metadata.get("document_id", "Unknown"),
                "department": file_metadata.get("department", "Unknown"),
                "category": category,
                "section_heading": heading,
                "content": split.page_content,
                # We will populate the vector next
            }
            all_chunks.append(chunk_data)

    print(f"Generated {len(all_chunks)} semantic chunks. Embedding now...")

    # 4. Generate Embeddings Custom Padded to 1536d
    texts_to_embed = [chunk["content"] for chunk in all_chunks]
    
    # Process in batches if large, but for these few docs we can do it all at once
    vectors = embed_texts(texts_to_embed, model)
    
    for chunk, vector in zip(all_chunks, vectors):
        chunk["content_vector"] = vector

    print("Embedding complete. Indexing into Azure AI Search...")

    # 5. Upload to Azure AI Search
    # Note: You MUST set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY environment variables
    # for this next part to succeed.
    if setup_azure_index():
        credential = AzureKeyCredential(AZURE_SEARCH_KEY)
        search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)
        
        try:
            result = search_client.upload_documents(documents=all_chunks)
            print(f"Successfully uploaded {len(result)} documents to Azure AI Search.")
        except Exception as e:
            print(f"Failed to upload documents. Error: {e}")
            
if __name__ == "__main__":
    main()
