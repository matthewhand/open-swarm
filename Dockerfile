FROM python:3.11-slim

# Build-time argument for runtime port (default: 8000)
ARG PORT=8000
ENV PORT=${PORT}

# Install system-level build dependencies, including sqlite3
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    libopenblas-dev \
    liblapack-dev \
    sqlite3 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all project files first (consider .dockerignore for efficiency)
COPY . .

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Install BLIS (if still needed, uncomment)
# ENV BLIS_ARCH="generic"
# RUN pip install --no-cache-dir --no-binary=blis blis==1.2.0

# Install the project
RUN pip install .

# Expose the specified port
EXPOSE ${PORT}

# --- Default Command ---
# This runs if no entrypoint overrides it. Includes DB setup.
CMD if [ -n "$SWAPFILE_PATH" ]; then \
      mkdir -p "$(dirname "$SWAPFILE_PATH")" && \
      fallocate -l 768M "$SWAPFILE_PATH" && \
      chmod 600 "$SWAPFILE_PATH" && \
      mkswap "$SWAPFILE_PATH" && \
      swapon "$SWAPFILE_PATH"; \
    fi && \
    : "${DJANGO_DB_NAME:=${SQLITE_DB_PATH:-/app/db.sqlite3}}" && \
    export DJANGO_DB_NAME SQLITE_DB_PATH="${DJANGO_DB_NAME}" && \
    mkdir -p "$(dirname "$DJANGO_DB_NAME")" && \
    if [ "$FACTORY_RESET_DATABASE" = "True" ]; then \
      echo "FACTORY_RESET_DATABASE is True; deleting database file if it exists" && \
      rm -f "$DJANGO_DB_NAME"; \
    fi && \
    if [ -f "$DJANGO_DB_NAME" ]; then \
      TABLE_COUNT=$(sqlite3 "$DJANGO_DB_NAME" "SELECT count(*) FROM sqlite_master WHERE type='table';") && \
      if [ "$TABLE_COUNT" -gt 0 ]; then \
        echo "Database exists with tables; applying migrations with --fake-initial if needed" && \
        python manage.py migrate --fake-initial; \
      else \
        echo "Database exists but is empty; applying migrations normally" && \
        python manage.py migrate; \
      fi; \
    else \
      echo "No database found; creating and applying migrations" && \
      python manage.py migrate; \
    fi && \
    echo "--- Starting Open Swarm ASGI (uvicorn) ---" && \
    exec uvicorn swarm.asgi:application --host 0.0.0.0 --port "$PORT" --workers "${SWARM_UVICORN_WORKERS:-1}"

