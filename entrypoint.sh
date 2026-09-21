#!/usr/bin/env bash
set -e

echo "Waiting for MySQL database to be ready..."
while ! nc -z db 3306; do
  sleep 1
done
echo "MySQL is up and running!"

echo "Running Alembic migrations..."
alembic upgrade head

echo "Seeding initial data if the database is empty..."
python -m seed

echo "Starting FastAPI server..."
exec uvicorn main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}" --reload
