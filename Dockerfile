FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
# Use PORT 7860 for Hugging Face Spaces, 8050 for local development
# The application will check for HF_SPACE environment variable to determine the environment
ENV PORT=8050
ENV HF_SPACE=1
# No need to set LOG_LEVEL as it will be determined from folio.yaml based on environment
# Note: Sensitive environment variables like GEMINI_API_KEY should be passed at runtime
# rather than build time for security reasons

# Flag to install development dependencies
ARG INSTALL_DEV=false

# Install only the necessary system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .
COPY requirements-dev.txt .

# Install required packages
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_DEV" = "true" ]; then \
    echo "Installing development dependencies..." && \
    pip install --no-cache-dir -r requirements-dev.txt; \
    fi

# Copy all necessary application code
COPY src ./src
COPY config ./config

# Expose both ports (7860 for Hugging Face, 8050 for local)
EXPOSE 7860 8050

# Run the application with Gunicorn for production deployment
# The command will determine the correct port based on environment
CMD ["sh", "-c", "if [ -n \"$HF_SPACE\" ]; then PORT=7860; fi && gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 src.folio.app:server"]
