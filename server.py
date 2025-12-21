import os
import shutil
import time
import subprocess
import logging
import json
from typing import List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from sqlmodel import Session, select, func
from app.database.models import engine, Drive, FileRecord, ScanMission, init_db
from app.core.scanner import Scanner

# --- AUTH ---
from fastapi.security import HTTPBasic, HTTPBasicCredentials
security = HTTPBasic()
def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    return credentials.username

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# --- DATA MODELS ---
class ScanRequest(BaseModel):
    gold_paths: List[str]
    target_paths: List[str]
    enable_privacy: bool = False

# --- HELPER: ROBUST HEALTH CHECK ---
def get_smart_status(device_path):
    # 1. Standard Check
    try:
        cmd = ["smartctl", "-H", device_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if "PASSED" in result.stdout: return "✅ PASSED"
        if "FAILED" in result.stdout: return "❌ FAILED"
    except: pass

    # 2. Force SAT
    try:
        cmd = ["smartctl", "-d", "sat", "-H", device_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if "PASSED" in result.stdout: return "✅ PASSED"
        if "FAILED" in result.stdout: return "❌ FAILED"
    except: pass

    # 3. Force Permissive
    try:
        cmd = ["smartctl", "-d", "sat", "-T", "permissive", "-H", device_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if "PASSED" in result.stdout: return "✅ PASSED"
        if "FAILED" in result.stdout: return "❌ FAILED"
    except: pass

    return "⚠️ UNKNOWN (Controller Limit)"

# --- BACKGROUND TASKS ---
def background_scan_task(gold_paths, target_paths, mission_id, enable_privacy):
    scanner = Scanner(mission_id=mission_id)
    with Session(engine) as session:
        mission = session.get(ScanMission, mission_id)
        mission.status = "RUNNING"
        session.add(mission)
        session.commit()
        
        # Scan Gold
        for path in gold_paths:
            scanner.scan_directory(path, "MASTER", os.path.basename(path), False)
            
        # Scan Target
        for path in target_paths:
            scanner.scan_directory(path, "TARGET", os.path.basename(path), enable_privacy)

        mission.status = "COMPLETE"
        session.add(mission)
        session.commit()

# --- ROUTES ---

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/drives")
def get_drives(user: str = Depends(get_current_user)):
    try:
        lsblk = subprocess.check_output(['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,LABEL,MODEL']).decode()
        data = json.loads(lsblk)
        drives = []
        
        for d in data.get('blockdevices', []):
            if d.get('type') == 'disk':
                dev_path = f"/dev/{d['name']}"
                health = get_smart_status(dev_path)
                d['health'] = health
                drives.append(d)
                
        return drives
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/fs/list")
def list_fs(path: str, user: str = Depends(get_current_user)):
    if not os.path.exists(path):
        return {"error": "Path not found"}
    try:
        entries = []
        for entry in os.scandir(path):
            entries.append({
                "name": entry.name,
                "path": entry.path,
                "type": "dir" if entry.is_dir() else "file"
            })
        return {"entries": sorted(entries, key=lambda x: (x['type']!='dir', x['name']))}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/scan")
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks, user: str = Depends(get_current_user)):
    all_paths = req.gold_paths + req.target_paths
    paths_json = json.dumps(all_paths)
    
    mission = ScanMission(
        status="PENDING", 
        timestamp=time.time(),
        root_paths=paths_json
    )
    
    with Session(engine) as session:
        session.add(mission)
        session.commit()
        session.refresh(mission)
    
    background_tasks.add_task(
        background_scan_task, 
        req.gold_paths, 
        req.target_paths, 
        mission.id, 
        req.enable_privacy
    )
    
    return {"status": "Started", "mission_id": mission.id}

@app.get("/api/status")
def get_status():
    with Session(engine) as session:
        mission = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        if not mission:
            return {"status": "IDLE", "file_count": 0}
        
        count = session.exec(select(func.count(FileRecord.id)).where(FileRecord.mission_id == mission.id)).one()
        return {"status": mission.status, "file_count": count}

@app.get("/api/privacy/review")
def get_privacy_flags(user: str = Depends(get_current_user)):
    with Session(engine) as session:
        latest = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        if not latest: return []
        
        statement = select(FileRecord).where(
            FileRecord.mission_id == latest.id, 
            FileRecord.is_flagged == True
        )
        return session.exec(statement).all()

@app.post("/api/privacy/quarantine")
def execute_quarantine(user: str = Depends(get_current_user)):
    moved_count = 0
    with Session(engine) as session:
        latest = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        if not latest: return {"error": "No mission"}
        
        flagged = session.exec(select(FileRecord).where(
            FileRecord.mission_id == latest.id, 
            FileRecord.is_flagged == True
        )).all()
        
        for record in flagged:
            vault_dir = os.path.join(os.path.dirname(record.path), "SENTRY_VAULT")
            os.makedirs(vault_dir, exist_ok=True)
            
            new_path = os.path.join(vault_dir, record.filename)
            try:
                shutil.move(record.path, new_path)
                record.path = new_path
                record.is_flagged = False
                session.add(record)
                moved_count += 1
            except Exception as e:
                print(f"Move failed: {e}")
            
        session.commit()
        
    return {"status": "Quarantined", "count": moved_count}
