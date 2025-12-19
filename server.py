import os
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlmodel import Session, select
from sqlalchemy import func

# --- Local imports (project) ---
from app.core.drive_manager import DriveManager
from app.workers.janitor import Janitor
from app.workers.scanner import run_scanner
from app.database.models import ScanMission, FileRecord, engine


# --------------------------------------------------------------------
# App init
# --------------------------------------------------------------------
app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------
# Static + Templates (resilient search paths)
# --------------------------------------------------------------------
static_search_paths = [
    os.path.join(BASE_DIR, "static"),
    os.path.join(BASE_DIR, "app", "static"),
]
for p in static_search_paths:
    if os.path.exists(p):
        app.mount("/static", StaticFiles(directory=p), name="static")
        break

template_search_paths = [
    os.path.join(BASE_DIR, "app", "templates"),
    os.path.join(BASE_DIR, "templates"),
]
templates = None
for p in template_search_paths:
    if os.path.exists(p):
        templates = Jinja2Templates(directory=p)
        break

if templates is None:
    raise RuntimeError("Templates directory not found. Checked: " + ", ".join(template_search_paths))

# --------------------------------------------------------------------
# Engines / Modules
# --------------------------------------------------------------------
dm = DriveManager()
janitor = Janitor()

# --------------------------------------------------------------------
# Basic Auth (fail closed)
# --------------------------------------------------------------------
basic_auth = HTTPBasic()

def require_auth(credentials: HTTPBasicCredentials = Depends(basic_auth)) -> bool:
    user = os.getenv("SENTRY_USER", "")
    pwd = os.getenv("SENTRY_PASS", "")

    # Fail closed if not configured
    if not user or not pwd:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured. Set SENTRY_USER and SENTRY_PASS.",
        )

    if credentials.username != user or credentials.password != pwd:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


# --------------------------------------------------------------------
# Filesystem Browser API (restricted)
# --------------------------------------------------------------------
ALLOWED_ROOT = Path("/mnt/sentry")
BLOCKED_PREFIXES = ("/proc", "/sys", "/dev")

@app.get("/api/fs/list")
async def fs_list(
    path: str = Query(str(ALLOWED_ROOT), description="Absolute path to list"),
    _: bool = Depends(require_auth),
):
    """
    Lists directories (and files) at a given path.
    Restricted to /mnt/sentry subtree.
    """
    try:
        p = Path(path).expanduser()

        # normalize to absolute path
        if not p.is_absolute():
            return JSONResponse({"error": "Path must be absolute."}, status_code=400)

        p_str = str(p)

        # block virtual fs
        if any(p_str == bp or p_str.startswith(bp + "/") for bp in BLOCKED_PREFIXES):
            return JSONResponse({"error": "Path is not allowed."}, status_code=403)

        # enforce allowed root
        try:
            p_res = p.resolve()
            root_res = ALLOWED_ROOT.resolve()
        except Exception:
            return JSONResponse({"error": "Invalid path."}, status_code=400)

        if not str(p_res).startswith(str(root_res)):
            return JSONResponse({"error": "Outside allowed root (/mnt/sentry)."}, status_code=403)

        if not p_res.exists():
            return JSONResponse({"error": "Path does not exist."}, status_code=404)
        if not p_res.is_dir():
            return JSONResponse({"error": "Path is not a directory."}, status_code=400)

        entries: List[Dict[str, Any]] = []
        for child in sorted(p_res.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            entries.append({
                "name": child.name,
                "path": str(child),
                "type": "dir" if child.is_dir() else "file",
            })

        parent = str(p_res.parent) if str(p_res) != str(root_res) else str(root_res.parent)

        return {"path": str(p_res), "parent": parent, "entries": entries}

    except PermissionError:
        return JSONResponse({"error": "Permission denied."}, status_code=403)
    except Exception as e:
        return JSONResponse({"error": f"Unhandled error: {e}"}, status_code=500)


# --------------------------------------------------------------------
# Web UI
# --------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _: bool = Depends(require_auth)):
    drives = dm.detect_drives()
    return templates.TemplateResponse("index.html", {"request": request, "drives": drives})


# --------------------------------------------------------------------
# Drives API
# --------------------------------------------------------------------
@app.get("/api/drives")
async def get_drives(_: bool = Depends(require_auth)):
    return dm.detect_drives()


# --------------------------------------------------------------------
# Scan API (background) + status
# --------------------------------------------------------------------
@app.post("/api/scan")
async def start_scan(
    request: Request,
    background_tasks: BackgroundTasks,
    _: bool = Depends(require_auth),
):
    data = await request.json()
    targets = data.get("targets", [])

    if not isinstance(targets, list) or not targets:
        return JSONResponse({"error": "No targets provided."}, status_code=400)

    # Create mission now; run scanner in background
    with Session(engine) as session:
        mission = ScanMission(
            timestamp=time.time(),
            root_paths=";".join(targets),
            status="RUNNING",
        )
        session.add(mission)
        session.commit()
        session.refresh(mission)

        mission_id = mission.id

    background_tasks.add_task(run_scanner, targets, mission_id)

    return {"status": "Scan Started", "mission_id": mission_id}


@app.get("/api/scan/status")
async def scan_status(
    mission_id: int = Query(...),
    _: bool = Depends(require_auth),
):
    with Session(engine) as session:
        mission = session.get(ScanMission, mission_id)
        if not mission:
            return JSONResponse({"error": "Mission not found."}, status_code=404)

        count = session.exec(
            select(func.count()).select_from(FileRecord).where(FileRecord.mission_id == mission_id)
        ).one()

        return {
            "mission_id": mission_id,
            "status": mission.status,
            "files_indexed": int(count),
            "root_paths": mission.root_paths,
            "timestamp": mission.timestamp,
        }


# --------------------------------------------------------------------
# Analyze / Clean endpoints (kept as-is hooks; ensure your existing code matches)
# --------------------------------------------------------------------
@app.get("/api/analyze")
async def analyze(gold_path: str = Query(...), _: bool = Depends(require_auth)):
    data = janitor.analyze_duplicates(gold_path)
    return data

@app.post("/api/clean")
async def clean(request: Request, _: bool = Depends(require_auth)):
    payload = await request.json()
    gold = payload.get("gold")
    targets = payload.get("targets", [])
    result = janitor.execute_reaper(gold, targets)
    return result
