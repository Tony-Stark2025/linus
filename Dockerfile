# Dockerfile for Linus Enterprise SRE Console
# Target Platform: Amazon ECS Express Mode / AWS ECS Fargate / Bedrock AgentCore Runtime
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    AWS_DEFAULT_REGION=us-east-1

WORKDIR /app

# Install system dependencies (git for unified diffs, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project specification & dependencies
COPY pyproject.toml .
COPY linus/ linus/
COPY web_demo/ web_demo/
COPY tests/ tests/
COPY agentcore.yaml .
COPY LICENSE .
COPY README.md .

# Install Python dependencies and linus package
RUN pip install --no-cache-dir -e .

# Expose web console port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run Linus Enterprise SRE Console
CMD ["python", "-m", "uvicorn", "web_demo.server:app", "--host", "0.0.0.0", "--port", "8000"]
