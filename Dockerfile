FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y util-linux ntfs-3g && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi uvicorn python-multipart jinja2
COPY . .
EXPOSE 8000
CMD ["python", "server.py"]
