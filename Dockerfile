# Use Python 3.12 slim image
FROM python:3.12-slim
# Set work directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy application code
COPY . .

# Run migrations, setup defaults and collect static files
RUN uv sync
RUN uv run python manage.py migrate

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the Django development server
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]