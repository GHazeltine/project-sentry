import os
import hashlib
from typing import List
from sqlmodel import Session, select
from app.database.models import FileRecord, Mission, Drive, engine


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
    print(f"--- STARTING MULTI-TARGET SCAN ---")
    print(f"Targets: {target_paths}")

    with Session(engine) as session:

        # 1️⃣ Create ONE mission for this scan run
        mission = Mission(status="running")
        session.add(mission)
        session.commit()
        session.refresh(mission)

        # 2️⃣ Loop over each target directory
        for root_directory in target_paths:
            if not os.path.exists(root_directory):
                print(f"[ERROR] Path not found: {root_directory}")
                continue

            # 3️⃣ Create ONE drive record per target
            drive = Drive(mountpoint=root_directory)
            session.add(drive)
            session.commit()
            session.refresh(drive)

            # 4️⃣ Walk files under this target
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

                        if not file_hash:
                            continue

                        record = FileRecord(
                            mission_id=mission.id,
                            drive_id=drive.id,
                            filename=filename,
                            path=filepath,
                            size_bytes=file_size,
                            file_hash=file_hash,
                            is_scanned=True,
                        )

                        session.add(record)
                        session.commit()
                        print(f"[+] Indexed: {filepath}")

                    except OSError:
                        continue

        # 5️⃣ Close out mission
        mission.status = "complete"
        session.add(mission)
        session.commit()

    print("--- SCAN COMPLETE ---")
