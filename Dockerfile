FROM python:3.11-slim

WORKDIR /app

# 1. Install System Dependencies
# 'libgl1' fixes the graphics error.
# 'libcamera-tools' & 'v4l-utils' for IMX500 and USB Webcams.
# 'cifs-utils' allows the container to mount Windows/Network drives.
# 'pciutils' & 'usbutils' for hardware scanning (Hailo/NVIDIA).
RUN apt-get update && apt-get install -y \
    util-linux \
    ntfs-3g \
    cifs-utils \
    libgl1 \
    libglib2.0-0 \
    libcamera-tools \
    v4l-utils \
    pciutils \
    usbutils \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Dependencies
# Added 'textual' for the TUI and 'sqlmodel' for the resume-capable database.
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    jinja2 \
    Pillow \
    numpy \
    opencv-python-headless \
    textual \
    sqlmodel

COPY . .

# Expose the Dashboard port
EXPOSE 8000

# 3. Launch Command
# Note: We keep server.py as the CMD so the container stays alive, 
# but you will 'exec' into it to use the TUI.
# Launch the unified interface
CMD ["python", "app/tui/main.py"]
