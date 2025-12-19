import os
import sys
import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
from fastapi import Query


# 1. FIX PATHS FOR DOCKER
# This tells Python to look in both the root and the /app folder for modules
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
if os.path.exists(os.path.join(BASE_DIR, "app")):
    sys.path.append(os.path.join(BASE_DIR, "app"))

# 2. CONNECT TO BACKEND ENGINES
try:
    from app.core.drive_manager import DriveManager
    from app.workers.scanner import run_scanner
    from app.core.janitor import Janitor
except ImportError:
    # Fallback for when we are already inside the /app directory
    from core.drive_manager import DriveManager
    from workers.scanner import run_scanner
    from core.janitor import Janitor

app = FastAPI()

# 3. SETUP STATIC & TEMPLATE PATHS
# We check multiple possible locations to prevent 404/Crash
static_search_paths = [
    os.path.join(BASE_DIR, "static"),
    os.path.join(BASE_DIR, "app", "static")
]
for path in static_search_paths:
    if os.path.exists(path):
        app.mount("/static", StaticFiles(directory=path), name="static")
        break

template_search_paths = [
    os.path.join(BASE_DIR, "app", "templates"),
    os.path.join(BASE_DIR, "templates")
]
templates = None
for path in template_search_paths:
    if os.path.exists(path):
        templates = Jinja2Templates(directory=path)
        break

# Initialize Engines
dm = DriveManager()
janitor = Janitor()

# 4. API ROUTES
@app.get("/")
async def index(request: Request):
    """Renders the Dashboard"""
    drives = dm.detect_drives()
    if templates:
        return templates.TemplateResponse("index.html", {"request": request, "drives": drives})
    return JSONResponse({"error": "Templates folder not found"}, status_code=500)

@app.get("/api/drives")
async def get_drives():
    """Refreshes the drive list"""
    return dm.detect_drives()

# --- Filesystem Browser API (for Web UI parity with TUI DirectoryTree) ---

BLOCKED_PREFIXES = ("/proc", "/sys", "/dev")

@app.get("/api/fs/list")
async def fs_list(path: str = Query("/", description="Absolute path to list")):
    """
    Lists directories (and files) at a given path.
    Intended for building a web-based directory tree selector.
    """
    try:
        # Normalize path safely
        p = Path(path).expanduser()
        p_str = str(p)

        # Block dangerous/virtual filesystem areas
        if any(p_str == bp or p_str.startswith(bp + "/") for bp in BLOCKED_PREFIXES):
            return JSONResponse({"error": "Path is not allowed."}, status_code=403)

        # Enforce absolute paths (keeps behavior predictable inside container)
        if not p.is_absolute():
            return JSONResponse({"error": "Path must be absolute."}, status_code=400)

        if not p.exists():
            return JSONResponse({"error": "Path does not exist."}, status_code=404)

        if not p.is_dir():
            return JSONResponse({"error": "Path is not a directory."}, status_code=400)

        entries = []
        # List children; sort: directories first, then files
        children = list(p.iterdir())
        children.sort(key=lambda c: (not c.is_dir(), c.name.lower()))

        for c in children:
            # Skip extremely noisy pseudo entries
            name = c.name
            c_path = str(c)
            entries.append({
                "name": name,
                "path": c_path,
                "type": "dir" if c.is_dir() else "file",
            })

        parent = str(p.parent) if str(p) != "/" else "/"

        return {
            "path": str(p),
            "parent": parent,
            "entries": entries
        }

    except PermissionError:
        return JSONResponse({"error": "Permission denied."}, status_code=403)
    except Exception as e:
        return JSONResponse({"error": f"Unhandled error: {e}"}, status_code=500)

@app.post("/api/scan")
async def start_scan(request: Request):
    """Triggers the Scanner Engine"""
    data = await request.json()
    targets = data.get('targets', [])
    run_scanner(targets)
    return {"status": "Scan Complete", "message": "Indexing finished."}

if __name__ == "__main__":
    print(f"🚀 Sentry Server starting from: {BASE_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
