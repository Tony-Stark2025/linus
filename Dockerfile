# Dockerfile for Linus Enterprise SRE Console
# Target Platform: AWS Lambda Serverless (via Lambda Web Adapter) / Amazon ECS / Bedrock AgentCore
FROM python:3.12-slim

# Copy AWS Lambda Web Adapter (enables FastAPI/Uvicorn to run on AWS Lambda serverless with response streaming)
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    AWS_LWA_PORT=8000 \
    AWS_LWA_INVOKE_MODE=response_stream \
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

# Create non-root execution user and writable temporary directories for sandbox & regressions (SEC-01)
RUN useradd -m -u 1000 -s /bin/bash linus \
    && mkdir -p /tmp/linus_regressions /tmp/linus_audit_store /app/tests/regressions \
    && chown -R linus:linus /app /tmp/linus_regressions /tmp/linus_audit_store

USER linus

# Expose web console port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run Linus Enterprise SRE Console
CMD ["python", "-m", "uvicorn", "web_demo.server:app", "--host", "0.0.0.0", "--port", "8000"]
