# Use Python 3.12.9 slim image as base
FROM python:3.12.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=reuptime.settings

# Set work directory
WORKDIR /app

# Install system dependencies including build tools and RRDtool headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    rrdtool \
    librrd-dev \
    build-essential \
    python3-dev \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn whitenoise

# Create instance directory and set permissions
RUN mkdir -p /app/instance && chmod 755 /app/instance

# Copy project files
COPY . .

# Create non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app

# Create staticfiles directory and set permissions
RUN mkdir -p /app/staticfiles && \
    chown -R appuser:appuser /app/staticfiles

# Set up ping permissions
RUN chmod u+s /usr/bin/ping

# Make entrypoint script executable
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
# normal
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "reuptime.wsgi:application"]

# debug
#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--enable-stdio-inheritance",  "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "reuptime.wsgi:application"]
