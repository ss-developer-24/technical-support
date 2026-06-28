# ChromaDB Setup Guide

The RAG engine now uses **ChromaDB** for persistent vector storage instead of ephemeral in-memory storage.

## Benefits of ChromaDB

✅ **Simple Setup** - No cloud infrastructure required  
✅ **Persistent Storage** - Data survives container restarts (with volume mounts)  
✅ **Built-in Vector Search** - Optimized similarity search included  
✅ **Metadata Filtering** - Filter results by document properties  
✅ **Cost-Effective** - No additional cloud service costs  
✅ **Docker-Friendly** - Easy to configure in containers  

## Architecture

```
┌─────────────────┐
│   PDF Files     │
│   (GCS Bucket)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RAG Engine     │
│  Vertex AI      │
│  Embeddings     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   ChromaDB      │
│   Collections   │
│   (SQLite +     │
│    Index Files) │
└─────────────────┘
```

## Storage Architecture

ChromaDB stores data in a persistent directory:
- **SQLite Database**: Metadata and document text
- **Index Files**: Vector indices for fast similarity search
- **Default Location**: `/tmp/chromadb` (customizable)

## Configuration

### Environment Variables

```bash
# Optional - defaults to /tmp/chromadb
CHROMA_PERSIST_DIR=/data/chromadb
```

### For Production with Cloud Run

To make storage persistent across container restarts, you have two options:

#### Option 1: Cloud Storage FUSE (Recommended)

Mount a GCS bucket as a filesystem:

```yaml
# cloudbuild.yaml or deployment config
volumes:
  - name: chroma-data
    gcsfuse:
      bucketName: your-bucket-name
      mountPath: /data/chromadb
```

Then set:
```bash
CHROMA_PERSIST_DIR=/data/chromadb
```

#### Option 2: Cloud SQL or Firestore Backend

ChromaDB supports remote backends for distributed deployments (requires additional configuration).

### For Local Development

```bash
# Use local directory
export CHROMA_PERSIST_DIR=./chromadb_data
```

## Usage

### Initialization

The RAG engine automatically initializes ChromaDB:

```python
from rag.rag_engine import RAGEngine

# Creates/loads collection on initialization
engine = RAGEngine()
print(f"Collection has {engine.collection.count()} documents")
```

### Ingest Documents

```python
# Automatically chunks PDFs and stores in ChromaDB
result = await engine.ingest_from_gcs()
print(f"Ingested {result['count']} chunks")
print(f"Total documents: {result['total_documents']}")
```

### Search

```python
# Semantic search using Vertex AI embeddings + ChromaDB
results = await engine.search("How do I reset my password?", top_k=5)

for doc in results:
    print(f"Score: {doc['score']:.3f}")
    print(f"Source: {doc['metadata']['source']}")
    print(f"Content: {doc['content'][:200]}...")
    print("---")
```

### Clear Collection (Development)

```python
# Delete all documents
engine.chroma_client.delete_collection("technical_support_docs")
engine.collection = engine.chroma_client.create_collection("technical_support_docs")
```

## How It Works

### 1. Document Ingestion Flow

```
PDF → Extract Text → Chunk → Generate Embeddings → Store in ChromaDB
                                   (Vertex AI)         (id, embedding, text, metadata)
```

### 2. Search Flow

```
Query → Generate Embedding → ChromaDB Similarity Search → Ranked Results
           (Vertex AI)           (cosine distance)
```

### 3. Data Structure

Each document in ChromaDB has:
- **ID**: Unique identifier (hash-based)
- **Embedding**: 768-dimensional vector from Vertex AI
- **Document**: Full text content
- **Metadata**: Source file, chunk info, type

## Performance

### Storage

- **10,000 documents**: ~50-100 MB
- **100,000 documents**: ~500 MB - 1 GB
- Includes SQLite DB + HNSW indices

### Query Speed

- **< 1000 docs**: < 10ms
- **10,000 docs**: ~50ms
- **100,000 docs**: ~200ms
- **1M+ docs**: Consider partitioning or Vertex AI Vector Search

## Comparison: ChromaDB vs Vertex AI Vector Search

| Feature | ChromaDB | Vertex AI Vector Search |
|---------|----------|------------------------|
| Setup Complexity | ⭐ Simple | ⭐⭐⭐ Complex |
| Cost | Free (compute only) | ~$68/month (prod) |
| Scalability | Up to ~1M vectors | Billions of vectors |
| Latency | Good (<200ms) | Excellent (<10ms) |
| Persistence | Volume/FUSE required | Built-in |
| Maintenance | Low | Managed service |
| Best For | Dev & small-medium prod | Large-scale production |

## Troubleshooting

### "Collection not found"

The collection is created automatically. If deleted, restart the service.

### Slow queries

- ChromaDB is fast for up to 100K documents
- For larger datasets, consider:
  - Partitioning by document type
  - Migrating to Vertex AI Vector Search
  - Using ChromaDB's distance thresholds

### Data lost on restart

Ensure `CHROMA_PERSIST_DIR` points to a persistent volume:
- Local dev: Use a local directory outside `/tmp`
- Cloud Run: Mount GCS bucket via FUSE
- Docker: Use volume mounts

### Import errors

```bash
pip install chromadb==0.4.22
```

## Migration from In-Memory Storage

The previous implementation used:
```python
# Old: ephemeral pickle cache
self.embeddings_cache_file = "/tmp/embeddings_cache.pkl"
self.documents = []
self.embeddings = []
```

Now using:
```python
# New: ChromaDB persistent storage
self.chroma_client = chromadb.PersistentClient(path=chroma_persist_dir)
self.collection = self.chroma_client.get_collection("technical_support_docs")
```

**Benefits:**
- Survives container restarts (with persistent volume)
- Better query performance
- Built-in metadata filtering
- No manual similarity calculation needed

## Development vs Production

### Development
```bash
# Local directory
export CHROMA_PERSIST_DIR=./chromadb_data
```

### Production (Cloud Run)
```yaml
# Option 1: GCS FUSE
apiVersion: serving.knative.dev/v1
kind: Service
spec:
  template:
    spec:
      volumes:
      - name: chroma
        csi:
          driver: gcsfuse.csi.storage.gke.io
          volumeAttributes:
            bucketName: your-bucket
      containers:
      - env:
        - name: CHROMA_PERSIST_DIR
          value: /mnt/chroma
        volumeMounts:
        - name: chroma
          mountPath: /mnt/chroma
```

## Advanced: Custom Collection Configuration

```python
# Create collection with custom settings
collection = chroma_client.create_collection(
    name="technical_support_docs",
    metadata={
        "hnsw:space": "cosine",  # or "l2", "ip"
        "hnsw:construction_ef": 200,
        "hnsw:M": 16
    }
)
```

## Monitoring

### Check Collection Status

```python
# Count documents
count = engine.collection.count()
print(f"Documents: {count}")

# Get sample
results = engine.collection.peek(limit=5)
print(results)
```

### View All Collections

```python
collections = engine.chroma_client.list_collections()
for coll in collections:
    print(f"{coll.name}: {coll.count()} docs")
```

## Cost Comparison

### ChromaDB
- **Storage**: Cloud Run container storage + GCS FUSE (if used)
- **Compute**: Only Cloud Run instance costs
- **Typical**: ~$20-40/month for production

### Vertex AI Vector Search
- **Storage**: $0.30 per million nodes/month
- **Compute**: $0.045 per node-hour
- **Queries**: $0.40 per million queries
- **Typical**: ~$68/month for production

**Savings**: ~40-60% with ChromaDB for small-medium workloads

## When to Upgrade to Vertex AI Vector Search

Consider upgrading when:
- ✅ You have > 500K documents
- ✅ You need < 10ms query latency
- ✅ You need distributed queries across regions
- ✅ You need automatic scaling and replication

For most use cases, ChromaDB is sufficient and cost-effective.

## References

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [ChromaDB GitHub](https://github.com/chroma-core/chroma)
- [Cloud Run GCS FUSE](https://cloud.google.com/run/docs/tutorials/network-filesystems-fuse)
