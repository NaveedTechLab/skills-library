FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy frontend package files and install
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Build frontend
RUN cd frontend && npm run build

# Expose Hugging Face Spaces default port
EXPOSE 7860

# Create startup script
RUN echo '#!/bin/bash\n\
cd /app/backend && uvicorn main:app --host 0.0.0.0 --port 7860 &\n\
cd /app/frontend && npm start -- -p 3000 &\n\
wait' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
