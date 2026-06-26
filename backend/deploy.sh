#!/bin/bash
# Deploy backend to Google Cloud Run

set -e

# Configuration
SERVICE_NAME="technical-support-backend"
REGION="us-central1"
PLATFORM="managed"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No GCP project is set. Run 'gcloud config set project PROJECT_ID'"
    exit 1
fi

echo "Deploying $SERVICE_NAME to project: $PROJECT_ID"

# Check and grant Cloud Build permissions if needed
echo "Checking Cloud Build permissions..."
PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
echo "Note: If this is your first deployment, Cloud Build needs permissions."
echo "Run these commands if the build fails with permission errors:"
echo "  gcloud projects add-iam-policy-binding $PROJECT_ID \\"
echo "    --member=serviceAccount:${PROJECT_NUM}@cloudbuild.gserviceaccount.com \\"
echo "    --role=roles/storage.admin"
echo "  gcloud projects add-iam-policy-binding $PROJECT_ID \\"
echo "    --member=serviceAccount:${PROJECT_NUM}@cloudbuild.gserviceaccount.com \\"
echo "    --role=roles/artifactregistry.writer"
echo ""

# Build and push to Google Container Registry
echo "Building container image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME .

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform $PLATFORM \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID" \
    --set-env-vars "VERTEX_AI_LOCATION=$REGION" \
    --set-secrets "GOOGLE_API_KEY=google-api-key:latest" \
    --set-secrets "TAVILY_API_KEY=tavily-api-key:latest" \
    --set-secrets "GCS_BUCKET_NAME=gcs-bucket-name:latest"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform $PLATFORM --region $REGION --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "Service URL: $SERVICE_URL"
echo ""
echo "Test the deployment:"
echo "curl $SERVICE_URL/health"
