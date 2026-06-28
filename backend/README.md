# Backend Deployment Guide

This guide covers deploying the Technical Support Backend with Google ADK agents to Google Cloud Run.

## Architecture Overview

The backend consists of three Google ADK agents:

1. **Orchestrator Agent** - Coordinates workflow between other agents
2. **Researcher Agent** - Performs web search (Tavily) and RAG retrieval (Vertex AI)
3. **Reviewer Agent** - Reviews and improves responses for quality

## Prerequisites

### Required Tools
- Google Cloud SDK (`gcloud` CLI)
- Docker
- Python 3.11+

### Required GCP APIs
Enable these APIs in your GCP project:
```bash
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com
```

### Required API Keys
1. **Google AI API Key** - For Gemini models via Google ADK
   - Get from: https://aistudio.google.com/app/apikey
   
2. **Tavily API Key** - For web search
   - Get from: https://tavily.com/

## Setup Instructions

### 1. Configure GCP Project
```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Set default region
gcloud config set run/region us-central1
```

### 2. Create GCS Bucket for PDFs
```bash
# Create bucket for PDF documents
gsutil mb -l us-central1 gs://YOUR_BUCKET_NAME

# Upload PDF documents
gsutil cp your-documents/*.pdf gs://YOUR_BUCKET_NAME/
```

### 3. Store Secrets in Secret Manager
```bash
# Create secrets
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create google-api-key --data-file=-
echo -n "YOUR_TAVILY_API_KEY" | gcloud secrets create tavily-api-key --data-file=-
echo -n "YOUR_BUCKET_NAME" | gcloud secrets create gcs-bucket-name --data-file=-

# Grant Cloud Run access to secrets
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding google-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding tavily-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gcs-bucket-name \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 4. Grant Service Account Permissions
```bash
# Get the default compute service account
PROJECT_ID=$(gcloud config get-value project)
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectViewer"
```

## Deployment

### Option 1: Using the Deploy Script
```bash
cd backend
chmod +x deployment/deploy.sh
./deployment/deploy.sh
```

### Option 2: Using Cloud Build

**First-time setup - Grant Cloud Build permissions:**
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

**Deploy:**
```bash
# Submit build from backend directory
cd backend
gcloud builds submit --config deployment/cloudbuild.yaml .
```

### Option 3: Manual Deployment
```bash
# Build the image (Dockerfile is in deployment/ subdirectory)
cd backend
docker build -f deployment/Dockerfile -t gcr.io/YOUR_PROJECT_ID/technical-support-backend .

# Push to GCR
docker push gcr.io/YOUR_PROJECT_ID/technical-support-backend

# Deploy to Cloud Run
gcloud run deploy technical-support-backend \
    --image gcr.io/YOUR_PROJECT_ID/technical-support-backend \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --set-env-vars "GCP_PROJECT_ID=YOUR_PROJECT_ID" \
    --set-env-vars "VERTEX_AI_LOCATION=us-central1" \
    --set-secrets "GOOGLE_API_KEY=google-api-key:latest" \
    --set-secrets "TAVILY_API_KEY=tavily-api-key:latest" \
    --set-secrets "GCS_BUCKET_NAME=gcs-bucket-name:latest"
```

## Initial Document Ingestion

After deployment, ingest PDF documents to create embeddings:

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe technical-support-backend \
    --platform managed \
    --region us-central1 \
    --format 'value(status.url)')

# Trigger document ingestion
curl -X POST "$SERVICE_URL/api/ingest"
```

## Testing the Deployment

### Health Check
```bash
curl $SERVICE_URL/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "technical-support-backend",
  "agents": {
    "orchestrator": false,
    "researcher": false,
    "reviewer": false
  }
}
```

### Ask a Question
```bash
curl -X POST "$SERVICE_URL/api/question" \
    -H "Content-Type: application/json" \
    -d '{"question": "How do I configure authentication?"}'
```

### Check Status
```bash
curl "$SERVICE_URL/api/status"
```

## Local Development

### Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your values
```

### Run Locally
```bash
# Set environment variables
export GOOGLE_API_KEY="your-key"
export TAVILY_API_KEY="your-key"
export GCP_PROJECT_ID="your-project"
export GCS_BUCKET_NAME="your-bucket"

# Run the server
python main.py
```

The server will start at http://localhost:8000

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GCP_PROJECT_ID` | Yes | Google Cloud Project ID |
| `GCS_BUCKET_NAME` | Yes | GCS bucket with PDF documents |
| `GOOGLE_API_KEY` | Yes | Google AI API key for Gemini |
| `TAVILY_API_KEY` | Yes | Tavily API key for web search |
| `VERTEX_AI_LOCATION` | No | Vertex AI region (default: us-central1) |
| `ORCHESTRATOR_MODEL` | No | Model for orchestrator (default: gemini-2.5-flash-lite) |
| `RESEARCHER_MODEL` | No | Model for researcher (default: gemini-2.5-flash-lite) |
| `REVIEWER_MODEL` | No | Model for reviewer (default: gemini-2.5-flash-lite) |
| `ENABLE_RAG` | No | Enable RAG retrieval (default: true) |
| `PORT` | No | Server port (default: 8000) |
| `LANGSMITH_TRACING` | No | Enable LangSmith observability (default: false) |
| `LANGSMITH_API_KEY` | No | LangSmith API key for tracing |
| `LANGSMITH_PROJECT` | No | LangSmith project name (default: technical-support) |

### Agent Configuration

Each agent can use different Gemini models:
- `gemini-2.5-flash-lite` - Fast, efficient (recommended, default)
- `gemini-2.0-flash-exp` - Experimental features
- `gemini-pro` - Balanced performance
- `gemini-1.5-pro` - Most capable

## Observability

### LangSmith Integration

LangSmith provides distributed tracing and monitoring for agent interactions:

- ✅ **Trace agent execution flow** (Orchestrator → Researcher → Reviewer)
- ✅ **Monitor performance** (latency, errors, success rate)
- ✅ **Track RAG vs. web search usage**
- ✅ **Capture inputs/outputs** for debugging
- ✅ **Analyze answer quality** over time

**Setup:** See [LANGSMITH_SETUP.md](./LANGSMITH_SETUP.md) for complete configuration guide.

**Quick enable:**
```bash
gcloud run services update technical-support-backend \
  --region us-central1 \
  --set-env-vars "LANGSMITH_TRACING=true,LANGSMITH_PROJECT=technical-support" \
  --update-secrets "LANGSMITH_API_KEY=langsmith-api-key:latest"
```

## Monitoring

### View Logs
```bash
gcloud run services logs read technical-support-backend \
    --region us-central1 \
    --limit 50
```

### View Metrics
```bash
# In Google Cloud Console
# Navigate to: Cloud Run > technical-support-backend > Metrics
```

## Troubleshooting

### Common Issues

**Issue: "GOOGLE_API_KEY environment variable is required"**
- Ensure the secret is created and IAM permissions are set
- Check secret version is latest

**Issue: "No documents in store"**
- Run the ingestion endpoint: `POST /api/ingest`
- Verify PDFs are in the GCS bucket
- Check service account has storage.objectViewer role

**Issue: "Vertex AI initialization failed"**
- Ensure aiplatform.googleapis.com is enabled
- Verify VERTEX_AI_LOCATION is correct
- Check service account has aiplatform.user role

**Issue: "Tavily search error"**
- Verify TAVILY_API_KEY is correct
- Check Tavily API quota and limits

### Debug Mode
Enable detailed logging:
```bash
gcloud run services update technical-support-backend \
    --update-env-vars "LOG_LEVEL=DEBUG"
```

## Updating the Service

### Update Code
```bash
# Make your changes, then redeploy
./deploy.sh
```

### Update Environment Variables
```bash
gcloud run services update technical-support-backend \
    --update-env-vars "ENABLE_RAG=false"
```

### Update Secrets
```bash
# Update secret value
echo -n "NEW_API_KEY" | gcloud secrets versions add google-api-key --data-file=-

# Restart service to use new secret
gcloud run services update technical-support-backend \
    --update-env-vars "RESTART=$(date +%s)"
```

## Cost Optimization

- **Memory**: Start with 2Gi, adjust based on metrics
- **CPU**: Use 2 CPUs for parallel agent processing
- **Max Instances**: Set based on expected load
- **Request Timeout**: 300s for complex queries with research

## Security Best Practices

1. **Never commit API keys** - Always use Secret Manager
2. **Restrict service access** - Remove `--allow-unauthenticated` for production
3. **Use VPC** - Deploy in VPC for additional security
4. **Enable audit logs** - Track API usage
5. **Rotate secrets** - Regularly update API keys

## Next Steps

1. Configure the frontend `app.py` to point to your backend URL
2. Deploy frontend to Cloud Run (see main DEPLOYMENT.md)
3. Set up monitoring and alerting
4. Configure custom domain
5. Enable authentication if required
