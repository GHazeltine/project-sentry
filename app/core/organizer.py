import os
import shutil
import time
import logging
from pathlib import Path
from sqlmodel import Session, select
from app.database.models import engine, FileTransaction, FileRecord

class Organizer:
    def __init__(self, mission_id: int):
        self.mission_id = mission_id

    def group_by_similarity(self):
        """Groups visually similar images into folders named after the NEWEST file."""
        grouped_count = 0
        
        with Session(engine) as session:
            # Get only images that actually have a visual hash
            images = session.exec(select(FileRecord).where(FileRecord.mission_id == self.mission_id, FileRecord.visual_hash != None)).all()
            
            processed_ids = set()

            for i in range(len(images)):
                if images[i].id in processed_ids: continue
                
                group = [images[i]]
                base_hash = int(images[i].visual_hash, 16)
                
                # Find friends
                for j in range(i + 1, len(images)):
                    if images[j].id in processed_ids: continue
                    
                    compare_hash = int(images[j].visual_hash, 16)
                    distance = bin(base_hash ^ compare_hash).count('1')
                    
                    # Distance < 10 allows for resizing, cropping, and light edits
                    if distance <= 10:
                        group.append(images[j])
                
                if len(group) > 1:
                    # Mark all as processed
                    for img in group: processed_ids.add(img.id)
                    
                    # INTELLIGENT NAMING: Sort by Creation Date (Newest First)
                    # We want the "Latest Edit" to dictate the folder name
                    group.sort(key=lambda x: x.created_at, reverse=True)
                    leader = group[0]
                    
                    self._create_visual_stack(group, leader)
                    grouped_count += 1
                    
        return grouped_count

    def undo_grouping(self):
        """Reverses all moves for this mission."""
        restored = 0
        with Session(engine) as session:
            # Find all moves for this mission
            txns = session.exec(select(FileTransaction).where(FileTransaction.mission_id == self.mission_id)).all()
            
            for txn in txns:
                if os.path.exists(txn.dest_path):
                    try:
                        # Move back to Source
                        # Create dir if it vanished (e.g. ghost folder cleanup)
                        os.makedirs(os.path.dirname(txn.src_path), exist_ok=True)
                        shutil.move(txn.dest_path, txn.src_path)
                        
                        # Update DB Record
                        rec = session.exec(select(FileRecord).where(FileRecord.path == txn.dest_path)).first()
                        if rec:
                            rec.path = txn.src_path
                            session.add(rec)
                        
                        # Delete the transaction log (history rewritten)
                        session.delete(txn)
                        restored += 1
                    except Exception as e:
                        logging.error(f"Undo Failed for {txn.dest_path}: {e}")
            
            session.commit()
        return restored

    def _create_visual_stack(self, files: list[FileRecord], leader: FileRecord):
        # Folder Name: "Foly_wedding_Set" based on "Foly_wedding.jpg"
        base_name = Path(leader.filename).stem
        parent_dir = Path(leader.path).parent
        folder_name = f"{base_name}_Set"
        stack_dir = parent_dir / folder_name
        
        if not stack_dir.exists():
            stack_dir.mkdir()
            
        for f in files:
            # Don't move if it's already in a folder with that name (idempotency)
            if stack_dir.name in f.path: continue
            self._move_file(f, stack_dir, "VISUAL_STACK")

    def _move_file(self, record: FileRecord, dest_folder: Path, action: str):
        src = Path(record.path)
        dest = dest_folder / record.filename
        
        if dest.exists():
            timestamp = int(time.time())
            dest = dest_folder / f"{dest.stem}_{timestamp}{dest.suffix}"

        try:
            shutil.move(str(src), str(dest))
            
            with Session(engine) as session:
                txn = FileTransaction(
                    mission_id=self.mission_id,
                    timestamp=time.time(),
                    action_type=action,
                    src_path=str(src),
                    dest_path=str(dest)
                )
                session.add(txn)
                
                db_rec = session.get(FileRecord, record.id)
                db_rec.path = str(dest)
                session.add(db_rec)
                session.commit()
                
        except Exception as e:
            logging.error(f"Move Error: {e}")
