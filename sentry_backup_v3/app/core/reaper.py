import os
from sqlmodel import Session, select, func
from app.database.models import FileRecord, engine

class Reaper:
    def __init__(self):
        # No init params needed anymore; logic is Tag-based
        pass

    def analyze_duplicates(self):
        """
        New Logic:
        1. Find duplicate hashes.
        2. Check if at least ONE copy exists in a 'MASTER' (Protected) path.
        3. If yes, mark all copies in 'TARGET' (Clean) paths for death.
        """
        kill_list = []
        with Session(engine) as session:
            # Get hashes with duplicates
            statement = (
                select(FileRecord.file_hash)
                .group_by(FileRecord.file_hash)
                .having(func.count(FileRecord.id) > 1)
            )
            
            duplicate_hashes = session.exec(statement).all()
            
            for f_hash in duplicate_hashes:
                files = session.exec(select(FileRecord).where(FileRecord.file_hash == f_hash)).all()
                
                # The Critical Check
                has_protected_copy = any(f.tag == "MASTER" for f in files)
                candidates = [f for f in files if f.tag == "TARGET"]
                
                # Only delete TARGET files if a MASTER copy exists
                if has_protected_copy and candidates:
                    for c in candidates:
                        kill_list.append({
                            "path": c.path,
                            "size": c.size_bytes,
                            "id": c.id
                        })
        return kill_list

    def execute_cleanup(self):
        kill_list = self.analyze_duplicates()
        deleted = 0
        errors = 0
        
        with Session(engine) as session:
            for item in kill_list:
                try:
                    if os.path.exists(item['path']):
                        os.remove(item['path'])
                    
                    # Remove from DB
                    rec = session.get(FileRecord, item['id'])
                    if rec: session.delete(rec)
                    deleted += 1
                except Exception:
                    errors += 1
            session.commit()
            
        return {"deleted": deleted, "errors": errors}
