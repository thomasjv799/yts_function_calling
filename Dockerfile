FROM python:3.11-slim

# Install system deps including pre-built libtorrent bindings
# (avoids compiling from source which takes 20+ minutes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-libtorrent \
    && rm -rf /var/lib/apt/lists/*

# Make the system libtorrent .so accessible to the Docker Python interpreter
RUN echo "/usr/lib/python3/dist-packages" \
    > /usr/local/lib/python3.11/site-packages/system-dist.pth

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies (libtorrent excluded — handled above)
COPY requirements.txt .
RUN grep -v "^libtorrent" requirements.txt > requirements-docker.txt \
    && uv pip install --system --no-cache -r requirements-docker.txt \
    && rm requirements-docker.txt

# Copy application code
COPY . .

CMD ["python", "main.py"]
