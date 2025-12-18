import os
import sys
# Import your actual application modules
from app.core.scanner import Scanner
from app.core.reaper import Reaper
from app.core.janitor import Janitor

def run_sim():
    # Hardcoded paths to our local sandbox
    cwd = os.getcwd()
    gold_path = os.path.join(cwd, "TEST_LAB/FAKE_GOLD_DRIVE")
    dirty_path = os.path.join(cwd, "TEST_LAB/FAKE_DIRTY_DRIVE")

    print("="*60)
    print("🧪 SENTRY SIMULATION: DRY RUN")
    print("="*60)

    # --- TEST MODULE B: SCANNER ---
    print("\n[MODULE B] Running Scanner...")
    scanner = Scanner(db_path="test_index.db") # Use a separate DB for testing
    
    print("   -> Indexing Gold...")
    scanner.scan_directory(gold_path, tag="MASTER")
    
    print("   -> Indexing Dirty...")
    scanner.scan_directory(dirty_path, tag="TARGET")

    # --- TEST MODULE D: REAPER ---
    print("\n[MODULE D] Running Reaper...")
    reaper = Reaper(master_path=gold_path, db_path="test_index.db")
    duplicates = reaper.analyze()

    if not duplicates:
        print("❌ TEST FAILED: No duplicates found (expected 1).")
        sys.exit(1)
        
    print(f"   -> Detected {len(duplicates)} duplicates.")
    
    print("\n⚠️  Simulating Deletion...")
    reaper.execute(duplicates)

    # --- TEST MODULE E: JANITOR ---
    print("\n[MODULE E] Running Ghostbuster...")
    janitor = Janitor()
    janitor.clean(dirty_path)

    # --- FINAL VERIFICATION ---
    print("\n🔎 VERIFYING RESULTS...")
    
    # 1. Did the duplicate die?
    dup_path = os.path.join(dirty_path, "backup_2023", "copy_of_photo.jpg")
    if not os.path.exists(dup_path):
        print("✅ SUCCESS: Duplicate file was killed.")
    else:
        print("❌ FAILURE: Duplicate file still exists.")

    # 2. Did the survivor live?
    survivor_path = os.path.join(dirty_path, "unique_project.doc")
    if os.path.exists(survivor_path):
        print("✅ SUCCESS: Unique file survived.")
    else:
        print("❌ FAILURE: Unique file was accidentally deleted!")

    # 3. Did the ghost town vanish?
    ghost_root = os.path.join(dirty_path, "old_stuff")
    if not os.path.exists(ghost_root):
        print("✅ SUCCESS: Ghost folders dissolved.")
    else:
        print("❌ FAILURE: Empty folders still exist.")

    print("\n🧪 SIMULATION COMPLETE.")

if __name__ == "__main__":
    run_sim()
