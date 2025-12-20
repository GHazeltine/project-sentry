import os
import time
from pathlib import Path
from typing import List
from fastapi import FastAPI, Request, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import Session, select, func
from pydantic import BaseModel

# Unified Core Imports
from app.database.models import init_db, engine, ScanMission, FileRecord
from app.core.drive_manager import DriveManager
from app.core.scanner import Scanner
from app.core.reaper import Reaper
from app.core.janitor import Janitor
from app.core.reporter import Reporter  # <--- NEW IMPORT

app = FastAPI(title="Project Sentry | Command Center")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))

# Auth Logic
security = HTTPBasic()
def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    user = os.getenv("SENTRY_USER", "admin")
    pwd = os.getenv("SENTRY_PASS", "change-this-now")
    if credentials.username != user or credentials.password != pwd:
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})
    return credentials.username

@app.on_event("startup")
def on_startup():
    init_db()
    print("🚀 Sentry Command Center Online.")

# --- DATA MODELS ---
class MountRequest(BaseModel):
    remote_path: str
    username: str
    password: str

class ScanRequest(BaseModel):
    gold_paths: List[str]
    target_paths: List[str]

class CleanRequest(BaseModel):
    target_paths: List[str]

# --- BACKGROUND TASKS ---
def background_scan_task(gold_paths: List[str], target_paths: List[str], mission_id: int):
    scanner = Scanner(mission_id=mission_id)
    with Session(engine) as session:
        mission = session.get(ScanMission, mission_id)
        mission.status = "RUNNING"
        session.add(mission)
        session.commit()
        try:
            for path in gold_paths:
                drive_id = os.path.basename(path)
                scanner.scan_directory(path, tag="MASTER", drive_id=drive_id)
            for path in target_paths:
                drive_id = os.path.basename(path)
                scanner.scan_directory(path, tag="TARGET", drive_id=drive_id)
            mission.status = "COMPLETE"
        except Exception as e:
            print(f"Scan Error: {e}")
            mission.status = "ERROR"
        session.add(mission)
        session.commit()

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user: str = Depends(get_current_user)):
    dm = DriveManager()
    drives = dm.detect_drives()
    return templates.TemplateResponse("index.html", {"request": request, "drives": drives})

@app.post("/api/mount")
def mount_share(req: MountRequest, user: str = Depends(get_current_user)):
    dm = DriveManager()
    result = dm.mount_smb(req.remote_path, req.username, req.password)
    return result

@app.get("/api/drives")
def get_drives(user: str = Depends(get_current_user)):
    return DriveManager().detect_drives()

@app.post("/api/scan")
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks, user: str = Depends(get_current_user)):
    all_paths = req.gold_paths + req.target_paths
    if not all_paths: return JSONResponse({"error": "No paths selected"}, status_code=400)

    with Session(engine) as session:
        mission = ScanMission(timestamp=time.time(), root_paths=";".join(all_paths), status="PENDING")
        session.add(mission)
        session.commit()
        session.refresh(mission)
        
    background_tasks.add_task(background_scan_task, req.gold_paths, req.target_paths, mission.id)
    return {"status": "Started", "mission_id": mission.id}

# --- FILESYSTEM BROWSER ---
ALLOWED_ROOTS = [
    Path("/mnt/sentry"), Path("/media"), Path("/mnt"), 
    Path("/run/media"), Path("/"), Path("/host_fs")
]

@app.get("/api/fs/list")
async def fs_list(path: str = Query("/mnt/sentry"), user: str = Depends(get_current_user)):
    try:
        if path == "ROOT":
            return {
                "path": "ROOT", "parent": "ROOT",
                "entries": [
                    {"name": "Local Media (USB)", "path": "/media", "type": "dir"},
                    {"name": "Network Mounts", "path": "/mnt/sentry", "type": "dir"},
                    {"name": "System Mounts", "path": "/mnt", "type": "dir"}
                ]
            }
        p = Path(path).resolve()
        if not p.exists(): return JSONResponse({"error": "Path not found"}, status_code=404)

        entries = []
        for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if child.name.startswith('.'): continue
            entries.append({
                "name": child.name, "path": str(child),
                "type": "dir" if child.is_dir() else "file",
            })
        return {"path": str(p), "parent": str(p.parent), "entries": entries}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/status")
def get_status(user: str = Depends(get_current_user)):
    with Session(engine) as session:
        count = session.exec(select(func.count(FileRecord.id))).one()
        latest = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        status = latest.status if latest else "IDLE"
        return {"file_count": count, "status": status}

@app.get("/api/analyze")
def analyze(user: str = Depends(get_current_user)):
    reaper = Reaper()
    kill_list = reaper.analyze_duplicates()
    total_size = sum(f['size'] for f in kill_list) / (1024**3)
    return {
        "count": len(kill_list),
        "size_gb": round(total_size, 2),
        "files": [f['path'] for f in kill_list[:10]]
    }

@app.post("/api/clean")
def clean(req: CleanRequest, user: str = Depends(get_current_user)):
    # 1. Execute Reaper (Delete Duplicates)
    reaper = Reaper()
    cleanup_stats = reaper.execute_cleanup()

    # 2. Execute Janitor (Delete Ghost Folders)
    janitor = Janitor()
    ghosts_removed = janitor.cleanup_ghosts(req.target_paths)
    
    # 3. Generate Report (PDF)
    reporter = Reporter()
    
    # Retrieve stats for the report
    with Session(engine) as session:
        total_scanned = session.exec(select(func.count(FileRecord.id))).one()
        latest_mission = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        mission_id = latest_mission.id if latest_mission else 0

    pdf_path = reporter.generate_report(
        mission_id=mission_id,
        total_scanned=total_scanned,
        duplicates_removed=cleanup_stats['deleted'],
        ghost_folders=ghosts_removed,
        target_paths=req.target_paths
    )
    
    return {
        "files_deleted": cleanup_stats['deleted'],
        "ghost_folders_removed": ghosts_removed,
        "report_url": f"/reports/{os.path.basename(pdf_path)}"
    }

# NEW: Endpoint to download the generated PDF
@app.get("/reports/{filename}")
def download_report(filename: str, user: str = Depends(get_current_user)):
    file_path = os.path.join("/app/reports", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/pdf', filename=filename)
    raise HTTPException(status_code=404, detail="Report not found")
