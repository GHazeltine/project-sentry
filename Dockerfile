FROM python:3.11-slim

# 1. Install System Dependencies
# 'cifs-utils' is REQUIRED for mounting SMB shares from the Web UI
# 'util-linux' provides lsblk for drive detection
RUN apt-get update && apt-get install -y \
    util-linux \
    cifs-utils \
    iputils-ping \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Python Dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    jinja2 \
    python-multipart \
    requests \
    pillow \
    numpy \
    sqlmodel

# 3. Copy Application Code
COPY . .

# 4. Environment Variables
ENV SENTRY_DB_PATH="/data/sentry.db"

# 5. Expose Web Port
EXPOSE 8000

# 6. Start the One Control Center
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
