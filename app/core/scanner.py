import os
import time
import logging
from sqlmodel import Session, select
from app.database.models import engine, FileRecord, ScanMission
from nudenet import NudeDetector  # Default CPU NudeNet

class Scanner:
    def __init__(self, mission_id: int):
        self.mission_id = mission_id
        # Initialize standard NudeNet (Runs on CPU)
        try:
            self.detector = NudeDetector()
        except Exception as e:
            logging.error(f"AI Init Failed: {e}")
            self.detector = None

    def scan_directory(self, path: str, drive_id: str, drive_label: str, enable_privacy: bool):
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4')):
                    full_path = os.path.join(root, file)
                    size = os.path.getsize(full_path)
                    
                    # 1. AI Scan (If Privacy Enabled)
                    is_flagged = False
                    if enable_privacy and self.detector:
                        try:
                            # Detect returns list of dicts: [{'class': 'EXPOSED...', 'score': 0.8}]
                            detections = self.detector.detect(full_path)
                            for d in detections:
                                if d['score'] > 0.45:  # Sensitivity Threshold
                                    is_flagged = True
                                    break
                        except:
                            pass # Skip corrupt images

                    # 2. Save to DB
                    with Session(engine) as session:
                        # Simple Visual Hash (Placeholder for complex hashing)
                        # In V4/V5 we will use proper perceptual hashing here
                        v_hash = str(size) 

                        record = FileRecord(
                            mission_id=self.mission_id,
                            drive_id=drive_id,
                            path=full_path,
                            filename=file,
                            extension=file.split('.')[-1],
                            size_bytes=size,
                            created_at=time.time(),
                            visual_hash=v_hash,
                            tag="DUPLICATE" if "Copy" in file else "scanned", # Simple duplicate logic for test
                            is_flagged=is_flagged
                        )
                        session.add(record)
                        session.commit()
