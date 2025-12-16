import os
import hashlib
import time
from sqlmodel import Session, select
from app.database.models import FileRecord, ScanMission, engine

def calculate_md5(file_path, block_size=65536):
    """Generates a unique fingerprint for a file without loading the whole thing into RAM."""
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            for buf in iter(lambda: f.read(block_size), b''):
                hasher.update(buf)
        return hasher.hexdigest()
    except (PermissionError, OSError):
        return None  # Skip files we aren't allowed to touch

def run_scanner(mission_id: int):
    """
    The Main Loop.
    1. Reads the Mission from DB.
    2. Crawls the folders.
    3. Saves every file found to DB.
    """
    print(f"[WORKER] Starting Scan for Mission #{mission_id}")
    
    with Session(engine) as session:
        # 1. Get the Mission details
        mission = session.get(ScanMission, mission_id)
        if not mission:
            print("[WORKER] Error: Mission not found.")
            return

        root_paths = mission.root_paths.split(",")
        
        # 2. Start Crawling
        for root_path in root_paths:
            # os.walk recursively finds every file in every subfolder
            for subdir, dirs, files in os.walk(root_path):
                
                for filename in files:
                    filepath = os.path.join(subdir, filename)
                    
                    # Skip if we already scanned this file (basic check)
                    # existing = session.exec(select(FileRecord).where(FileRecord.path == filepath)).first()
                    # if existing: continue 

                    # 3. Analyze the File
                    try:
                        stats = os.stat(filepath)
                        file_hash = calculate_md5(filepath)
                        
                        if file_hash:
                            # 4. Save to Database
                            record = FileRecord(
                                mission_id=mission_id,
                                path=filepath,
                                filename=filename,
                                extension=os.path.splitext(filename)[1].lower(),
                                size_bytes=stats.st_size,
                                created_at=stats.st_ctime,
                                file_hash=file_hash,
                                is_scanned=True
                            )
                            session.add(record)
                            
                            # Commit in batches (every file for now, optimize later)
                            session.commit()
                            
                    except Exception as e:
                        print(f"[WORKER] Failed to scan {filepath}: {e}")

    print(f"[WORKER] Mission #{mission_id} Complete.")
