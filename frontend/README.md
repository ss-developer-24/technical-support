# Technical Support Frontend

Streamlit-based user interface for the Technical Support Assistant.

## Overview

This is the frontend application that provides a chat interface for users to interact with the backend agents. It's built with Streamlit and designed to be deployed to Google Cloud Run.

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and set API_HOST to your backend URL

# Run the application
streamlit run app.py
```

The frontend will start at http://localhost:8501

### Configuration

The frontend uses a `.env` file for configuration. Create it from the example:

```bash
cp .env.example .env
```

Then edit `.env` to set your backend URL:

```env
# For local development
API_HOST=http://localhost:8000

# For production (deployed backend)
API_HOST=https://technical-support-backend-255507724672.us-central1.run.app
```

Alternatively, set the environment variable directly:

```bash
# Local development
export API_HOST=http://localhost:8000

# Production
export API_HOST=https://technical-support-backend-255507724672.us-central1.run.app
```

You can also configure the API host through the UI sidebar.

## Docker

### Build

```bash
docker build -t technical-support-frontend .
```

### Run

```bash
docker run -p 8080:8080 \
  -e API_HOST=http://your-backend:8000 \
  technical-support-frontend
```

Access at http://localhost:8080

## Deploy to Google Cloud Run

**Current Deployed Services:**
- **Backend:** https://technical-support-backend-255507724672.us-central1.run.app
- **Frontend:** https://technical-support-frontend-255507724672.us-central1.run.app

### Option 1: Using Cloud Build (Recommended)

```bash
cd frontend
gcloud builds submit --config cloudbuild.yaml
```

This will automatically:
1. Build the Docker image
2. Push to Artifact Registry
3. Deploy to Cloud Run with the configured backend URL

### Option 2: Using Deployment Script

```bash
cd frontend
./deploy.sh technical-support-499903 us-central1 https://technical-support-backend-255507724672.us-central1.run.app
```

### Option 3: Manual Deployment

```bash
# Build and push to Artifact Registry
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/docker-repo/technical-support-frontend .
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/docker-repo/technical-support-frontend

# Deploy to Cloud Run
gcloud run deploy technical-support-frontend \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/docker-repo/technical-support-frontend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --set-env-vars API_HOST=https://technical-support-backend-255507724672.us-central1.run.app
```

### Option 3: Using Deployment Script

```bash
./deploy.sh technical-support-499903 us-central1 https://technical-support-backend-255507724672.us-central1.run.app
```

## Features

- **Chat Interface**: Clean, intuitive chat-based UI
- **Connection Monitoring**: Real-time backend health status
- **Session Management**: Maintains conversation history
- **Error Handling**: Graceful error messages and timeout handling
- **Configuration**: Adjustable API host through UI

## Environment Variables

Configuration is managed through a `.env` file (see `.env.example` for template):

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | Backend API URL | http://localhost:8000 |
| `PORT` | Server port (Cloud Run) | 8080 |

**Note:** For Docker/Cloud Run deployments, environment variables should be passed via `-e` flag or Cloud Run configuration, not through the `.env` file.

## Files

- `app.py` - Main Streamlit application
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration
- `deploy.sh` - Deployment script
- `cloudbuild.yaml` - Cloud Build configuration
- `.dockerignore` - Docker build exclusions
- `.gcloudignore` - Deployment exclusions

## Dependencies

```txt
streamlit==1.31.1
requests==2.31.0
```

## Health Check

The frontend connects to the backend's `/health` endpoint to verify connectivity. Connection status is displayed in the sidebar.

## Troubleshooting

### "Connection failed" error
- Verify backend is running
- Check `API_HOST` environment variable
- Ensure firewall allows connections

### "Request timed out" error
- Backend may be cold starting (normal on first request)
- Check backend logs for errors

### UI not loading
- Verify port 8501 (local) or 8080 (Docker) is not in use
- Check Streamlit logs for errors

## Development

To modify the UI:

1. Edit `app.py`
2. Restart Streamlit (it will auto-reload on save)
3. Test changes locally before deploying

## Related Documentation

- [Main README](../README.md) - Project overview
- [Backend README](../backend/README.md) - Backend documentation
- [Getting Started](../GETTING_STARTED.md) - Complete setup guide
