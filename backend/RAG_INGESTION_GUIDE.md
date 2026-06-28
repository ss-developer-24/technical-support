# RAG Document Ingestion Guide

## Problem
RAG queries return no results because ChromaDB collection is empty.

```
WARNING:rag.rag_engine:No documents in ChromaDB collection, returning empty results
```

## Solution: Ingest Documents

### Option 1: Via API Endpoint (Recommended)

Trigger ingestion via the `/api/ingest` endpoint:

```bash
# Using Cloud Console or another Cloud Run service
curl -X POST https://YOUR-SERVICE-URL/api/ingest \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "status": "started",
  "message": "Document ingestion started in background. Check logs for progress."
}
```

### Option 2: Run Ingestion Script Locally

If you have access to credentials:

```bash
cd backend

# Set environment variables
export GCP_PROJECT_ID=technical-support-499903
export GCS_BUCKET_NAME=src_docs
export VERTEX_AI_LOCATION=us-central1
export GOOGLE_API_KEY=your-api-key
export CHROMA_PERSIST_DIR=./chromadb_local

# Run ingestion
python3 ingest_documents.py
```

### Option 3: Via Cloud Run Job

Create a one-time Cloud Run job:

```bash
# Build the same image
gcloud builds submit --config deployment/cloudbuild.yaml

# Run as a job
gcloud run jobs create ingest-docs \
  --image us-central1-docker.pkg.dev/technical-support-499903/docker-repo/technical-support-backend:latest \
  --region us-central1 \
  --command python3 \
  --args ingest_documents.py \
  --set-env-vars "GCP_PROJECT_ID=technical-support-499903,VERTEX_AI_LOCATION=us-central1" \
  --set-secrets "GOOGLE_API_KEY=google-api-key:latest,GCS_BUCKET_NAME=gcs-bucket-name:latest"

# Execute the job
gcloud run jobs execute ingest-docs --region us-central1
```

### Option 4: Exec into Running Container

```bash
# Get the container instance
gcloud run services describe technical-support-backend \
  --region us-central1 \
  --format="value(status.url)"

# Trigger via internal Cloud Shell
gcloud run services proxy technical-support-backend \
  --region us-central1 \
  --port 8080 &

curl -X POST http://localhost:8080/api/ingest
```

## Verify Ingestion

Check the logs to see progress:

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=technical-support-backend" \
  --limit 50 \
  --format="value(textPayload)" \
  --project technical-support-499903 | grep -i "ingest\|chroma\|document"
```

Expected log output:
```
INFO:rag.rag_engine:Starting document ingestion from gs://src_docs
INFO:rag.rag_engine:Found 1 PDF files
INFO:rag.rag_engine:Processing 1/1: TIS-084...
INFO:rag.rag_engine:Adding 45 documents to ChromaDB...
INFO:rag.rag_engine:Successfully ingested 45 document chunks. Total in collection: 45
```

## Test RAG After Ingestion

Once documents are ingested, test with a relevant question:

```bash
curl -X POST https://YOUR-SERVICE-URL/api/question \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the virtual host requirements?"
  }'
```

The response should now include relevant content from the ingested PDF.

## Troubleshooting

### "No documents in ChromaDB collection"
- Documents haven't been ingested yet - run ingestion
- ChromaDB storage is ephemeral (at /tmp/chromadb) - data lost on container restart
- Solution: Re-run ingestion after every deployment or configure persistent storage

### "Permission denied" accessing GCS bucket
- Check service account has `roles/storage.objectViewer` or `roles/storage.objectAdmin`
- Verify GCS_BUCKET_NAME environment variable is correct

### Ingestion times out
- Large PDFs may take time to process
- The `/api/ingest` endpoint runs in background - check logs for completion
- Increase Cloud Run timeout if needed (currently 300s)

## Making Storage Persistent

ChromaDB currently uses `/tmp/chromadb` which is ephemeral. To make it persistent:

### Use Cloud Storage FUSE

Update Cloud Run service to mount GCS bucket:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
spec:
  template:
    spec:
      volumes:
      - name: chromadb-storage
        csi:
          driver: gcsfuse.csi.storage.gke.io
          volumeAttributes:
            bucketName: technical-support-chromadb-storage
      containers:
      - env:
        - name: CHROMA_PERSIST_DIR
          value: /mnt/chromadb
        volumeMounts:
        - name: chromadb-storage
          mountPath: /mnt/chromadb
```

Then deploy:
```bash
gcloud run services replace service.yaml --region us-central1
```

### Alternative: Use Cloud SQL with ChromaDB

For production, consider using ChromaDB with a remote backend (Cloud SQL PostgreSQL).

## Current Status

- **GCS Bucket**: `gs://src_docs/`
- **PDF Files**: 1 file found
  - `TIS-084, Virtual Host Server Requirements, Rev. A.pdf`
- **ChromaDB Collection**: `technical_support_docs`
- **Current Status**: Empty (needs ingestion)
- **Storage**: `/tmp/chromadb` (ephemeral)

## Next Steps

1. Run ingestion using one of the options above
2. Verify documents are loaded by checking logs
3. Test RAG queries
4. Consider implementing persistent storage for production
