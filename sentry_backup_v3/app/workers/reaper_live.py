import sys
import os

# --- PATH HACK (MUST BE AT THE TOP) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)
# --------------------------------------

from sqlmodel import Session, select, func
from app.database.models import FileRecord, engine

# === CONFIGURATION ===
MASTER_DRIVE_ID = "My Book"
# =====================

def execute_reaper():
    print("="*60)
    print(f"💀 PROJECT SENTRY: LIVE REAPER PROTOCOL")
    print(f"🛡️  MASTER DRIVE (SAFE): {MASTER_DRIVE_ID}")
    print("="*60)
    
    confirm = input("⚠️  WARNING: This will PERMANENTLY DELETE files from secondary drives.\nType 'DESTROY' to continue: ")
    if confirm != "DESTROY":
        print("Abort.")
        return

    deleted_count = 0
    errors = 0
    bytes_reclaimed = 0

    with Session(engine) as session:
        # 1. Get the list of duplicate groups
        print("🔍 Scanning database for targets...")
        statement = (
            select(FileRecord.file_hash)
            .group_by(FileRecord.file_hash)
            .having(func.count(FileRecord.id) > 1)
        )
        duplicate_hashes = session.exec(statement).all()
        total_groups = len(duplicate_hashes)
        
        print(f"🎯 Found {total_groups} duplicate sets. Starting deletion...")
        
        for index, file_hash in enumerate(duplicate_hashes):
            # Fetch all files in this group
            files = session.exec(select(FileRecord).where(FileRecord.file_hash == file_hash)).all()
            
            keepers = [x for x in files if x.drive_id == MASTER_DRIVE_ID]
            candidates = [x for x in files if x.drive_id != MASTER_DRIVE_ID]
            
            # SAFETY CHECK: Only delete if we have a SAFE MASTER COPY
            if keepers and candidates:
                for target in candidates:
                    try:
                        # A. DELETE FROM DISK
                        if os.path.exists(target.path):
                            os.remove(target.path)
                        
                        # B. DELETE FROM DATABASE
                        session.delete(target)
                        
                        # Stats
                        bytes_reclaimed += target.size_bytes
                        deleted_count += 1
                        print(f"  [DEL] {target.path}")
                        
                    except Exception as e:
                        print(f"  [ERR] Could not delete {target.path}: {e}")
                        errors += 1

            # Commit changes to DB every 100 groups to save progress
            if index % 100 == 0:
                session.commit()
                print(f"  ...Progress: {index}/{total_groups} groups processed...")

        # Final Commit
        session.commit()

    # Final Report
    gb_saved = bytes_reclaimed / (1024**3)
    print("\n" + "="*60)
    print("✅ REAPER MISSION COMPLETE")
    print(f"🗑️  Files Deleted: {deleted_count}")
    print(f"💾 Space Reclaimed: {gb_saved:.2f} GB")
    print(f"⚠️  Errors: {errors}")
    print("="*60)

if __name__ == "__main__":
    execute_reaper()
