# Deployment Guide: Varanasi Shop Scraper UI

This guide covers running the Web Dashboard locally and deploying it to **Google Cloud Run**.

---

## 💻 1. Running the UI Dashboard Locally

To start the dashboard on your local machine:

```bash
cd /Users/shwetasingh/Development/varanasi-shop-website/shop-scrapping
source .venv/bin/activate
python server.py
```

Open your browser and navigate to:
👉 **`http://localhost:8080`**

### What you can do from the UI:
- Select from all **81 Varanasi localities** using search tags or quick-filter buttons (*"Top 10 Markets"*, *"Select All"*, *"Clear"*).
- Choose between **General Sweep** or **Exhaustive Census**.
- Adjust scroll depth.
- Click **"Start Scraping Selected Localities"** to see live streaming progress, real-time counters, and discovered shops.
- Click **"Download Excel (.xlsx)"** to get your spreadsheet with clickable WhatsApp outreach links.

---

## 🐳 2. Testing Locally with Docker

Before deploying to Google Cloud, you can test the containerized version locally:

```bash
# 1. Build the Docker container
docker build -t varanasi-scraper .

# 2. Run the container
docker run -p 8080:8080 varanasi-scraper
```

Open `http://localhost:8080` in your browser.

---

## ☁️ 3. Deploying to Google Cloud Run

**Google Cloud Run** is the recommended hosting platform because:
- **Serverless**: Autoscales down to 0 instances when you are not using it (effectively \$0/month when idle).
- **Headless Browser Support**: Pre-configured with Microsoft's official Playwright Chromium image.
- **Dedicated Resources**: Runs with 2 CPUs and 2 GB of RAM for smooth multi-tab scraping.

### Step-by-Step Deployment:

#### Step 3.1: Install and Authenticate Google Cloud CLI
If you haven't installed `gcloud`, download it from [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) or via Homebrew:
```bash
brew install --cask google-cloud-sdk
```

Authenticate your Google account:
```bash
gcloud auth login
```

#### Step 3.2: Set your Google Cloud Project
```bash
# List your available projects
gcloud projects list

# Set the active project
gcloud config set project YOUR_PROJECT_ID
```

*(Ensure billing is enabled for your project in the Google Cloud Console).*

#### Step 3.3: One-Click Deploy
Run the included deployment script:
```bash
./deploy.sh
```

Alternatively, run the manual `gcloud` deploy command:
```bash
gcloud run deploy varanasi-scraper \
    --source . \
    --region asia-south1 \
    --platform managed \
    --memory 2Gi \
    --cpu 2 \
    --timeout 1800s \
    --allow-unauthenticated
```

### Explanation of Settings:
- `--region asia-south1`: Deploys to Mumbai, India (closest data center to Varanasi for minimum network latency).
- `--memory 2Gi`: Allocates 2GB RAM required by Chromium headless.
- `--cpu 2`: 2 vCPUs for smooth asynchronous parsing.
- `--timeout 1800s`: Extends max HTTP request timeout to **30 minutes** so large locality sweeps finish without timing out.
- `--allow-unauthenticated`: Generates a public HTTPS URL (e.g. `https://varanasi-scraper-xyz-el.a.run.app`) accessible from any browser or smartphone.

---

## 🔒 Notes on Data Persistence in Cloud Run
- Google Cloud Run instances are stateless. When Cloud Run scales down to 0, locally stored files reset.
- However, every time you trigger a scrape from the UI, the generated `.xlsx` file is immediately streamed and available for instant download on the webpage.
- If you need long-term persistent storage of the master SQLite database in the cloud, you can mount a **Google Cloud Storage (GCS) bucket** as a volume or connect to **Cloud SQL**.
