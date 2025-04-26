# Docker Setup for Folio

This document provides instructions for running the Folio application using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your system
- [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

## Quick Start

1. **Create a .env file** (optional)

   Copy the example environment file if you want to customize settings:

   ```bash
   cp .env.example .env
   # Edit .env to customize settings if needed
   ```

   Note: Since we're using yfinance as the default data source, no API keys are required.

2. **Build and run with Docker Compose**

   ```bash
   # Build and start the container in detached mode
   make docker-up
   ```

   After successful startup, you'll see a message with the URL where you can access the application.

3. **Access the application**

   Open your browser and navigate to:

   ```
   http://localhost:8050
   ```

4. **View logs**

   To monitor the application logs in real-time:

   ```bash
   make docker-logs
   ```

   Press Ctrl+C to stop viewing logs.

5. **Stop the application**

   ```bash
   make docker-down
   ```

## Docker Commands Reference

The following Make commands are available for working with Docker:

| Command | Description |
|---------|-------------|
| `make docker-build` | Build the Docker image |
| `make docker-run` | Run the Docker container |
| `make docker-up` | Start the application with docker-compose |
| `make docker-down` | Stop the docker-compose services |
| `make docker-logs` | Tail the Docker logs |
| `make docker-test` | Run tests in a Docker container |

### Manual Docker Commands

If you prefer to use Docker directly without Make:

1. **Build the Docker image**

   ```bash
   docker build -t folio:latest .
   ```

2. **Run the Docker container**

   ```bash
   docker run -p 8050:8050 --env-file .env folio:latest
   ```

3. **Use Docker Compose directly**

   ```bash
   # Start services
   docker-compose up -d

   # View logs
   docker-compose logs -f

   # Stop services
   docker-compose down
   ```

## Troubleshooting

- **Port conflicts**: If port 8050 is already in use, modify the `PORT` environment variable in your `.env` file and update the port mapping in `docker-compose.yml`.

- **Data source**: The application uses yfinance as the data source for stock data.

- **Volume mounting**: If you're making changes to the code and want to see them reflected immediately, ensure the volumes in `docker-compose.yml` are correctly mapping your local directories.

- **Dependencies**: The Docker image uses `requirements.txt` for its dependencies. If you need to add or update dependencies, modify this file instead of editing the Dockerfile directly.

- **Development dependencies**: For development and testing, the Docker image can also install dependencies from `requirements-dev.txt`. These are installed automatically when running `make docker-test`.

- **API Keys**: Sensitive data like API keys should be passed at runtime using environment variables or the `.env` file, not hardcoded in the Dockerfile.

## Testing in Docker

To run tests in a Docker container:

```bash
make docker-test
```

This will build a Docker image with development dependencies and run the test suite inside the container.

## Next Steps

After successfully running the application locally with Docker, you can consider:

1. Setting up CI/CD with GitHub Actions
2. Deploying to a hosting platform like Hugging Face Spaces
3. Implementing additional Docker configurations for production environments
