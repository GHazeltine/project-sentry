import os
import sys

# === CONFIGURATION ===
TARGET_ROOT = "/media/greg/RyanNicole"
# =====================

def run_janitor():
    print("="*60)
    print(f"🧹 PROJECT SENTRY: GHOST TOWN CLEANUP")
    print(f"🎯 TARGET ZONE: {TARGET_ROOT}")
    print("="*60)
    
    if not os.path.exists(TARGET_ROOT):
        print(f"❌ Error: Target path not found: {TARGET_ROOT}")
        return

    print("🔍 Scanning for empty directories... (This may take a moment)")
    
    empty_dirs = []
    
    # os.walk with topdown=False is critical.
    # It lets us delete the child, then see if the parent is empty.
    for root, dirs, files in os.walk(TARGET_ROOT, topdown=False):
        for name in dirs:
            full_path = os.path.join(root, name)
            try:
                # Check if directory is actually empty
                if not os.listdir(full_path):
                    empty_dirs.append(full_path)
            except OSError:
                pass # Skip folders we can't read

    count = len(empty_dirs)
    if count == 0:
        print("✅ The drive is already clean! No empty folders found.")
        return

    print(f"👻 Found {count} empty 'Ghost Folders'.")
    print("Example targets:")
    for d in empty_dirs[:5]:
        print(f"  - {d}")
    if count > 5: print("  ...and many more.")
    
    print("-" * 60)
    confirm = input("⚠️  Ready to dissolve these ghosts? Type 'CLEANUP' to confirm: ")
    
    if confirm != "CLEANUP":
        print("Abort.")
        return

    print("\n🧹 Scrubbing directories...")
    deleted = 0
    errors = 0
    
    for folder in empty_dirs:
        try:
            os.rmdir(folder)
            deleted += 1
            # Optional: Print every 100 deletions so we know it's working
            if deleted % 100 == 0:
                print(f"  ...removed {deleted} folders...")
        except OSError as e:
            errors += 1
    
    print("="*60)
    print(f"✨ CLEANUP COMPLETE")
    print(f"🗑️  Folders Removed: {deleted}")
    print(f"⚠️  Errors: {errors}")

if __name__ == "__main__":
    run_janitor()
# --- Compatibility wrapper (server.py expects "Janitor") ---

class Janitor:
    """
    Thin wrapper to keep server.py stable.
    If server.py calls janitor.run(...) or janitor.clean(...),
    we route that to the existing run_janitor() for now.
    """

    def run(self, *args, **kwargs):
        return run_janitor()

    def clean(self, *args, **kwargs):
        return run_janitor()
