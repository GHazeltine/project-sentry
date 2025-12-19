import os
from sqlmodel import Session, select, func
from app.database.models import FileRecord, engine

class Reaper:
    def __init__(self, master_drive_id: str):
        self.master_drive_id = master_drive_id

    def analyze_duplicates(self):
        kill_list = []
        with Session(engine) as session:
            statement = (
                select(FileRecord.file_hash)
                .group_by(FileRecord.file_hash)
                .having(func.count(FileRecord.id) > 1)
            )
            for f_hash in session.exec(statement).all():
                files = session.exec(select(FileRecord).where(FileRecord.file_hash == f_hash)).all()
                keepers = [x for x in files if x.drive_id == self.master_drive_id]
                candidates = [x for x in files if x.drive_id != self.master_drive_id]
                if keepers and candidates:
                    for c in candidates:
                        kill_list.append({"path": c.path, "size": c.size_bytes, "id": c.id})
        return kill_list

    def execute_cleanup(self):
        kill_list = self.analyze_duplicates()
        deleted = 0
        errors = 0
        with Session(engine) as session:
            for item in kill_list:
                try:
                    if os.path.exists(item['path']): os.remove(item['path'])
                    rec = session.get(FileRecord, item['id'])
                    if rec: session.delete(rec)
                    deleted += 1
                except: errors += 1
            session.commit()
        return {"deleted": deleted, "errors": errors}
