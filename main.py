import sys
import os
import time

# Import our new modules (We will build these files next)
# Note: Python needs to know 'app' is a package.
try:
    from app.core.drive_manager import DriveManager
    from app.core.scanner import Scanner
    from app.core.reaper import Reaper
    from app.core.janitor import Janitor
except ImportError as e:
    print("❌ Configuration Error: Could not import modules.")
    print(f"   Details: {e}")
    print("   Make sure you are running this from the root 'project-sentry' folder.")
    sys.exit(1)

def main():
    print("="*60)
    print("🛡️  PROJECT SENTRY: AUTONOMOUS DATA RECOVERY")
    print("="*60)
    
    # --- PHASE 1: HARDWARE DISCOVERY (Module A) ---
    print("\n🔍 Detecting Hardware...")
    dm = DriveManager()
    drives = dm.detect_drives()
    
    if not drives:
        print("❌ No external drives detected. Please connect a drive.")
        sys.exit(1)
        
    dm.display_drives(drives)
    
    # --- PHASE 2: HEALTH CHECK & AUTO-FIX ---
    print("\n🩺 Performing Health & Permission Checks...")
    for drive in drives:
        # This checks for Read-Only status, Dirty Bits, or Wrong Owners
        status = dm.health_check(drive)
        
        if status == "LOCKED":
            print(f"⚠️  Drive '{drive['label']}' is Read-Only ({drive['fstype']}).")
            fix = input(f"   Attempt Auto-Unlock? (y/n): ")
            if fix.lower() == 'y':
                dm.unlock_drive(drive)
        elif status == "PERMISSION_DENIED":
            print(f"⚠️  Drive '{drive['label']}' has wrong ownership.")
            fix = input(f"   Claim ownership for user {os.environ.get('USER')}? (y/n): ")
            if fix.lower() == 'y':
                dm.claim_ownership(drive)

    # --- PHASE 3: CONFIGURATION (Module C - The Arbiter) ---
    print("\n🎯 MISSION CONFIGURATION")
    print("Available Drives:")
    for i, d in enumerate(drives):
        print(f"  [{i+1}] {d['label']} ({d['mountpoint']})")

    try:
        gold_idx = int(input("\nSelect GOLD MASTER drive (enter number): ")) - 1
        gold_path = drives[gold_idx]['mountpoint']
        
        target_indices = input("Select TARGET drives to clean (comma separated, e.g., '1,3'): ").split(',')
        target_paths = [drives[int(idx)-1]['mountpoint'] for idx in target_indices]
    except (ValueError, IndexError):
        print("❌ Invalid selection. Aborting.")
        sys.exit(1)

    print(f"\n🔒 GOLD MASTER: {gold_path}")
    print(f"🎯 TARGETS:     {target_paths}")
    input("Press Enter to begin Scanning...")

    # --- PHASE 4: SCANNING (Module B) ---
    scanner = Scanner()
    
    print(f"\nrunning Indexer on GOLD: {gold_path}...")
    scanner.scan_directory(gold_path, tag="MASTER")
    
    for t_path in target_paths:
        print(f"running Indexer on TARGET: {t_path}...")
        scanner.scan_directory(t_path, tag="TARGET")
        
    # --- PHASE 5: EXECUTION (Module D - The Reaper) ---
    print("\n💀 REAPER ANALYSIS READY")
    reaper = Reaper(master_path=gold_path)
    
    # Generate the "Kill List"
    duplicates = reaper.analyze()
    
    if not duplicates:
        print("✅ No duplicates found. Your drives are clean.")
        sys.exit(0)

    print(f"⚠️  Found {len(duplicates)} files to delete.")
    confirm = input("⚠️  EXECUTE DELETION? Type 'DESTROY' to confirm: ")
    
    if confirm == "DESTROY":
        reaper.execute(duplicates)
        
        # --- PHASE 6: CLEANUP (Module E - The Ghostbuster) ---
        print("\n🧹 Initializing Ghostbuster (Janitor)...")
        janitor = Janitor()
        for t_path in target_paths:
            janitor.clean(t_path)
            
    print("\n✅ MISSION COMPLETE.")

if __name__ == "__main__":
    main()
