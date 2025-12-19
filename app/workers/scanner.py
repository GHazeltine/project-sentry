import os
import time
import hashlib
from typing import List
from sqlmodel import Session, select
from app.database.models import FileRecord, ScanMission, engine




# ---------------------------------------------------------

# CONFIGURATION
# ---------------------------------------------------------
IGNORE_LIST = {
    'Windows', 'Program Files', 'Program Files (x86)',
    '.git', 'node_modules', '$RECYCLE.BIN', 'System Volume Information'
}

def calculate_md5(file_path, block_size=65536):
    """Generates a unique MD5 hash for the file content."""
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            for buf in iter(lambda: f.read(block_size), b''):
                hasher.update(buf)
        return hasher.hexdigest()
    except Exception as e:
        # Log locked files but don't crash
        # print(f"[LOCKED] Could not read {file_path}")
        return None

def run_scanner(target_paths: List[str]):
    """
    Scans a LIST of directories recursively.
    Creates one ScanMission per run and links each FileRecord to it.
    """
    print(f"--- STARTING MULTI-TARGET SCAN ---")
    print(f"Targets: {target_paths}")

    with Session(engine) as session:
        # Create a mission record for this scan run
        mission = ScanMission(
            timestamp=time.time(),
            root_paths=";".join(target_paths),
            status="RUNNING",
        )
        session.add(mission)
        session.commit()
        session.refresh(mission)

        for root_directory in target_paths:
            if not os.path.exists(root_directory):
                print(f"[ERROR] Path not found: {root_directory}")
                continue

            for subdir, dirs, files in os.walk(root_directory):
                # Filter ignored directories
                dirs[:] = [d for d in dirs if d not in IGNORE_LIST]

                for filename in files:
                    filepath = os.path.join(subdir, filename)

                    # Resume logic: skip if already indexed
                    existing = session.exec(
                        select(FileRecord).where(FileRecord.path == filepath)
                    ).first()
                    if existing:
                        continue

                    try:
                        file_size = os.path.getsize(filepath)
                        file_hash = calculate_md5(filepath)
                        ext = os.path.splitext(filename)[1].lstrip(".").lower() or None

                        if file_hash:
                            new_record = FileRecord(
                                mission_id=mission.id,
                                drive_id=root_directory,
                                path=filepath,
                                filename=filename,
                                extension=ext or "",
                                size_bytes=file_size,
                                created_at=time.time(),
                                file_hash=file_hash,
                                is_scanned=True,
                            )
                            session.add(new_record)
                            session.commit()
                            print(f"[+] Indexed: {filename}")

                    except OSError:
                        continue

        # Mark mission complete
        mission.status = "COMPLETE"
        session.add(mission)
        session.commit()

    print("--- SCAN COMPLETE ---")
