FROM python:3.11-slim

# 1. Install System Dependencies
# 'cifs-utils' for SMB, 'util-linux' for lsblk, 'libgl1' for AI/Image processing
RUN apt-get update && apt-get install -y \
    util-linux \
    cifs-utils \
    iputils-ping \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Copy the Shopping List first (Better Docker Caching)
COPY requirements.txt .

# 3. Install Python Dependencies from the list
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Application Code
COPY . .

# 5. Environment Variables
ENV SENTRY_DB_PATH="/data/sentry.db"

# 6. Expose Web Port
EXPOSE 8000

# 7. Start the One Control Center
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
