# Official Playwright Python image with Chromium & all OS dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY . .

# Create downloads directory
RUN mkdir -p downloads

EXPOSE 8080

# Run the FastAPI server on Cloud Run's dynamic PORT
CMD ["python", "server.py"]

