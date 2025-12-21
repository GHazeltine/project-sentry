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

class DriveCmdRequest(BaseModel):
    device_path: str 

class CleanRequest(BaseModel):
    target_paths: List[str]

class NetworkMountRequest(BaseModel):
    remote_path: str
    username: str
    password: str

# --- HELPER: SYSTEM MOUNT ---
def system_mount(device_path, mount_point):
    os.makedirs(mount_point, exist_ok=True)
    try:
        subprocess.run(["mount", device_path, mount_point], check=True)
        return True
    except:
        try:
            subprocess.run(["mount", "-t", "ntfs-3g", device_path, mount_point], check=True)
            return True
        except:
            return False

def get_smart_status(device_path):
    try:
        # Handle partitions (sda1 -> sda)
        parent = device_path.rstrip('0123456789') if device_path[-1].isdigit() else device_path
        cmd = ["smartctl", "-H", parent]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if "PASSED" in result.stdout: return "✅ PASSED"
        if "FAILED" in result.stdout: return "❌ FAILED"
    except: pass
    return "⚠️ UNKNOWN"

# --- BACKGROUND TASKS ---
def background_scan_task(gold_paths, target_paths, mission_id, enable_privacy):
    scanner = Scanner(mission_id=mission_id)
    with Session(engine) as session:
        mission = session.get(ScanMission, mission_id)
        mission.status = "RUNNING"
        session.add(mission)
        session.commit()
        
        # 1. Scan Gold
        for path in gold_paths:
            scanner.scan_directory(path, "MASTER", os.path.basename(path), False)
            
        # 2. Scan Target
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

# --- 1. HARDWARE APIS ---
@app.get("/api/drives")
def get_drives(user: str = Depends(get_current_user)):
    try:
        lsblk = subprocess.check_output(['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,LABEL,MODEL']).decode()
        data = json.loads(lsblk)
        drives = []
        
        def extract(devices):
            for d in devices:
                if d.get('type') in ['part', 'disk']:
                    dev_path = f"/dev/{d['name']}"
                    drives.append({
                        "device": dev_path,
                        "name": d.get('label') or d['name'],
                        "size": d['size'],
                        "mountpoint": d['mountpoint'],
                        "is_mounted": d['mountpoint'] is not None,
                        "health": get_smart_status(dev_path)
                    })
                if 'children' in d: extract(d['children'])

        extract(data.get('blockdevices', []))
        return drives
    except Exception as e:
        return [{"name": "Error", "size": "0", "device": str(e), "mountpoint": None, "health": "FAIL"}]

@app.post("/api/drives/mount")
def mount_drive_endpoint(req: DriveCmdRequest, user: str = Depends(get_current_user)):
    if not req.device_path.startswith("/dev/"): return {"error": "Invalid device path"}
    
    device_name = os.path.basename(req.device_path)
    mount_point = f"/media/{device_name}"
    
    if system_mount(req.device_path, mount_point):
        return {"status": "Mounted", "mountpoint": mount_point}
    else:
        return {"error": "Mount failed. Check filesystem."}

@app.post("/api/drives/unmount")
def unmount_drive_endpoint(req: DriveCmdRequest, user: str = Depends(get_current_user)):
    try:
        subprocess.run(["umount", req.device_path], check=True)
        return {"status": "Unmounted"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/mount")
def mount_network(req: NetworkMountRequest, user: str = Depends(get_current_user)):
    local_mount = "/mnt/sentry"
    os.makedirs(local_mount, exist_ok=True)
    cmd = [
        "mount", "-t", "cifs", req.remote_path, local_mount,
        f"-o", f"username={req.username},password={req.password}"
    ]
    try:
        subprocess.run(cmd, check=True)
        return {"message": "Network Drive Mounted Successfully"}
    except Exception as e:
        return {"message": f"Mount Failed: {str(e)}"}

# --- 2. FILE SYSTEM ---
@app.get("/api/fs/list")
def list_fs(path: str, user: str = Depends(get_current_user)):
    if not os.path.exists(path): return {"error": "Path not found"}
    try:
        entries = []
        for entry in os.scandir(path):
            entries.append({"name": entry.name, "path": entry.path, "type": "dir" if entry.is_dir() else "file"})
        return {"entries": sorted(entries, key=lambda x: (x['type']!='dir', x['name']))}
    except Exception as e: return {"error": str(e)}

# --- 3. MISSION CONTROL ---
@app.post("/api/scan")
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks, user: str = Depends(get_current_user)):
    paths_json = json.dumps(req.gold_paths + req.target_paths)
    mission = ScanMission(status="PENDING", timestamp=time.time(), root_paths=paths_json)
    with Session(engine) as session:
        session.add(mission)
        session.commit()
        session.refresh(mission)
    background_tasks.add_task(background_scan_task, req.gold_paths, req.target_paths, mission.id, req.enable_privacy)
    return {"status": "Started", "mission_id": mission.id}

@app.get("/api/status")
def get_status():
    with Session(engine) as session:
        mission = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        if not mission: return {"status": "IDLE", "file_count": 0}
        count = session.exec(select(func.count(FileRecord.id)).where(FileRecord.mission_id == mission.id)).one()
        return {"status": mission.status, "file_count": count}

# --- 4. REAPER & ANALYTICS (RESTORED) ---
@app.get("/api/analyze")
def analyze_results(user: str = Depends(get_current_user)):
    """Returns stats for the 'ANALYZE' button"""
    with Session(engine) as session:
        latest = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        if not latest: return {"count": 0, "size_gb": 0}
        
        # Count flagged files (Privacy or Duplicate logic would go here)
        files = session.exec(select(FileRecord).where(FileRecord.mission_id == latest.id, FileRecord.is_flagged == True)).all()
        
        total_size = sum(f.size_bytes for f in files) if files else 0
        return {"count": len(files), "size_gb": round(total_size / (1024**3), 4)}

@app.post("/api/clean")
def execute_clean(req: CleanRequest, user: str = Depends(get_current_user)):
    """The 'EXECUTE REAPER' button logic"""
    deleted_count = 0
    with Session(engine) as session:
        latest = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        if not latest: return {"error": "No mission"}
        
        # Select all flagged files from latest mission
        files_to_kill = session.exec(select(FileRecord).where(
            FileRecord.mission_id == latest.id, 
            FileRecord.is_flagged == True
        )).all()
        
        for f in files_to_kill:
            try:
                # Security: Prevent deletion of GOLD files
                if "GOLD" in f.path: continue 
                
                if os.path.exists(f.path):
                    os.remove(f.path)
                    deleted_count += 1
            except Exception as e:
                print(f"Fail: {e}")
        
    return {
        "files_deleted": deleted_count, 
        "ghost_folders_removed": 0, 
        "report_url": "#" 
    }
