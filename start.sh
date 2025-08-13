#!/bin/bash

echo "Starting ContextLens Django application..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first."
    echo "Visit: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Sync dependencies
echo "Installing dependencies with uv..."
uv sync

# Run database migrations
echo "Running database migrations..."
uv run python manage.py migrate

echo "Starting Django development server..."
echo "Access the application at: http://0.0.0.0:8000"
uv run python manage.py runserver 0.0.0.0:8000