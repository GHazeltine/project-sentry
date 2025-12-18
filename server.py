import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# --- CONNECTING TO YOUR v2.0 BACKEND ---
# We use absolute imports to avoid Docker pathing issues
try:
    from app.core.drive_manager import DriveManager
    from app.workers.scanner import run_scanner
    from app.core.janitor import Janitor
except ImportError:
    from core.drive_manager import DriveManager
    from workers.scanner import run_scanner
    from core.janitor import Janitor

# 1. SETUP ABSOLUTE PATHING
# This prevents the "Directory does not exist" crash
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# Mount Static Files (Looking in root first, then app/static)
static_path = os.path.join(BASE_DIR, "static")
if not os.path.exists(static_path):
    static_path = os.path.join(BASE_DIR, "app", "static")

if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Setup Templates (Looking in app/templates)
templates_path = os.path.join(BASE_DIR, "app", "templates")
if not os.path.exists(templates_path):
    templates_path = os.path.join(BASE_DIR, "templates")

templates = Jinja2Templates(directory=templates_path)

# Initialize Engines
dm = DriveManager()
janitor = Janitor()

@app.get("/")
async def index(request: Request):
    """Renders the Dashboard"""
    drives = dm.detect_drives()
    return templates.TemplateResponse("index.html", {"request": request, "drives": drives})

@app.get("/api/drives")
async def get_drives():
    """Refreshes the drive list"""
    return dm.detect_drives()

@app.post("/api/scan")
async def start_scan(request: Request):
    """Triggers the Scanner Engine"""
    data = await request.json()
    targets = data.get('targets', [])
    
    # Offload to the verified scanner worker
    run_scanner(targets)
    return {"status": "Scan Complete", "message": "Indexing finished."}

if __name__ == "__main__":
    # Unified Launch configuration
    uvicorn.run(app, host="0.0.0.0", port=8000)
