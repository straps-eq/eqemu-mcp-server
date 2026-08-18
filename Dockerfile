FROM python:3.13-slim

# Install ripgrep and git (for auto-cloning docs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ripgrep git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package metadata and application code before installing the project.
COPY pyproject.toml README.md LICENSE server.py ./
COPY eqemu_mcp/ ./eqemu_mcp/
RUN pip install --no-cache-dir .

COPY start.sh ./
RUN chmod +x start.sh

# Default to read-only mode and Streamable HTTP transport.
ENV EQEMU_ACCESS_MODE=read
ENV RG_PATH=/usr/bin/rg

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8888/health', timeout=3)" || exit 1

ENTRYPOINT ["python", "server.py"]
CMD ["--http", "8888"]
