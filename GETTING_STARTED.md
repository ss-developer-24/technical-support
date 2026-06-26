# Getting Started Guide

This guide will help you get the Technical Support Assistant up and running quickly.

## Prerequisites

### Required
- Python 3.11 or higher
- Google Cloud Platform account
- Google AI API key (for Gemini)
- Tavily API key (for web search)

### Optional (for deployment)
- Docker
- Google Cloud SDK (`gcloud` CLI)

## Step 1: Get API Keys

### 1.1 Google AI API Key
1. Visit https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key - you'll need it later

### 1.2 Tavily API Key
1. Visit https://tavily.com/
2. Sign up for an account
3. Get your API key from the dashboard

### 1.3 Google Cloud Project
1. Visit https://console.cloud.google.com/
2. Create a new project or select existing
3. Enable required APIs:
   ```bash
   gcloud services enable \
       run.googleapis.com \
       cloudbuild.googleapis.com \
       aiplatform.googleapis.com \
       storage.googleapis.com \
       secretmanager.googleapis.com
   ```

## Step 2: Create GCS Bucket

Upload your PDF documents for RAG:

```bash
# Create bucket
gsutil mb -l us-central1 gs://your-bucket-name

# Upload PDFs
gsutil cp your-documents/*.pdf gs://your-bucket-name/
```

## Step 3: Quick Setup (Local)

### Automated Setup
```bash
# Clone or navigate to project
cd technical-support

# Run setup script
./setup.sh
```

### Manual Setup

#### Backend
```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `backend/.env`:
```env
GOOGLE_API_KEY=your-google-api-key-here
TAVILY_API_KEY=your-tavily-api-key-here
GCP_PROJECT_ID=your-gcp-project-id
GCS_BUCKET_NAME=your-bucket-name
VERTEX_AI_LOCATION=us-central1
ENABLE_RAG=true
```

#### Frontend
```bash
cd frontend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `frontend/.env`:
```env
API_HOST=http://localhost:8000
```

```bash
cd ..
```

## Step 4: Run Locally

### Start Backend
```bash
cd backend
source venv/bin/activate
python main.py
```

Backend will start at: http://localhost:8000

Verify it's running:
```bash
curl http://localhost:8000/health
```

### Ingest Documents (First Time Only)
```bash
curl -X POST http://localhost:8000/api/ingest
```

This will:
- Read PDFs from your GCS bucket
- Extract text and create chunks
- Generate embeddings using Vertex AI
- Store in vector database

### Start Frontend
In a new terminal:
```bash
cd frontend
export API_HOST=http://localhost:8000
streamlit run app.py
```

Frontend will start at: http://localhost:8501

## Step 5: Test the System

### Option 1: Using the UI
1. Open http://localhost:8501
2. Check connection status in sidebar (should show "✅ Connected")
3. Type a question in the chat input
4. Wait for response from agents

### Option 2: Using the Test Script
```bash
cd backend
python test_backend.py http://localhost:8000
```

### Option 3: Using curl
```bash
# Test health
curl http://localhost:8000/health

# Test status
curl http://localhost:8000/api/status

# Ask a question
curl -X POST http://localhost:8000/api/question \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Python?"}'
```

## Step 6: Deploy to Google Cloud Run

### Prerequisites
```bash
# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Set region
gcloud config set run/region us-central1
```

### Grant Cloud Build Permissions

Cloud Build needs permissions to push images and deploy:

```bash
# Get project number
PROJECT_NUM=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')

# Grant Container Registry permissions
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
    --member=serviceAccount:${PROJECT_NUM}@cloudbuild.gserviceaccount.com \
    --role=roles/storage.admin

# Grant Artifact Registry permissions
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
    --member=serviceAccount:${PROJECT_NUM}@cloudbuild.gserviceaccount.com \
    --role=roles/artifactregistry.writer
```

### Store Secrets
```bash
# Store API keys in Secret Manager
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create google-api-key --data-file=-
echo -n "YOUR_TAVILY_API_KEY" | gcloud secrets create tavily-api-key --data-file=-
echo -n "YOUR_BUCKET_NAME" | gcloud secrets create gcs-bucket-name --data-file=-

# Grant access to secrets
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
for secret in google-api-key tavily-api-key gcs-bucket-name; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

### Deploy Backend
```bash
cd backend
./deploy.sh
```

Get the backend URL:
```bash
gcloud run services describe technical-support-backend \
  --region us-central1 \
  --format 'value(status.url)'
```

### Deploy Frontend
```bash
cd ..  # Back to project root
./deploy.sh YOUR_PROJECT_ID us-central1 https://your-backend-url
```

## Common Issues & Solutions

### Issue: "GOOGLE_API_KEY environment variable is required"
**Solution**: Make sure you've set the environment variable or added it to `.env`:
```bash
export GOOGLE_API_KEY=your-key-here
```

### Issue: "No documents in store"
**Solution**: Run the ingestion endpoint:
```bash
curl -X POST http://localhost:8000/api/ingest
```

### Issue: "Connection failed" in frontend
**Solution**: 
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify API_HOST is correct: `echo $API_HOST`
3. Check firewall settings

### Issue: "Permission denied" errors in GCP
**Solution**: Grant necessary permissions:
```bash
PROJECT_ID=$(gcloud config get-value project)
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/storage.objectViewer"
```

### Issue: Embeddings are slow
**Solution**: 
- Use batch processing (already implemented)
- Consider caching (already implemented)
- Use Vertex AI Vector Search for production

### Issue: Tavily API rate limits
**Solution**:
- Reduce max_results in web search
- Implement request queuing
- Upgrade Tavily plan

## Next Steps

1. **Customize Agents**: Edit agent prompts in `backend/agents/`
2. **Add More Documents**: Upload PDFs to GCS and re-run ingestion
3. **Monitor Performance**: Check Cloud Run metrics
4. **Set Up Alerts**: Configure monitoring and alerting
5. **Add Authentication**: Implement IAM or custom auth
6. **Optimize Costs**: Review and adjust resource allocation

## Useful Commands

```bash
# View backend logs (local)
cd backend && python main.py 2>&1 | tee backend.log

# View backend logs (Cloud Run)
gcloud run services logs read technical-support-backend --limit 50

# Restart backend
# Local: Ctrl+C and run again
# Cloud Run: redeploy or update env var

# Check agent status
curl http://localhost:8000/api/status | jq

# Clear embeddings cache
rm /tmp/embeddings_cache.pkl

# Update secrets
echo -n "NEW_KEY" | gcloud secrets versions add google-api-key --data-file=-
```

## Resources

- [Backend Documentation](backend/README.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Google ADK Documentation](https://ai.google.dev/gemini-api/docs/adk)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Tavily API Documentation](https://docs.tavily.com/)

## Support

For issues or questions:
1. Check the documentation files
2. Review logs for error messages
3. Verify all API keys and credentials
4. Ensure all GCP APIs are enabled
5. Check service account permissions

Happy building! 🚀
