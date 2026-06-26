# Technical Support UI - Streamlit Frontend

A Streamlit-based user interface for technical support that connects to a backend API. Fully containerized and ready for Google Cloud Run deployment.

## Features

- 🔧 **Configurable Backend**: Easy API host configuration through the UI
- 💬 **Chat Interface**: Clean, intuitive chat-based Q&A interface
- 📊 **Connection Status**: Real-time backend health monitoring
- 🐳 **Docker Ready**: Fully containerized for easy deployment
- ☁️ **Cloud Run Optimized**: Configured for Google Cloud Run deployment

## Project Structure

```
.
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
├── .dockerignore      # Docker ignore patterns
└── DEPLOYMENT.md      # This file
```

## Local Development

### Prerequisites

- Python 3.11+
- pip

### Setup

1. Navigate to frontend directory and install dependencies:
```bash
cd frontend
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run app.py
```

3. Access the UI at `http://localhost:8501`

### Environment Variables

Configuration is managed through a `.env` file for local development:

1. Create `.env` from template:
```bash
cp .env.example .env
```

2. Edit `.env` with your backend URL:
```env
# Local development
API_HOST=http://localhost:8000

# Production (deployed backend)
API_HOST=https://technical-support-backend-255507724672.us-central1.run.app
```

**Available Variables:**
- `API_HOST`: Backend API URL (required)
  - Local: `http://localhost:8000`
  - Production: `https://technical-support-backend-255507724672.us-central1.run.app`

**Note:** The `.env` file is only used for local development. For Docker/Cloud Run deployments, pass environment variables directly (see Docker and Cloud Run sections).

## Docker Deployment

### Build the Docker Image

```bash
cd frontend
docker build -t technical-support-frontend .
```

### Run Locally with Docker

```bash
cd frontend
# For local backend
docker run -p 8080:8080 \
  -e API_HOST=http://host.docker.internal:8000 \
  technical-support-frontend

# For production backend
docker run -p 8080:8080 \
  -e API_HOST=https://technical-support-backend-255507724672.us-central1.run.app \
  technical-support-frontend
```

Access the UI at `http://localhost:8080`

## Google Cloud Run Deployment

### Deployed Services

- **Backend:** https://technical-support-backend-255507724672.us-central1.run.app
- **Frontend:** https://technical-support-frontend-255507724672.us-central1.run.app
- **Region:** us-central1
- **Project:** technical-support-499903

### Prerequisites

- Google Cloud SDK installed and configured
- Google Cloud project with Cloud Run API enabled
- Docker installed locally

### Deployment Steps

#### 1. Authenticate with Google Cloud

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

#### 2. Configure Docker for Google Container Registry

```bash
gcloud auth configure-docker
```

#### 3. Build and Tag the Image

```bash
cd frontend

# Build the image
docker build -t gcr.io/YOUR_PROJECT_ID/technical-support-frontend:latest .

# Push to Google Container Registry
docker push gcr.io/YOUR_PROJECT_ID/technical-support-frontend:latest
```

#### 4. Deploy to Cloud Run

```bash
gcloud run deploy technical-support-frontend \
  --image gcr.io/YOUR_PROJECT_ID/technical-support-frontend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars API_HOST=https://your-backend-api.com \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 0
```

#### 5. Get the Service URL

```bash
gcloud run services describe technical-support-frontend \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)'
```

### Alternative: Using Cloud Build

The project includes a `cloudbuild.yaml` file for automated deployment.

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
cd frontend
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_API_HOST=https://your-backend-url.run.app
```

**Note:** The `cloudbuild.yaml` uses `$BUILD_ID` for image tagging, which works for both manual builds and automated triggers.

## Backend API Requirements

The backend API should expose the following endpoints:

### Health Check
```
GET /health
Response: 200 OK
```

### Question Endpoint
```
POST /api/question
Content-Type: application/json

Request Body:
{
  "question": "Your question here"
}

Response:
{
  "answer": "The response from the backend"
}
```

## Configuration

### Updating API Host

Users can configure the backend API host in two ways:

1. **Through the UI**: Use the sidebar configuration panel
2. **Environment Variable**: Set `API_HOST` when deploying

### Customization

#### Change Port

Modify the `PORT` environment variable in the Dockerfile or when running:

```bash
docker run -p 8080:8080 -e PORT=8080 technical-support-frontend
```

#### Adjust Memory/CPU for Cloud Run

Use the `--memory` and `--cpu` flags during deployment:

```bash
gcloud run deploy technical-support-frontend \
  --memory 1Gi \
  --cpu 2
```

## Monitoring and Logs

### View Cloud Run Logs

```bash
gcloud run logs read technical-support-frontend \
  --region us-central1 \
  --limit 100
```

### Stream Logs

```bash
gcloud run logs tail technical-support-frontend \
  --region us-central1
```

## Cost Optimization

Cloud Run charges based on:
- Request count
- CPU and memory usage
- Networking

To optimize costs:
- Use `--min-instances 0` for automatic scaling to zero
- Adjust `--memory` and `--cpu` based on actual needs
- Set `--max-instances` to control maximum concurrency

## Security Considerations

1. **Authentication**: Consider adding Cloud Run authentication for production:
   ```bash
   # Remove --allow-unauthenticated flag
   gcloud run deploy technical-support-frontend \
     --image gcr.io/YOUR_PROJECT_ID/technical-support-frontend:latest \
     --no-allow-unauthenticated
   ```

2. **CORS**: Configured to be disabled by default; adjust if needed

3. **XSRF Protection**: Enabled by default in Streamlit configuration

4. **Environment Variables**: Use Secret Manager for sensitive configuration:
   ```bash
   gcloud run deploy technical-support-frontend \
     --set-secrets API_KEY=api-key:latest
   ```

## Troubleshooting

### Container doesn't start
- Check logs: `gcloud run logs read technical-support-frontend`
- Verify PORT is set to 8080 (Cloud Run default)
- Ensure health check endpoint is accessible

### Can't connect to backend
- Verify API_HOST environment variable is set correctly
- Check backend API is accessible from Cloud Run
- Review firewall rules if backend is on private network

### High latency
- Consider deploying frontend and backend in same region
- Increase memory/CPU allocation
- Enable Cloud Run's request/response caching

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify backend API is operational
3. Ensure all environment variables are correctly set

## License

[Your License Here]
