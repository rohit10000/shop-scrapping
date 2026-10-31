#!/usr/bin/env bash
# Automated Setup Script for Google Cloud Compute Engine VM (Ubuntu / Debian)
set -e

echo "=========================================================="
echo " Setting up Varanasi Shop Scraper on Google Cloud VM"
echo "=========================================================="

# 1. Update system packages
echo "Updating package list..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl ufw

# 2. Set up virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and install Python packages
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install Playwright Chromium and required OS dependencies
echo "Installing Chromium browser and system libraries..."
playwright install --with-deps chromium

# 5. Create downloads folder
mkdir -p downloads

# 6. Configure Systemd Service to keep it running 24/7
APP_DIR=$(pwd)
USER_NAME=$(whoami)

echo "Creating systemd background service..."
sudo bash -c "cat > /etc/systemd/system/varanasi-scraper.service" <<EOF
[Unit]
Description=Varanasi Shop Scraper Dashboard
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/server.py
Restart=always
RestartSec=5
Environment=PORT=8080
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable the service
echo "Starting and enabling varanasi-scraper service..."
sudo systemctl daemon-reload
sudo systemctl enable varanasi-scraper
sudo systemctl restart varanasi-scraper

echo ""
echo "=========================================================="
echo " Setup Finished!"
echo " Service Status:"
sudo systemctl status varanasi-scraper --no-pager
echo "=========================================================="
echo " Next step: Make sure port 8080 is allowed in GCP Firewall!"

