import os
import time
import hashlib
from typing import List, Optional

from sqlmodel import Session, select
from app.database.models import FileRecord, ScanMission, engine

IGNORE_LIST = {
    "Windows", "Program Files", "Program Files (x86)",
    ".git", "node_modules", "$RECYCLE.BIN", "System Volume Information"
}

def calculate_md5(file_path: str, block_size: int = 65536) -> Optional[str]:
    hasher = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for buf in iter(lambda: f.read(block_size), b""):
                hasher.update(buf)
        return hasher.hexdigest()
    except Exception:
        return None

def run_scanner(target_paths: List[str], mission_id: Optional[int] = None) -> int:
    """
    Scans a list of directories recursively.
    If mission_id is provided, files are written under that mission.
    If not, a new ScanMission is created.
    Returns mission_id.
    """
    print("--- STARTING MULTI-TARGET SCAN ---")
    print(f"Targets: {target_paths}")

    with Session(engine) as session:
        # Create or load mission
        if mission_id is None:
            mission = ScanMission(
                timestamp=time.time(),
                root_paths=";".join(target_paths),
                status="RUNNING",
            )
            session.add(mission)
            session.commit()
            session.refresh(mission)
        else:
            mission = session.get(ScanMission, mission_id)
            if mission is None:
                # Fail safe: create a mission if caller passed a bad id
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
                dirs[:] = [d for d in dirs if d not in IGNORE_LIST]

                for filename in files:
                    filepath = os.path.join(subdir, filename)

                    # Resume logic
                    existing = session.exec(
                        select(FileRecord).where(FileRecord.path == filepath)
                    ).first()
                    if existing:
                        continue

                    try:
                        file_size = os.path.getsize(filepath)
                        file_hash = calculate_md5(filepath)

                        # extension is required in your model, so never leave it None
                        ext = os.path.splitext(filename)[1].lstrip(".").lower() or ""

                        if file_hash:
                            new_record = FileRecord(
                                mission_id=mission.id,
                                drive_id=root_directory,     # required
                                path=filepath,
                                filename=filename,
                                extension=ext,               # required
                                size_bytes=file_size,
                                created_at=time.time(),      # required
                                file_hash=file_hash,         # required
                                is_scanned=True,
                            )
                            session.add(new_record)
                            session.commit()
                    except OSError:
                        continue

        mission.status = "COMPLETE"
        session.add(mission)
        session.commit()

        print(f"--- SCAN COMPLETE (mission_id={mission.id}) ---")
        return mission.id
