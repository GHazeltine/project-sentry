import os
import time
from typing import List
from fastapi import FastAPI, Request, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
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

app = FastAPI(title="Project Sentry | Command Center")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Setup Templates
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

class CleanRequest(BaseModel):
    gold: str
    targets: List[str]

# --- BACKGROUND TASKS ---
def background_scan_task(targets: List[str], mission_id: int):
    scanner = Scanner(mission_id=mission_id)
    with Session(engine) as session:
        mission = session.get(ScanMission, mission_id)
        mission.status = "RUNNING"
        session.add(mission)
        session.commit()
        try:
            for path in targets:
                tag = "MASTER" if "GOLD" in path.upper() else "TARGET"
                drive_id = os.path.basename(path) 
                scanner.scan_directory(path, tag, drive_id)
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

@app.get("/api/drives")
def get_drives(user: str = Depends(get_current_user)):
    return DriveManager().detect_drives()

@app.post("/api/mount")
def mount_share(req: MountRequest, user: str = Depends(get_current_user)):
    """Transferred from TUI: Mounts a network share via API."""
    dm = DriveManager()
    result = dm.mount_smb(req.remote_path, req.username, req.password)
    if not result["success"]:
        return JSONResponse({"error": result["message"]}, status_code=400)
    return result

@app.post("/api/scan")
async def start_scan(request: Request, background_tasks: BackgroundTasks, user: str = Depends(get_current_user)):
    data = await request.json()
    targets = data.get("targets", [])
    if not targets: return JSONResponse({"error": "No targets"}, status_code=400)

    with Session(engine) as session:
        mission = ScanMission(timestamp=time.time(), root_paths=";".join(targets), status="PENDING")
        session.add(mission)
        session.commit()
        session.refresh(mission)
        
    background_tasks.add_task(background_scan_task, targets, mission.id)
    return {"status": "Started", "mission_id": mission.id}

@app.get("/api/status")
def get_status(user: str = Depends(get_current_user)):
    with Session(engine) as session:
        count = session.exec(select(func.count(FileRecord.id))).one()
        latest = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        status = latest.status if latest else "IDLE"
        return {"file_count": count, "status": status}

@app.get("/api/analyze")
def analyze(gold_path: str = Query(...), user: str = Depends(get_current_user)):
    reaper = Reaper(master_drive_id=os.path.basename(gold_path))
    kill_list = reaper.analyze_duplicates()
    total_size = sum(f['size'] for f in kill_list) / (1024**3)
    return {
        "count": len(kill_list),
        "size_gb": round(total_size, 2),
        "files": [f['path'] for f in kill_list[:10]]
    }

@app.post("/api/clean")
def clean(req: CleanRequest, user: str = Depends(get_current_user)):
    reaper = Reaper(master_drive_id=os.path.basename(req.gold))
    return reaper.execute_cleanup()
