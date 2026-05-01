FROM python:3.13-slim

# Install ripgrep and git (for auto-cloning docs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ripgrep git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application code
COPY server.py start.sh ./
COPY eqemu_mcp/ ./eqemu_mcp/
RUN chmod +x start.sh

# Default to read-only mode and SSE transport
ENV EQEMU_ACCESS_MODE=read
ENV RG_PATH=/usr/bin/rg

EXPOSE 8888

ENTRYPOINT ["python", "server.py"]
CMD ["--sse", "8888"]
