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

# Copy all project files into the container
COPY . .

# Upgrade pip to the latest version for compatibility
RUN pip install --upgrade pip setuptools wheel

# Install BLIS with generic architecture support
ENV BLIS_ARCH="generic"
#RUN pip install --no-cache-dir --no-binary=blis blis==1.2.0
# RUN pip install --no-cache-dir --no-dependencies nemoguardrails

# Install the project along with its dependencies using Hatchling (as set in pyproject.toml)
RUN pip install .

# Expose the specified port
EXPOSE ${PORT}

# Runtime logic:
# - If SWAPFILE_PATH is defined, configure swap
# - Set default SQLite DB path if not provided
# - If FACTORY_RESET_DATABASE is True, delete the database file
# - Check if database exists and has tables; apply migrations accordingly
# - Start the Django server
CMD if [ -n "$SWAPFILE_PATH" ]; then \
      mkdir -p "$(dirname "$SWAPFILE_PATH")" && \
      fallocate -l 768M "$SWAPFILE_PATH" && \
      chmod 600 "$SWAPFILE_PATH" && \
      mkswap "$SWAPFILE_PATH" && \
      swapon "$SWAPFILE_PATH"; \
    fi && \
    : "${SQLITE_DB_PATH:=/app/db.sqlite3}" && \
    mkdir -p "$(dirname "$SQLITE_DB_PATH")" && \
    if [ "$FACTORY_RESET_DATABASE" = "True" ]; then \
      echo "FACTORY_RESET_DATABASE is True; deleting database file if it exists" && \
      rm -f "$SQLITE_DB_PATH"; \
    fi && \
    if [ -f "$SQLITE_DB_PATH" ]; then \
      TABLE_COUNT=$(sqlite3 "$SQLITE_DB_PATH" "SELECT count(*) FROM sqlite_master WHERE type='table';") && \
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
    python manage.py runserver 0.0.0.0:$PORT