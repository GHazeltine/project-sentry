FROM python:3.9-slim

# Install system dependencies (ffmpeg for video, libgl1 for cv2, postgres libs)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the API port
EXPOSE 8000

# Start the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
