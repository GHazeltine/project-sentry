import os
import shutil

def create_file(path, content="test content"):
    with open(path, "w") as f:
        f.write(content)

def setup():
    root = "TEST_LAB"
    gold = os.path.join(root, "FAKE_GOLD_DRIVE")
    dirty = os.path.join(root, "FAKE_DIRTY_DRIVE")

    # 1. Clean slate
    if os.path.exists(root):
        shutil.rmtree(root)
    
    os.makedirs(gold)
    os.makedirs(dirty)
    
    print("🧪 CREATING TEST LAB...")

    # --- SCENARIO 1: The Duplicate (Should die) ---
    # Same content, different name, different folder
    create_file(os.path.join(gold, "vacation_photo.jpg"), "DATA_BLOCK_A")
    
    os.makedirs(os.path.join(dirty, "backup_2023"))
    create_file(os.path.join(dirty, "backup_2023", "copy_of_photo.jpg"), "DATA_BLOCK_A")
    print("   -> Created Duplicate Pair: 'vacation_photo.jpg'")

    # --- SCENARIO 2: The Survivor (Should live) ---
    # Only exists on Dirty Drive
    create_file(os.path.join(dirty, "unique_project.doc"), "DATA_BLOCK_B")
    print("   -> Created Unique File: 'unique_project.doc'")

    # --- SCENARIO 3: The Ghost Town (Should vanish) ---
    # Nested empty folders
    ghost_path = os.path.join(dirty, "old_stuff", "empty_folder", "void")
    os.makedirs(ghost_path)
    print("   -> Created Ghost Town: /old_stuff/empty_folder/void")

    # --- SCENARIO 4: The Locked File (Should trigger error handling) ---
    # We simulate a permission issue by making it read-only
    locked_path = os.path.join(dirty, "locked_file.txt")
    create_file(locked_path, "DATA_BLOCK_C")
    os.chmod(locked_path, 0o444) # Read-only
    print("   -> Created Locked File (Read-Only): 'locked_file.txt'")
    
    print("\n✅ TEST ENVIRONMENT READY.")
    print(f"   GOLD PATH:   {os.path.abspath(gold)}")
    print(f"   DIRTY PATH:  {os.path.abspath(dirty)}")

if __name__ == "__main__":
    setup()
