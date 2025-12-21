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

def scan_directory(self, root_path: str, tag: str, drive_id: str, privacy_scan_enabled: bool = False):
        print(f"[Scanner] Starting scan on: {root_path} (Privacy Scan Enabled: {privacy_scan_enabled})")
        
        if not os.path.exists(root_path):
            return

        with Session(engine) as session:
            for dirpath, _, filenames in os.walk(root_path):
                for name in filenames:
                    filepath = os.path.join(dirpath, name)
                    try:
                        stats = os.stat(filepath)
                        file_hash = self.calculate_md5(filepath)
                        
                        visual_data = None
                        is_flagged = False
                        
                        # --- ROBUST IMAGE DETECTION ---
                        # 1. Ask System
                        mime_type, _ = mimetypes.guess_type(filepath)
                        # 2. Check Extension (Fallback)
                        lower_name = name.lower()
                        is_image = (mime_type and mime_type.startswith('image')) or \
                                   lower_name.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))
                        
                        # Only run AI if enabled, in TARGET, AND it is an image
                        if privacy_scan_enabled and tag == "TARGET" and is_image:
                            print(f"[AI CHECK] Analyzing: {name}...") 
                            
                            ai_result = self.ai.analyze_image(filepath)
                            visual_data = json.dumps(ai_result)
                            
                            # Score > 0.40 triggers the flag
                            score = ai_result.get('nsfw_score', 0)
                            if score > 0.40:
                                is_flagged = True
                                print(f"🚩 FLAGGED: {name} (Score: {score})")

                        # Create Record
                        record = FileRecord(
                            mission_id=self.mission_id,
                            drive_id=drive_id,
                            path=filepath,
                            filename=name,
                            extension=os.path.splitext(name)[1].lower(),
                            size_bytes=stats.st_size,
                            created_at=stats.st_ctime,
                            file_hash=file_hash,
                            visual_hash=visual_data,
                            tag=tag,
                            is_flagged=is_flagged
                        )
                        session.add(record)
                        session.commit()

                    except Exception as e:
                        print(f"Error scanning {filepath}: {e}")
