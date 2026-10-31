#!/usr/bin/env bash
set -e

# Configuration
SERVICE_NAME="varanasi-scraper"
REGION="asia-south1"       # Mumbai, India (Lowest latency for Indian Google Maps)
MEMORY="2Gi"               # 2GB RAM for Chromium Headless
CPU="2"
TIMEOUT="1800s"            # 30-minute timeout for multi-locality scraping

echo "=========================================================="
echo " Deploying Varanasi Shop Scraper to Google Cloud Run"
echo "=========================================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: 'gcloud' CLI is not installed or not in PATH."
    echo "Please install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project 2> /dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "No Google Cloud project set. Please set a project:"
    echo "  gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Project ID: $PROJECT_ID"
echo "Region:     $REGION"
echo "Service:    $SERVICE_NAME"
echo ""

# Enable required Google Cloud APIs if not already enabled
echo "Enabling Cloud Run and Cloud Build APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy directly using source (Cloud Build builds the Dockerfile)
echo "Deploying container to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --platform managed \
    --memory "$MEMORY" \
    --cpu "$CPU" \
    --timeout "$TIMEOUT" \
    --allow-unauthenticated

echo ""
echo "=========================================================="
echo " Deployment Complete!"
echo " Your dashboard URL is listed above."
echo "=========================================================="
