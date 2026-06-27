# RAG Sources Feature Implementation

## Overview
The frontend and backend have been modified to properly display and track the source of information, distinguishing between RAG (internal documentation) and web sources.

## Backend Changes

### File: `backend/agents/researcher.py`
- **Enhanced RAG source tracking**: Modified the `_synthesize_research()` method to include detailed metadata for RAG sources:
  - `type`: "rag" (distinguishes from "web" sources)
  - `document`: Original document filename from GCS
  - `source`: Full source path/name
  - `chunk_id`: Chunk identifier within the document
  - `content`: Excerpt from the document
  - `score`: Relevance score from vector similarity

## Frontend Changes

### File: `frontend/app.py`
- **Enhanced source display**: Modified chat interface to show sources with expandable sections:
  - Separate sections for RAG (Internal Documentation) and Web sources
  - RAG sources show:
    - 📄 Document icon
    - Document name
    - Relevance score
    - Source path
    - Excerpt from the document
  - Web sources show:
    - 🌐 Web icon
    - Title and clickable URL
    - Relevance score
    - Content excerpt
  
- **Persistent sources in chat history**: Sources are now stored with each message and displayed when scrolling through chat history

## How It Works

1. **Question Processing**:
   - User asks a question through the frontend
   - Backend orchestrator determines if research is needed
   - Researcher agent queries both RAG engine and web search in parallel

2. **RAG Search** (if documents are available):
   - Generates embeddings for the query
   - Performs cosine similarity search against document embeddings
   - Returns top-k relevant document chunks with metadata

3. **Source Attribution**:
   - RAG results include document name, chunk ID, and source path
   - Web results include URL, title, and content
   - All sources include relevance scores

4. **Frontend Display**:
   - Answer is displayed first
   - Sources section appears below with expandable cards
   - Internal documentation (RAG) shown separately from web sources
   - Each source shows relevance score and preview

## Testing

Test the backend:
```bash
curl -X POST https://technical-support-backend-255507724672.us-central1.run.app/api/question \
  -H "Content-Type: application/json" \
  -d '{"question": "Your question here"}' | python3 -m json.tool
```

Expected response structure:
```json
{
  "answer": "The answer text...",
  "sources": [
    {
      "type": "rag",
      "title": "Document name (chunk 1/5)",
      "document": "example.pdf",
      "source": "example.pdf",
      "chunk_id": 0,
      "content": "Excerpt from document...",
      "score": 0.85
    },
    {
      "type": "web",
      "title": "Web Page Title",
      "url": "https://example.com/page",
      "content": "Excerpt from web page...",
      "score": 0.89
    }
  ]
}
```

## Future Enhancements

- Add page numbers for RAG sources
- Implement source highlighting in answers
- Add filtering options for source types
- Enable direct document download from sources
- Add citation formatting options

