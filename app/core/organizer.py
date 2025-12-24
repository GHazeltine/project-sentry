import os
import shutil
import time
import logging
import random
import string
import zipfile
from pathlib import Path
from sqlmodel import Session, select
from app.database.models import engine, FileTransaction, FileRecord

class Organizer:
    def __init__(self, mission_id: int):
        self.mission_id = mission_id

    # --- 1. VISUAL GROUPING ---
    def group_by_similarity(self):
        grouped_count = 0
        with Session(engine) as session:
            images = session.exec(select(FileRecord).where(
                FileRecord.mission_id == self.mission_id,
                FileRecord.visual_hash != None
            )).all()

            processed_ids = set()
            for i in range(len(images)):
                if images[i].id in processed_ids: continue
                if not self._is_valid_hash(images[i].visual_hash): continue

                group = [images[i]]
                try:
                    base_hash = int(images[i].visual_hash, 16)
                except ValueError: continue

                for j in range(i + 1, len(images)):
                    if images[j].id in processed_ids: continue
                    if not self._is_valid_hash(images[j].visual_hash): continue
                    try:
                        compare_hash = int(images[j].visual_hash, 16)
                        distance = bin(base_hash ^ compare_hash).count('1')
                        if distance <= 12: group.append(images[j])
                    except ValueError: continue

                if len(group) > 1:
                    for img in group: processed_ids.add(img.id)
                    group.sort(key=lambda x: x.created_at, reverse=True)
                    self._create_visual_stack(group, group[0])
                    grouped_count += 1
        return grouped_count

    # --- 2. SECURE VAULT ---
    def secure_privacy_files(self):
        vault_path = None
        password = None
        count = 0

        with Session(engine) as session:
            sensitive = session.exec(select(FileRecord).where(
                FileRecord.mission_id == self.mission_id,
                FileRecord.is_flagged == True
            )).all()

            if not sensitive: return 0, None, None

            first_file_path = Path(sensitive[0].path)
            if not first_file_path.exists(): return 0, None, None
            
            root_path = first_file_path.parent
            vault_name = f"SENTRY_SECURE_VAULT_{int(time.time())}"
            vault_dir = root_path / vault_name
            vault_dir.mkdir(exist_ok=True)
            (vault_dir / ".nomedia").touch()

            for f in sensitive:
                src = Path(f.path)
                if not src.exists(): continue
                dest = vault_dir / f.filename
                if dest.exists(): dest = vault_dir / f"{dest.stem}_{int(time.time())}{dest.suffix}"
                
                try:
                    shutil.move(str(src), str(dest))
                    f.path = str(dest)
                    f.tag = "SECURED"
                    session.add(f)
                    count += 1
                except Exception as e:
                    logging.error(f"Vault Move Error: {e}")

            session.commit()

            if count > 0:
                password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                zip_path = root_path / f"{vault_name}.zip"
                try:
                    with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
                        for root, dirs, files in os.walk(vault_dir):
                            for file in files:
                                zf.setpassword(password.encode('utf-8'))
                                zf.write(os.path.join(root, file), arcname=file)
                    vault_path = str(zip_path)
                except Exception as e:
                    vault_path = str(vault_dir)

        return count, vault_path, password

    # --- HELPERS ---
    def _is_valid_hash(self, h_str):
        if not h_str or len(h_str) < 4: return False
        try:
            int(h_str, 16)
            return True
        except ValueError: return False

    def undo_grouping(self):
        restored = 0
        with Session(engine) as session:
            txns = session.exec(select(FileTransaction).where(FileTransaction.mission_id == self.mission_id)).all()
            for txn in txns:
                if os.path.exists(txn.dest_path):
                    try:
                        os.makedirs(os.path.dirname(txn.src_path), exist_ok=True)
                        shutil.move(txn.dest_path, txn.src_path)
                        rec = session.exec(select(FileRecord).where(FileRecord.path == txn.dest_path)).first()
                        if rec:
                            rec.path = txn.src_path
                            session.add(rec)
                        session.delete(txn)
                        restored += 1
                    except: pass
            session.commit()
        return restored

    def _create_visual_stack(self, files: list[FileRecord], leader: FileRecord):
        base_name = Path(leader.filename).stem
        parent_dir = Path(leader.path).parent
        stack_dir = parent_dir / f"{base_name}_Set"
        if not stack_dir.exists(): stack_dir.mkdir()
        for f in files:
            if stack_dir.name in f.path: continue
            self._move_file(f, stack_dir, "VISUAL_STACK")

    def _move_file(self, record: FileRecord, dest_folder: Path, action: str):
        src = Path(record.path)
        dest = dest_folder / record.filename
        if dest.exists(): dest = dest_folder / f"{dest.stem}_{int(time.time())}{dest.suffix}"
        try:
            shutil.move(str(src), str(dest))
            with Session(engine) as session:
                txn = FileTransaction(mission_id=self.mission_id, timestamp=time.time(), action_type=action, src_path=str(src), dest_path=str(dest))
                session.add(txn)
                db_rec = session.get(FileRecord, record.id)
                db_rec.path = str(dest)
                db_rec.tag = "GROUPED"
                session.add(db_rec)
                session.commit()
        except Exception as e: logging.error(f"Move Error: {e}")
