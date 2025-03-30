#!/bin/sh
# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
BLUEPRINT_NAME="echocraft"
BLUEPRINTS_SOURCE_DIR="/app/blueprints"
CONFIG_PATH="/app/swarm_config.json"
PORT=${PORT:-8000} # Get port from env
SQLITE_DB_PATH=${SQLITE_DB_PATH:-/app/db.sqlite3}

echo "--- Docker Override Entrypoint: Starting Setup ---"

# --- Ensure .local/bin is in PATH ---
export PATH=$HOME/.local/bin:$PATH
echo "PATH set to: $PATH"

# --- Add Blueprint using swarm-cli ---
echo "Adding blueprint '$BLUEPRINT_NAME' from '$BLUEPRINTS_SOURCE_DIR/$BLUEPRINT_NAME' using config '$CONFIG_PATH'..."
swarm-cli --config-path "$CONFIG_PATH" add "$BLUEPRINTS_SOURCE_DIR/$BLUEPRINT_NAME" --name "$BLUEPRINT_NAME"
echo "Blueprint '$BLUEPRINT_NAME' added."

# --- Install Blueprint Launcher using swarm-cli ---
echo "Installing launcher for blueprint '$BLUEPRINT_NAME' using config '$CONFIG_PATH'..."
swarm-cli --config-path "$CONFIG_PATH" install "$BLUEPRINT_NAME"
echo "Launcher for '$BLUEPRINT_NAME' installed."

# --- (Optional) Test Launcher ---
LAUNCHER_PATH="$HOME/.local/bin/$BLUEPRINT_NAME"
if [ -x "$LAUNCHER_PATH" ]; then
    echo "Testing launcher '$LAUNCHER_PATH'..."
    "$LAUNCHER_PATH" --help || echo "Launcher test command failed (continuing...)"
    echo "Launcher test finished."
else
    echo "WARNING: Launcher '$LAUNCHER_PATH' not found or not executable."
fi

# --- Database Migration Logic (Copied from original Dockerfile CMD) ---
echo "Running database checks and migrations..."
mkdir -p "$(dirname "$SQLITE_DB_PATH")"
if [ "$FACTORY_RESET_DATABASE" = "True" ]; then
  echo "FACTORY_RESET_DATABASE is True; deleting database file if it exists"
  rm -f "$SQLITE_DB_PATH"
fi
if [ -f "$SQLITE_DB_PATH" ]; then
  TABLE_COUNT=$(sqlite3 "$SQLITE_DB_PATH" "SELECT count(*) FROM sqlite_master WHERE type='table';")
  if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "Database exists with tables; applying migrations with --fake-initial if needed"
    python manage.py migrate --fake-initial
  else
    echo "Database exists but is empty; applying migrations normally"
    python manage.py migrate
  fi
else
  echo "No database found; creating and applying migrations"
  python manage.py migrate
fi
echo "Database migrations complete."

# --- Start the main application (Django server) ---
echo "--- Docker Override Entrypoint: Setup Complete ---"
echo "Executing Django runserver on 0.0.0.0:$PORT..."
# Execute the default command (Django server)
exec python manage.py runserver 0.0.0.0:$PORT

