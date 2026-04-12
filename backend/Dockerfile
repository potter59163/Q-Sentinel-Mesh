FROM python:3.11-slim

WORKDIR /app

# System deps for scipy, nibabel, Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 gcc g++ libglib2.0-0 libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire repo (backend/ + src/ + weights/ + results/)
# Build context must be repo root: docker build -f backend/Dockerfile .
COPY . .

# Set working dir to backend/ so main.py is found
WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--timeout-keep-alive", "300", "--log-level", "info"]
