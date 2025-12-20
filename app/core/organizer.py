import os
import shutil
import time
import logging
from pathlib import Path
from sqlmodel import Session
from app.database.models import engine, FileTransaction, FileRecord

class Organizer:
    """
    The Librarian.
    Handles 'Smart Stacking' (RAW+JPG) and 'Privacy Vault' (NSFW) moves.
    """
    
    def __init__(self, mission_id: int):
        self.mission_id = mission_id

    def smart_stack(self, file_record: FileRecord, siblings: list[FileRecord]):
        """
        Groups a file and its siblings into a folder.
        Example: IMG_001.JPG + IMG_001.ARW -> /IMG_001_Grouped/
        """
        # 1. Determine the "Leader" (usually the JPG or the last modified)
        # For simplicity, we name the folder after the base filename
        base_name = Path(file_record.filename).stem
        parent_dir = Path(file_record.path).parent
        
        # 2. Create the Group Folder
        group_folder = parent_dir / f"{base_name}_Grouped"
        if not group_folder.exists():
            group_folder.mkdir()
            logging.info(f"📁 Created Stack: {group_folder}")

        # 3. Move all siblings
        for sibling in siblings:
            self._move_file(sibling, group_folder, "GROUP_RAW")

    def privacy_quarantine(self, file_record: FileRecord, vault_root: str):
        """
        Moves a sensitive file to the Privacy Vault.
        """
        vault_path = Path(vault_root)
        if not vault_path.exists():
            vault_path.mkdir(parents=True)
            
        self._move_file(file_record, vault_path, "PRIVACY_MOVE")

    def _move_file(self, record: FileRecord, dest_folder: Path, action: str):
        """
        Safe Move with DB Logging.
        """
        src = Path(record.path)
        dest = dest_folder / record.filename
        
        # Avoid overwriting
        if dest.exists():
            timestamp = int(time.time())
            dest = dest_folder / f"{dest.stem}_{timestamp}{dest.suffix}"

        try:
            # 1. Physical Move
            shutil.move(str(src), str(dest))
            
            # 2. Log Transaction (The Undo Receipt)
            with Session(engine) as session:
                txn = FileTransaction(
                    mission_id=self.mission_id,
                    timestamp=time.time(),
                    action_type=action,
                    src_path=str(src),
                    dest_path=str(dest)
                )
                session.add(txn)
                
                # 3. Update File Record
                record.path = str(dest)
                session.add(record)
                
                session.commit()
                
            logging.info(f"✅ Moved: {src.name} -> {dest_folder.name}")
            
        except Exception as e:
            logging.error(f"❌ Failed to move {src}: {e}")
