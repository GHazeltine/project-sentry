import sys
import os

# --- PATH HACK ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)
# -----------------

from sqlmodel import Session, select, func
from app.database.models import FileRecord, engine

# === CONFIGURATION ===
MASTER_DRIVE_ID = "My Book"  # The Survivor
# =====================

def generate_kill_list():
    print(f"💀 INITIALIZING REAPER PROTOCOL (Dry Run)...")
    print(f"🛡️  MASTER DRIVE (PROTECTED): {MASTER_DRIVE_ID}")
    
    report_file = "kill_list_preview.txt"
    bytes_to_save = 0
    files_to_delete = 0
    
    with Session(engine) as session:
        # 1. Find all hashes that have duplicates
        # (This SQL is optimized for speed)
        statement = (
            select(FileRecord.file_hash)
            .group_by(FileRecord.file_hash)
            .having(func.count(FileRecord.id) > 1)
        )
        duplicate_hashes = session.exec(statement).all()
        
        print(f"🔍 Analyzing {len(duplicate_hashes)} duplicate groups...")
        
        with open(report_file, "w") as f:
            f.write("PROJECT SENTRY: DELETION PREVIEW\n")
            f.write(f"Master Drive Rule: KEEP files on '{MASTER_DRIVE_ID}'\n")
            f.write("=" * 60 + "\n\n")
            
            for file_hash in duplicate_hashes:
                # Get all files in this group
                files = session.exec(select(FileRecord).where(FileRecord.file_hash == file_hash)).all()
                
                # Sort them: Keepers vs. Candidates
                keepers = [x for x in files if x.drive_id == MASTER_DRIVE_ID]
                candidates = [x for x in files if x.drive_id != MASTER_DRIVE_ID]
                
                # LOGIC CHECK:
                # We only delete if we actually HAVE a safe copy on the Master Drive.
                if keepers and candidates:
                    f.write(f"HASH: {file_hash[:8]}...\n")
                    
                    for keep in keepers:
                        f.write(f"  ✅ KEEP: {keep.path}\n")
                        
                    for kill in candidates:
                        f.write(f"  ❌ KILL: {kill.path}\n")
                        bytes_to_save += kill.size_bytes
                        files_to_delete += 1
                        
                    f.write("-" * 40 + "\n")

    # Summary
    gb_saved = bytes_to_save / (1024**3)
    print(f"\n✅ ANALYSIS COMPLETE.")
    print(f"📄 Preview saved to: {report_file}")
    print(f"📉 Potential Storage Reclaimed: {gb_saved:.2f} GB")
    print(f"🗑️  Files marked for death: {files_to_delete}")

if __name__ == "__main__":
    generate_kill_list()
