#!/bin/bash

# Deployment script for Google Cloud Run
# Usage: ./deploy.sh [PROJECT_ID] [REGION] [API_HOST]

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_REGION="us-central1"
DEFAULT_API_HOST="https://technical-support-backend-255507724672.us-central1.run.app"
SERVICE_NAME="technical-support-frontend"

# Parse arguments
PROJECT_ID="${1}"
REGION="${2:-$DEFAULT_REGION}"
API_HOST="${3:-$DEFAULT_API_HOST}"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate prerequisites
print_info "Validating prerequisites..."

if ! command_exists gcloud; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

if ! command_exists docker; then
    print_error "Docker is not installed. Please install it first."
    exit 1
fi

# Get or validate project ID
if [ -z "$PROJECT_ID" ]; then
    print_info "No project ID provided. Using current gcloud project..."
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    
    if [ -z "$PROJECT_ID" ]; then
        print_error "No project ID found. Please provide one as the first argument."
        echo "Usage: ./deploy.sh [PROJECT_ID] [REGION] [API_HOST]"
        exit 1
    fi
fi

print_info "Project ID: $PROJECT_ID"
print_info "Region: $REGION"
print_info "API Host: $API_HOST"
print_info "Service Name: $SERVICE_NAME"

# Confirm deployment
echo ""
read -p "Continue with deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Deployment cancelled."
    exit 0
fi

# Set the project
print_info "Setting gcloud project to $PROJECT_ID..."
gcloud config set project "$PROJECT_ID"

# Enable required APIs
print_info "Ensuring required APIs are enabled..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    --project="$PROJECT_ID" 2>/dev/null || true

# Configure Docker authentication for Artifact Registry
print_info "Configuring Docker authentication for Artifact Registry..."
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

# Build the Docker image
IMAGE_NAME="us-central1-docker.pkg.dev/$PROJECT_ID/docker-repo/$SERVICE_NAME"
IMAGE_TAG="$(date +%Y%m%d-%H%M%S)"
IMAGE_FULL="$IMAGE_NAME:$IMAGE_TAG"
IMAGE_LATEST="$IMAGE_NAME:latest"

print_info "Building Docker image: $IMAGE_FULL..."
docker build -t "$IMAGE_FULL" -t "$IMAGE_LATEST" .

if [ $? -ne 0 ]; then
    print_error "Docker build failed!"
    exit 1
fi

print_success "Docker image built successfully!"

# Push the image to Artifact Registry
print_info "Pushing image to Artifact Registry..."
docker push "$IMAGE_FULL"
docker push "$IMAGE_LATEST"

if [ $? -ne 0 ]; then
    print_error "Docker push failed!"
    exit 1
fi

print_success "Image pushed successfully!"

# Deploy to Cloud Run
print_info "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_FULL" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars "API_HOST=$API_HOST" \
    --project "$PROJECT_ID"

if [ $? -ne 0 ]; then
    print_error "Cloud Run deployment failed!"
    exit 1
fi

print_success "Deployment completed successfully!"

# Get the service URL
print_info "Fetching service URL..."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --format 'value(status.url)' \
    --project "$PROJECT_ID")

echo ""
echo "=================================="
print_success "Deployment Summary"
echo "=================================="
echo "Service Name: $SERVICE_NAME"
echo "Region: $REGION"
echo "Image: $IMAGE_FULL"
echo "API Host: $API_HOST"
echo ""
print_success "Service URL: $SERVICE_URL"
echo "=================================="
echo ""
print_info "You can view logs with:"
echo "  gcloud run logs read $SERVICE_NAME --region $REGION"
echo ""
print_info "You can update the service with:"
echo "  gcloud run services update $SERVICE_NAME --region $REGION"
echo ""
