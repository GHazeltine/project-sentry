import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# --- CONNECTING TO YOUR v2.0 BACKEND ---
from app.core.drive_manager import DriveManager
from app.core.scanner import Scanner
from app.core.reaper import Reaper
from app.core.janitor import Janitor

app = FastAPI()

# Setup folders for the web interface
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Initialize the v2.0 Engines
dm = DriveManager()
scanner = Scanner()
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
    """
    Button: 'INITIATE SCAN'
    Action: Triggers Module B (Scanner)
    """
    data = await request.json()
    gold_path = data.get('gold')
    targets = data.get('targets', [])

    print(f"🚀 API STARTING SCAN: Gold={gold_path}, Targets={targets}")
    
    # 1. Scan Gold (Master)
    scanner.scan_directory(gold_path, tag="MASTER")
    
    # 2. Scan Targets
    for t in targets:
        scanner.scan_directory(t, tag="TARGET")
        
    return {"status": "Scan Complete", "message": "Indexing finished."}

@app.get("/api/analyze")
async def analyze_duplicates(gold_path: str):
    """
    Button: 'ANALYZE DUPLICATES'
    Action: Triggers Module D (Reaper Analysis)
    """
    reaper = Reaper(master_path=gold_path)
    duplicates = reaper.analyze()
    
    # Calculate stats for the UI
    total_size = sum([os.path.getsize(p) for p in duplicates]) / (1024*1024*1024)
    
    return {
        "count": len(duplicates),
        "size_gb": round(total_size, 2),
        "files": duplicates[:50] # Send first 50 for preview
    }

@app.post("/api/clean")
async def execute_clean(request: Request):
    """
    Button: 'DESTROY' (The Big Red Button)
    Action: Triggers Module D (Execute) + Module E (Janitor)
    """
    data = await request.json()
    gold_path = data.get('gold')
    targets = data.get('targets', [])
    
    # 1. Reaper Execution
    reaper = Reaper(master_path=gold_path)
    duplicates = reaper.analyze()
    reaper.execute(duplicates)
    
    # 2. Ghostbuster (Janitor)
    cleaned_stats = []
    for t in targets:
        stats = janitor.clean(t)
        cleaned_stats.append(stats)
        
    return {"status": "Clean Complete", "janitor_stats": cleaned_stats}

if __name__ == "__main__":
    # Run on Port 8000 (Standard for K3s/Docker)
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
