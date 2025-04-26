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
    apt-get install -y --no-install-recommends gcc curl && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_CREATE=false
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# Copy only what's needed for dependency installation
COPY pyproject.toml poetry.lock* ./

# Install dependencies with --no-root to skip installing the current project
RUN if [ "$INSTALL_DEV" = "true" ]; then \
    echo "Installing with development dependencies..." && \
    poetry install --no-interaction --no-ansi --no-root; \
    else \
    echo "Installing without development dependencies..." && \
    poetry install --no-interaction --no-ansi --only main --no-root; \
    fi

# Copy only the application code
COPY src ./src

# Expose both ports (7860 for Hugging Face, 8050 for local)
EXPOSE 7860 8050

# Run the application with Gunicorn for production deployment
# The command will determine the correct port based on environment
# Note: Huggingface must use port 7860
CMD ["sh", "-c", "if [ -n \"$HF_SPACE\" ]; then PORT=7860; fi && gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 src.folio.app:server"]
