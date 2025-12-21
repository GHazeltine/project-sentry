import os
import hashlib
import json
import mimetypes
from sqlmodel import Session
from app.database.models import engine, FileRecord
from app.core.ai_engine import AIEngine

class Scanner:
    def __init__(self, mission_id: int):
        self.mission_id = mission_id
        self.ai = AIEngine()

    def scan_directory(self, root_path: str, tag: str, drive_id: str, privacy_scan_enabled: bool = False):
        print(f"[Scanner] Starting scan on: {root_path} (Privacy Scan: {privacy_scan_enabled})")
        
        if not os.path.exists(root_path):
            print(f"[Scanner] Path not found: {root_path}")
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
                        mime_type, _ = mimetypes.guess_type(filepath)
                        lower_name = name.lower()
                        is_image = (mime_type and mime_type.startswith('image')) or \
                                   lower_name.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))
                        
                        # Only run AI if enabled, in TARGET, AND it is an image
                        if privacy_scan_enabled and tag == "TARGET" and is_image:
                            print(f"[AI CHECK] Analyzing: {name}...") 
                            ai_result = self.ai.analyze_image(filepath)
                            visual_data = json.dumps(ai_result)
                            
                            score = ai_result.get('nsfw_score', 0)
                            if score > 0.40:
                                is_flagged = True
                                print(f"🚩 FLAGGED: {name} (Score: {score})")

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

    def calculate_md5(self, filepath):
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return None
