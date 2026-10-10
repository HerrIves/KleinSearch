# Official Microsoft Playwright image with Python and Chromium dependencies
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

# Prevent Python from writing .pyc files & enable immediate log output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SCAN_INTERVAL_MINUTES=60

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/
COPY pyproject.toml .

# Create data directory for volume mapping
RUN mkdir -p /app/data

# Persist user data (config.json, listings.csv, notified_ids.json, browser profile)
VOLUME ["/app/data"]

# Default entrypoint: continuous background scanning every 60 minutes
CMD ["python", "src/main.py", "--no-ui", "--loop", "60"]
