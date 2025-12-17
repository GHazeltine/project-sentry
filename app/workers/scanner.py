import os
import hashlib
from sqlmodel import Session
from app.database.models import FileRecord, ScanMission, engine

def calculate_md5(file_path, block_size=65536):
    """Generates a unique fingerprint for a file."""
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            for buf in iter(lambda: f.read(block_size), b''):
                hasher.update(buf)
        return hasher.hexdigest()
    except (PermissionError, OSError):
        return None

def run_scanner(mission_id: int):
    """
    Main Loop: Crawls folders -> Hashes Files -> Saves to DB -> Marks Complete.
    """
    print(f"[WORKER] Starting Scan for Mission #{mission_id}")
    
    with Session(engine) as session:
        # 1. Get the Mission details
        mission = session.get(ScanMission, mission_id)
        if not mission:
            return

        root_paths = mission.root_paths.split(",")
        
        # 2. Start Crawling
        for root_path in root_paths:
            for subdir, dirs, files in os.walk(root_path):
                for filename in files:
                    filepath = os.path.join(subdir, filename)
                    
                    try:
                        stats = os.stat(filepath)
                        file_hash = calculate_md5(filepath)
                        
                        if file_hash:
                            # Save to Database
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
                            session.commit()
                            
                    except Exception as e:
                        print(f"[WORKER] Failed to scan {filepath}: {e}")

        # 3. MARK MISSION AS COMPLETE
        # We must re-fetch the mission to ensure we have the latest state before updating
        mission = session.get(ScanMission, mission_id)
        mission.status = "COMPLETED"
        session.add(mission)
        session.commit()

    print(f"[WORKER] Mission #{mission_id} Complete.")
