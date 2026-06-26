# Technical Support Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Interface                          │
│                      (Streamlit Frontend)                        │
│                                                                  │
│  - Chat Interface                                               │
│  - Connection Monitoring                                        │
│  - Configuration                                                │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     │ HTTP/REST API
                     │
┌────────────────────▼─────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Orchestrator Agent                          │  │
│  │              (Google ADK / Gemini)                       │  │
│  │                                                          │  │
│  │  - Analyzes query requirements                          │  │
│  │  - Coordinates agent workflow                           │  │
│  │  - Generates final response                             │  │
│  └───────────────┬──────────────────────┬───────────────────┘  │
│                  │                      │                       │
│      ┌───────────▼──────────┐  ┌───────▼────────────┐         │
│      │  Researcher Agent    │  │  Reviewer Agent     │         │
│      │  (Google ADK)        │  │  (Google ADK)       │         │
│      │                      │  │                     │         │
│      │  - Web Search        │  │  - Quality Check    │         │
│      │  - RAG Retrieval     │  │  - Validation       │         │
│      │  - Synthesis         │  │  - Improvement      │         │
│      └──────┬────────┬──────┘  └─────────────────────┘         │
│             │        │                                          │
└─────────────┼────────┼──────────────────────────────────────────┘
              │        │
              │        │
    ┌─────────▼────┐   │
    │ Tavily API   │   │
    │              │   │
    │ Web Search   │   │
    └──────────────┘   │
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │         Google Cloud Platform                      │
         │                                                    │
         │  ┌──────────────────┐  ┌─────────────────────┐   │
         │  │  Vertex AI       │  │  Cloud Storage      │   │
         │  │                  │  │                     │   │
         │  │  - Text          │  │  - PDF Documents    │   │
         │  │    Embeddings    │  │  - Source Data      │   │
         │  │  - Vector        │  │                     │   │
         │  │    Search        │  │                     │   │
         │  └──────────────────┘  └─────────────────────┘   │
         │                                                    │
         └────────────────────────────────────────────────────┘
```

## Request Flow

1. **User Query** → Streamlit Frontend
2. **Frontend** → POST /api/question → FastAPI Backend
3. **Orchestrator Agent**:
   - Analyzes if research is needed
   - If yes → calls Researcher Agent
   - If no → generates response directly
4. **Researcher Agent** (if invoked):
   - Performs parallel search:
     - Web search via Tavily API
     - RAG search via Vertex AI embeddings
   - Synthesizes findings using Gemini
   - Returns context and sources
5. **Orchestrator** → Generates response using research context
6. **Reviewer Agent**:
   - Assesses response quality
   - If score < 0.7 → improves response
   - Returns final answer with quality metrics
7. **Backend** → Returns response to Frontend
8. **Frontend** → Displays answer to user

## Data Flow for RAG

```
PDF Documents (GCS Bucket)
         │
         │ 1. Ingest (POST /api/ingest)
         ▼
    PDF Parsing
         │
         │ 2. Text Extraction & Chunking
         ▼
  Vertex AI Embeddings
         │
         │ 3. Generate Embeddings
         ▼
   Vector Storage
    (In-Memory)
         │
         │ 4. Query Time: Semantic Search
         ▼
  Relevant Documents
         │
         │ 5. Return to Researcher
         ▼
   Answer Generation
```

## Agent Interactions

```
┌─────────────────┐
│  User Question  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Orchestrator Agent     │
│  "Does this need        │
│   research?"            │
└────┬──────────────┬─────┘
     │ YES          │ NO
     │              │
     ▼              ▼
┌────────────┐  ┌──────────────┐
│ Researcher │  │ Direct       │
│ Agent      │  │ Response     │
└─────┬──────┘  └──────┬───────┘
      │                │
      │ Research       │
      │ Results        │
      │                │
      ▼                ▼
┌────────────────────────────┐
│  Orchestrator              │
│  "Generate answer with     │
│   research context"        │
└──────────────┬─────────────┘
               │
               ▼
     ┌─────────────────┐
     │ Reviewer Agent  │
     │ "Check quality" │
     └────────┬────────┘
              │
              ▼ Quality < 0.7?
     ┌─────────────────┐
     │ Improve Answer  │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │ Final Response  │
     └─────────────────┘
```

## Technology Stack

### Frontend
- **Framework**: Streamlit
- **Language**: Python 3.11
- **Container**: Docker
- **Deployment**: Google Cloud Run

### Backend
- **Framework**: FastAPI
- **Agent SDK**: Google ADK (Agent Development Kit)
- **LLM**: Google Gemini (2.0 Flash / Pro)
- **Language**: Python 3.11
- **Container**: Docker
- **Deployment**: Google Cloud Run

### AI/ML Services
- **LLM Provider**: Google AI (Gemini)
- **Embeddings**: Vertex AI (textembedding-gecko@003)
- **Web Search**: Tavily API
- **RAG Storage**: In-memory (production: Vertex AI Vector Search)

### Infrastructure
- **Cloud Provider**: Google Cloud Platform
- **Storage**: Google Cloud Storage
- **Container Registry**: Google Container Registry
- **Secrets**: Google Secret Manager
- **CI/CD**: Google Cloud Build

## Scalability & Performance

### Backend
- Horizontal scaling via Cloud Run
- Lazy agent initialization
- Parallel research (RAG + Web Search)
- In-memory caching for embeddings
- Async/await for I/O operations

### Frontend
- Stateless design
- Session state management
- Connection pooling
- Timeout handling

## Security

1. **API Keys**: Stored in Secret Manager
2. **Service Account**: Least privilege access
3. **Network**: HTTPS only
4. **Authentication**: Optional IAM integration
5. **Secrets**: Never logged or committed

## Cost Optimization

1. **Cloud Run**: Pay per request, auto-scaling to zero
2. **Vertex AI**: Batch embeddings, caching
3. **Tavily**: Limited to necessary searches
4. **Storage**: Lifecycle policies for old data
5. **Model Selection**: Use Flash for efficiency

## Future Enhancements

1. **Vector Database**: Migrate to Vertex AI Vector Search
2. **Streaming**: Real-time response streaming
3. **Multi-turn**: Conversation context management
4. **Fine-tuning**: Custom models for domain
5. **Analytics**: Usage tracking and insights
6. **Authentication**: User management system
7. **Rate Limiting**: API throttling
8. **Caching**: Response caching for common queries
