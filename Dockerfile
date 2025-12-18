FROM python:3.11-slim

WORKDIR /app

# 1. Install System Dependencies
# 'libgl1' fixes the graphics error.
# 'libcamera-tools' & 'v4l-utils' allow access to the IMX500 and USB Webcams.
# 'pciutils' & 'usbutils' allow the code to scan for Hardware (Hailo/NVIDIA).
RUN apt-get update && apt-get install -y \
    util-linux \
    ntfs-3g \
    libgl1 \
    libglib2.0-0 \
    libcamera-tools \
    v4l-utils \
    pciutils \
    usbutils \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Dependencies
# 'opencv-python-headless' is the standard for visual processing on any OS.
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    jinja2 \
    Pillow \
    numpy \
    opencv-python-headless

COPY . .

EXPOSE 8000

# 3. Launch Command
CMD ["python", "server.py"]
