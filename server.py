import os
import shutil
import time
import subprocess
import logging
import json
from typing import List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from sqlmodel import Session, select, func
from app.database.models import engine, Drive, FileRecord, ScanMission, FileTransaction, init_db
from app.core.scanner import Scanner
from app.core.organizer import Organizer
from app.core.reporter import Reporter
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()
def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    return credentials.username

app = FastAPI()
os.makedirs("/app/reports", exist_ok=True)
app.mount("/reports", StaticFiles(directory="/app/reports"), name="reports")
templates = Jinja2Templates(directory="app/templates")

class ScanRequest(BaseModel):
    gold_paths: List[str]
    target_paths: List[str]
    enable_privacy: bool = False
    enable_grouping: bool = False

class DriveCmdRequest(BaseModel):
    device_path: str

class CleanRequest(BaseModel):
    target_paths: List[str]

class NetworkMountRequest(BaseModel):
    remote_path: str
    username: str
    password: str

# --- SYSTEM HELPERS ---
def system_mount(device_path, mount_point):
    os.makedirs(mount_point, exist_ok=True)
    try:
        subprocess.run(["mount", device_path, mount_point], check=True)
        return True
    except:
        try:
            subprocess.run(["mount", "-t", "ntfs-3g", device_path, mount_point], check=True)
            return True
        except: return False

def get_smart_status(device_path):
    try:
        parent = device_path.rstrip('0123456789') if device_path[-1].isdigit() else device_path
        cmd = ["smartctl", "-H", parent]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if "PASSED" in result.stdout: return "✅ PASSED"
        if "FAILED" in result.stdout: return "❌ FAILED"
    except: pass
    return "⚠️ UNKNOWN"

# --- TASKS ---
def background_scan_task(gold_paths, target_paths, mission_id, enable_privacy, enable_grouping):
    scanner = Scanner(mission_id=mission_id)
    with Session(engine) as session:
        mission = session.get(ScanMission, mission_id)
        mission.status = "RUNNING"
        session.add(mission)
        session.commit()

        for path in gold_paths: scanner.scan_directory(path, "MASTER", os.path.basename(path), False)
        for path in target_paths: scanner.scan_directory(path, "TARGET", os.path.basename(path), enable_privacy)

        if enable_grouping:
            try:
                organizer = Organizer(mission_id)
                organizer.group_by_similarity()
            except Exception as e: print(f"Grouping Error: {e}")

        mission.status = "COMPLETE"
        session.add(mission)
        session.commit()

# --- API ROUTES ---
@app.on_event("startup")
def on_startup(): init_db()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/drives")
def get_drives(user: str = Depends(get_current_user)):
    try:
        lsblk = subprocess.check_output(['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,LABEL,MODEL']).decode()
        data = json.loads(lsblk)
        drives = []
        def extract(devices):
            for d in devices:
                if d.get('type') in ['part', 'disk']:
                    drives.append({
                        "device": f"/dev/{d['name']}",
                        "name": d.get('label') or d['name'],
                        "size": d['size'],
                        "mountpoint": d['mountpoint'],
                        "health": "UNKNOWN"
                    })
                if 'children' in d: extract(d['children'])
        extract(data.get('blockdevices', []))
        return drives
    except: return []

@app.post("/api/drives/mount")
def mount_drive_endpoint(req: DriveCmdRequest, user: str = Depends(get_current_user)):
    mount_point = f"/media/{os.path.basename(req.device_path)}"
    if system_mount(req.device_path, mount_point): return {"status": "Mounted", "mountpoint": mount_point}
    return {"error": "Mount failed"}

@app.post("/api/mount")
def mount_network(req: NetworkMountRequest, user: str = Depends(get_current_user)):
    os.makedirs("/mnt/sentry", exist_ok=True)
    try:
        subprocess.run(["mount", "-t", "cifs", req.remote_path, "/mnt/sentry", f"-o", f"username={req.username},password={req.password}"], check=True)
        return {"message": "Mounted"}
    except Exception as e: return {"message": str(e)}

@app.get("/api/fs/list")
def list_fs(path: str, user: str = Depends(get_current_user)):
    if not os.path.exists(path): return {"error": "Path not found"}
    entries = [{"name": e.name, "path": e.path, "type": "dir" if e.is_dir() else "file"} for e in os.scandir(path)]
    return {"entries": sorted(entries, key=lambda x: (x['type']!='dir', x['name']))}

@app.post("/api/scan")
async def start_scan(req: ScanRequest, bg: BackgroundTasks, user: str = Depends(get_current_user)):
    mission = ScanMission(status="PENDING", timestamp=time.time(), root_paths=json.dumps(req.gold_paths + req.target_paths))
    with Session(engine) as session:
        session.add(mission)
        session.commit()
        session.refresh(mission)
    bg.add_task(background_scan_task, req.gold_paths, req.target_paths, mission.id, req.enable_privacy, req.enable_grouping)
    return {"status": "Started", "mission_id": mission.id}

@app.get("/api/status")
def get_status():
    with Session(engine) as session:
        m = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        if not m: return {"status": "IDLE", "file_count": 0}
        c = session.exec(select(func.count(FileRecord.id)).where(FileRecord.mission_id == m.id)).one()
        return {"status": m.status, "file_count": c}

@app.get("/api/analyze")
def analyze_results(user: str = Depends(get_current_user)):
    with Session(engine) as session:
        latest = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        if not latest: return {"count": 0, "size_gb": 0}
        trash_count = session.exec(select(func.count(FileRecord.id)).where(FileRecord.mission_id == latest.id, FileRecord.tag == "DUPLICATE")).one()
        flag_count = session.exec(select(func.count(FileRecord.id)).where(FileRecord.mission_id == latest.id, FileRecord.is_flagged == True)).one()
        return {"count": trash_count + flag_count, "size_gb": 0}

@app.post("/api/clean")
def execute_clean(req: CleanRequest, user: str = Depends(get_current_user)):
    deleted = 0
    report_url = "#"
    vault_info = {"count": 0, "path": "N/A", "password": "N/A"}

    with Session(engine) as session:
        latest = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        if not latest: return {"error": "No mission"}

        # 1. DELETE DUPLICATES (Trash)
        trash = session.exec(select(FileRecord).where(FileRecord.mission_id == latest.id, FileRecord.tag == "DUPLICATE")).all()
        for f in trash:
            if "GOLD" in f.path: continue
            try:
                if os.path.exists(f.path):
                    os.remove(f.path)
                    deleted += 1
            except: pass

        # 2. SECURE PRIVACY FILES (Move to Vault)
        try:
            organizer = Organizer(latest.id)
            v_count, v_path, v_pass = organizer.secure_privacy_files()
            if v_count > 0:
                vault_info = {"count": v_count, "path": v_path, "password": v_pass}
        except Exception as e:
            print(f"Vault Error: {e}")

        # 3. GENERATE REPORT
        try:
            reporter = Reporter()
            grouped_count = session.exec(select(func.count(FileRecord.id)).where(FileRecord.mission_id == latest.id, FileRecord.tag == "GROUPED")).one()
            pdf = reporter.generate_report(
                mission_id=latest.id,
                total_scanned=session.exec(select(func.count(FileRecord.id)).where(FileRecord.mission_id == latest.id)).one(),
                duplicates_removed=deleted,
                ghost_folders=grouped_count,
                target_paths=req.target_paths,
                vault_info=vault_info
            )
            report_url = f"/reports/{os.path.basename(pdf)}"
        except Exception as e: print(e)

    return {"files_deleted": deleted, "ghost_folders_removed": 0, "report_url": report_url}

@app.post("/api/undo")
def undo_last_action(user: str = Depends(get_current_user)):
    with Session(engine) as session:
        latest = session.exec(select(ScanMission).order_by(ScanMission.id.desc())).first()
        if latest:
            count = Organizer(latest.id).undo_grouping()
            return {"status": "Undone", "files_restored": count}
    return {"error": "No mission"}
