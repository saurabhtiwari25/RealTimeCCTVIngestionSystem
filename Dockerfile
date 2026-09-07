FROM python:3.11-slim

# Install system dependencies including FFmpeg and OpenGL libraries for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ ./app/
COPY streaming/ ./streaming/
COPY sample_videos/ ./sample_videos/
COPY .streamlit/ ./.streamlit/
COPY .env.example .

# Create recordings directory
RUN mkdir -p /app/recordings

# Set environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose Streamlit port
EXPOSE 8501

# Healthcheck for Streamlit
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start Streamlit application (supports dynamic $PORT for cloud deployment with 8501 fallback)
CMD ["sh", "-c", "streamlit run app/streamlit_app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.fileWatcherType=none"]
