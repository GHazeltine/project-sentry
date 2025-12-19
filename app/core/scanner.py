import os
import hashlib
import time
from pathlib import Path
from sqlmodel import Session
from app.database.models import engine, ScanMission, FileRecord
from app.core.ai_processor import AIProcessor

class Scanner:
    def __init__(self, mission_id: int):
        self.mission_id = mission_id
        self.ai = AIProcessor()

    def calculate_hash(self, filepath: str) -> str:
        h = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                while chunk := f.read(65536): h.update(chunk)
            return h.hexdigest()
        except: return None

    def scan_directory(self, root_path: str, tag: str, drive_id: str):
        visual_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        with Session(engine) as session:
            count = 0
            for root, dirs, files in os.walk(root_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fname in files:
                    if fname.startswith('.'): continue
                    fpath = os.path.join(root, fname)
                    try:
                        ext = Path(fname).suffix.lower()
                        f_hash = self.calculate_hash(fpath)
                        v_hash = self.ai.get_visual_hash(fpath) if ext in visual_exts else None
                        rec = FileRecord(
                            mission_id=self.mission_id, drive_id=drive_id,
                            path=fpath, filename=fname, extension=ext,
                            size_bytes=os.path.getsize(fpath),
                            created_at=time.time(), file_hash=f_hash,
                            visual_hash=v_hash, tag=tag
                        )
                        session.add(rec)
                        count += 1
                        if count % 100 == 0: session.commit()
                    except: continue
            session.commit()
