FROM python:3.11-slim

RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install --no-cache-dir alembic==1.16.5

# Copy backend and frontend source
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x ./entrypoint.sh

# Set working directory to backend where main.py and Alembic live
WORKDIR /app/backend

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
