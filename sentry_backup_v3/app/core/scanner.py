import os
import hashlib
import mimetypes
from sqlmodel import Session
from app.database.models import engine, FileRecord
from app.core.ai_engine import AIEngine
from app.core.ai_processor import AIProcessor

class Scanner:
    def __init__(self, mission_id: int):
        self.mission_id = mission_id
        self.ai_privacy = AIEngine()       # For Nudity/Privacy
        self.ai_vision = AIProcessor()     # For Similarity/Grouping

    def scan_directory(self, root_path: str, tag: str, drive_id: str, privacy_scan_enabled: bool = False):
        print(f"[Scanner] Starting scan on: {root_path}")
        
        if not os.path.exists(root_path):
            return

        with Session(engine) as session:
            for dirpath, _, filenames in os.walk(root_path):
                for name in filenames:
                    filepath = os.path.join(dirpath, name)
                    try:
                        stats = os.stat(filepath)
                        file_hash = self.calculate_md5(filepath)
                        
                        # --- VISUAL PROCESSING ---
                        visual_hash = None
                        is_flagged = False
                        
                        mime_type, _ = mimetypes.guess_type(filepath)
                        lower_name = name.lower()
                        is_image = (mime_type and mime_type.startswith('image')) or \
                                   lower_name.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.cr2', '.arw', '.dng'))

                        if is_image:
                            # 1. GENERATE FINGERPRINT (Always, for potential grouping)
                            try:
                                visual_hash = self.ai_vision.get_visual_hash(filepath)
                            except:
                                visual_hash = None

                            # 2. PRIVACY SCAN (Optional)
                            if privacy_scan_enabled and tag == "TARGET":
                                try:
                                    ai_result = self.ai_privacy.analyze_image(filepath)
                                    score = ai_result.get('nsfw_score', 0)
                                    if score > 0.40:
                                        is_flagged = True
                                        print(f"🚩 FLAGGED: {name}")
                                except: pass

                        record = FileRecord(
                            mission_id=self.mission_id,
                            drive_id=drive_id,
                            path=filepath,
                            filename=name,
                            extension=os.path.splitext(name)[1].lower(),
                            size_bytes=stats.st_size,
                            created_at=stats.st_ctime,
                            file_hash=file_hash,
                            visual_hash=visual_hash,
                            tag=tag,
                            is_flagged=is_flagged
                        )
                        session.add(record)
                        
                        if len(session.new) > 50: session.commit()

                    except Exception as e:
                        print(f"Error scanning {filepath}: {e}")
            
            session.commit()

    def calculate_md5(self, filepath):
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return None
