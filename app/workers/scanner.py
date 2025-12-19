# app/workers/scanner.py
import os
import time
import hashlib
from typing import List, Callable, Optional

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

def run_scanner(
    target_paths: List[str],
    progress_cb: Optional[Callable[[dict], None]] = None,
) -> int:
    """
    Scans a LIST of directories recursively.
    Returns mission_id.
    """

    now = time.time()
    root_paths_str = ";".join(target_paths)

    def emit(payload: dict):
        if progress_cb:
            progress_cb(payload)

    emit({"event": "start", "targets": target_paths, "ts": now})

    with Session(engine) as session:
        # Create mission record
        mission = ScanMission(timestamp=now, root_paths=root_paths_str, status="RUNNING")
        session.add(mission)
        session.commit()
        session.refresh(mission)

        mission_id = mission.id

        scanned = 0
        indexed = 0
        skipped = 0
        errors = 0
        last_commit = time.time()

        for root_directory in target_paths:
            if not os.path.exists(root_directory):
                errors += 1
                emit({"event": "error", "message": f"Path not found: {root_directory}"})
                continue

            emit({"event": "target", "path": root_directory})

            for subdir, dirs, files in os.walk(root_directory):
                dirs[:] = [d for d in dirs if d not in IGNORE_LIST]

                for filename in files:
                    scanned += 1
                    filepath = os.path.join(subdir, filename)

                    # Resume: skip if already indexed
                    existing = session.exec(
                        select(FileRecord).where(FileRecord.path == filepath)
                    ).first()
                    if existing:
                        skipped += 1
                        if scanned % 250 == 0:
                            emit({
                                "event": "progress",
                                "mission_id": mission_id,
                                "scanned": scanned,
                                "indexed": indexed,
                                "skipped": skipped,
                                "errors": errors,
                                "current": filepath,
                                "ts": time.time(),
                            })
                        continue

                    try:
                        file_size = os.path.getsize(filepath)
                        file_hash = calculate_md5(filepath)
                        ext = os.path.splitext(filename)[1].lstrip(".").lower()
# ext will be "" if no extension, which is safe for a required str column


                        if not file_hash:
                            skipped += 1
                            continue

                        rec = FileRecord(
                            mission_id=mission_id,
                            drive_id=root_directory,      # lightweight linkage
                            path=filepath,
                            filename=filename,
                            extension=ext,
                            size_bytes=file_size,
                            created_at=time.time(),
                            file_hash=file_hash,
                            is_scanned=True,
                        )
                        session.add(rec)
                        indexed += 1

                        # Commit periodically for performance + durability
                        if time.time() - last_commit > 2.0:
                            session.commit()
                            last_commit = time.time()

                        if indexed % 50 == 0:
                            emit({
                                "event": "progress",
                                "mission_id": mission_id,
                                "scanned": scanned,
                                "indexed": indexed,
                                "skipped": skipped,
                                "errors": errors,
                                "current": filepath,
                                "ts": time.time(),
                            })

                    except OSError:
                        errors += 1
                        continue

        # Final commit + mission status
        session.commit()
        mission.status = "COMPLETE"
        session.add(mission)
        session.commit()

        emit({
            "event": "complete",
            "mission_id": mission_id,
            "scanned": scanned,
            "indexed": indexed,
            "skipped": skipped,
            "errors": errors,
            "ts": time.time(),
        })

        return mission_id
