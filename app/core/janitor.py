import shutil
import os
import hashlib

def calculate_md5(file_path, block_size=65536):
    """Re-calculates hash to verify data integrity."""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for buf in iter(lambda: f.read(block_size), b''):
            hasher.update(buf)
    return hasher.hexdigest()

def secure_move(source_path: str, destination_folder: str) -> bool:
    """
    Moves a file with cryptographic verification.
    1. Copies file to destination.
    2. Calculates hash of NEW file.
    3. Compares with OLD file.
    4. ONLY deletes old file if hashes match perfectly.
    """
    if not os.path.exists(source_path):
        print(f"[JANITOR] Error: Source not found {source_path}")
        return False

    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    filename = os.path.basename(source_path)
    dest_path = os.path.join(destination_folder, filename)

    # Handle naming conflicts (don't overwrite existing duplicates)
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(destination_folder, f"{base}_COPY{counter}{ext}")
            counter += 1

    print(f"[JANITOR] Copying {source_path} -> {dest_path}...")
    
    try:
        # 1. Copy
        shutil.copy2(source_path, dest_path)

        # 2. Verify
        source_hash = calculate_md5(source_path)
        dest_hash = calculate_md5(dest_path)

        if source_hash == dest_hash:
            # 3. Delete Source (Safe)
            print("[JANITOR] Verification Successful. Removing original.")
            os.remove(source_path)
            return True
        else:
            # 3. Abort (Unsafe)
            print(f"[ALARM] HASH MISMATCH! {source_hash} vs {dest_hash}")
            print("[JANITOR] Deleting corrupted copy. Original untouched.")
            os.remove(dest_path)
            return False

    except Exception as e:
        print(f"[JANITOR] Error during move: {e}")
        return False
