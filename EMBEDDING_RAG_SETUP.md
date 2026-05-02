# Embedding RAG Setup

The app now supports semantic RAG with Gemini embeddings and a local vector
index. It uses the Gemini REST `embedContent` API with `gemini-embedding-001`,
so it does not depend on the deprecated `google.generativeai` embedding client.
It does not require Firebase Storage billing, Pinecone, PGVector, or Vertex AI
Vector Search.

## 1. Enable Embeddings

Add these values to `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
RAG_USE_EMBEDDINGS=true
RAG_EMBEDDING_MODEL=gemini-embedding-001
RAG_VECTOR_INDEX_PATH=.rag_index/context_vectors.json
```

Use a Gemini API key from Google AI Studio. Do not paste the Firebase web API
key here.

## 2. Build The Vector Index

From the project folder:

```powershell
python -m data.embedding_rag
```

This creates:

```text
.rag_index/context_vectors.json
```

The `.rag_index/` folder is ignored by git because it can be rebuilt.

## 3. Runtime Behavior

When embeddings are enabled, retrieval runs in this order:

```text
BigQuery context if enabled -> Gemini vector index -> TF-IDF/keyword fallback
```

If the Gemini key is missing or embedding generation fails, the app continues
using the existing TF-IDF/BigQuery retriever.
