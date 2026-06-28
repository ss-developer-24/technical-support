# Quick Reference Guide

## 🚀 Start Commands

```bash
# Local Backend
cd backend && python main.py

# Local Frontend  
cd frontend && streamlit run app.py

# Test Backend
cd backend && python test_backend.py

# Setup Everything
./setup.sh

# Deploy Backend
cd backend && ./deployment/deploy.sh

# Deploy Frontend
cd frontend && ./deploy.sh PROJECT_ID REGION BACKEND_URL
```

## 🔑 Required Environment Variables

### Backend (.env)
```bash
GOOGLE_API_KEY=<your-key>          # Required - Google AI
TAVILY_API_KEY=<your-key>          # Required - Tavily
GCP_PROJECT_ID=<project-id>        # Required - GCP
GCS_BUCKET_NAME=<bucket-name>      # Required - Storage
```

### Frontend (.env)
```bash
# Local development
API_HOST=http://localhost:8000

# Production (deployed backend)
API_HOST=https://technical-support-backend-255507724672.us-central1.run.app
```

## 🌐 Deployed Services

### Backend (Cloud Run)
```
URL: https://technical-support-backend-255507724672.us-central1.run.app
Region: us-central1
Status: ✅ Deployed
Last Updated: 2026-06-26
```

### Frontend (Cloud Run)
```
URL: https://technical-support-frontend-255507724672.us-central1.run.app
Region: us-central1
Backend: https://technical-support-backend-255507724672.us-central1.run.app
Status: ✅ Deployed
Last Updated: 2026-06-26
```

## 📡 API Endpoints

```bash
# Health Check
GET /health

# Ask Question
POST /api/question
Body: {"question": "your question"}

# System Status
GET /api/status

# Ingest Documents
POST /api/ingest
```

## 🧪 Testing

```bash
# Quick health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/api/question \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Python?"}'

# Run test suite
cd backend && python test_backend.py
```

## 🐳 Docker Commands

```bash
# Build backend (Dockerfile in deployment/ subdirectory)
cd backend && docker build -f deployment/Dockerfile -t backend .

# Run backend
cd backend && docker run -p 8000:8000 --env-file .env backend

# Build frontend
cd frontend && docker build -t frontend .

# Run frontend
cd frontend && docker run -p 8080:8080 -e API_HOST=http://localhost:8000 frontend
```

## ☁️ GCP Commands

```bash
# Enable APIs
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com

# Grant Cloud Build permissions (first-time only)
PROJECT_NUM=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member=serviceAccount:${PROJECT_NUM}@cloudbuild.gserviceaccount.com \
  --role=roles/storage.admin
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member=serviceAccount:${PROJECT_NUM}@cloudbuild.gserviceaccount.com \
  --role=roles/artifactregistry.writer

# Create bucket
gsutil mb -l us-central1 gs://BUCKET_NAME

# Upload PDFs
gsutil cp *.pdf gs://BUCKET_NAME/

# Store secret
echo -n "KEY" | gcloud secrets create SECRET_NAME --data-file=-

# View logs
gcloud run services logs read SERVICE_NAME --limit 50

# Get service URL
gcloud run services describe SERVICE_NAME --format 'value(status.url)'
```

## 🔧 Common Tasks

### First Time Setup
1. Get API keys (Google AI, Tavily)
2. Create GCP project
3. Run `./setup.sh`
4. Edit `backend/.env`
5. Upload PDFs to GCS
6. Start backend
7. Run ingestion: `curl -X POST http://localhost:8000/api/ingest`
8. Start frontend

### Adding Documents
```bash
# Upload to GCS
gsutil cp new-doc.pdf gs://BUCKET_NAME/

# Re-ingest
curl -X POST http://localhost:8000/api/ingest
```

### Updating Agents
1. Edit files in `backend/agents/`
2. Restart backend
3. Test changes

### Viewing Logs
```bash
# Local: Check terminal output

# Cloud Run:
gcloud run services logs read technical-support-backend
```

## 📁 File Locations

```
Configuration:     backend/.env
Agents:           backend/agents/*.py
Backend App:      backend/main.py
Frontend App:     frontend/app.py
Tests:           backend/test_backend.py
Docs:            *.md files
```

## 🆘 Troubleshooting Quick Fixes

```bash
# Backend won't start
# → Check .env file exists and has all keys

# No documents found
# → Run: curl -X POST http://localhost:8000/api/ingest

# Connection refused
# → Verify backend is running: curl http://localhost:8000/health

# Permission errors in GCP
# → Grant service account roles (see GETTING_STARTED.md)

# Slow responses
# → Normal for first request (cold start)

# Embeddings cache issues
# → Delete cache: rm /tmp/embeddings_cache.pkl
```

## 🔗 Important Links

- Google AI Studio: https://aistudio.google.com/
- Tavily: https://tavily.com/
- GCP Console: https://console.cloud.google.com/
- Documentation: See *.md files in project

## 📊 Default Ports

- Backend: 8000
- Frontend: 8501 (local) / 8080 (Docker)

## 🎯 Architecture Summary

```
User → Streamlit UI → FastAPI Backend
                         ↓
                   Orchestrator Agent
                    ↙          ↘
          Researcher        (Direct)
          (Tavily + RAG)      ↓
                    ↘        ↙
                   Reviewer Agent
                         ↓
                    Final Answer
```

## 💡 Pro Tips

1. **First request is slow** - Agents initialize lazily (normal)
2. **Cache embeddings** - Already done in `/tmp/`
3. **Use Flash model** - Faster and cheaper than Pro
4. **Parallel searches** - RAG + Web run in parallel
5. **Quality threshold** - Reviewer improves if score < 0.7
6. **Batch PDFs** - Upload multiple PDFs before ingesting
7. **Monitor costs** - Check GCP billing regularly
8. **Test locally first** - Cheaper and faster iteration

## 📚 Documentation Map

- **New user?** → GETTING_STARTED.md
- **Deploying?** → backend/README.md, DEPLOYMENT.md  
- **Understanding system?** → ARCHITECTURE.md
- **Quick overview?** → README.md
- **Complete details?** → PROJECT_SUMMARY.md

## 🎓 Learning Path

1. Read README.md (5 min)
2. Run setup.sh (5 min)
3. Start locally (10 min)
4. Test with UI (5 min)
5. Read ARCHITECTURE.md (15 min)
6. Customize agents (30 min)
7. Deploy to Cloud Run (30 min)

Total: ~90 minutes to production deployment!
