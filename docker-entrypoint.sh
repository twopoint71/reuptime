#!/bin/bash
set -e

# Wait for database to be ready (if using PostgreSQL)
# while ! nc -z $DB_HOST $DB_PORT; do
#   echo "Waiting for database..."
#   sleep 1
# done

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Start Gunicorn
exec "$@"
