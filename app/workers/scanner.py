import os
import hashlib
from sqlmodel import Session, select
from app.database.models import FileRecord, engine

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
IGNORE_LIST = {
    'Windows', 'Program Files', 'Program Files (x86)',
    '.git', 'node_modules', '$RECYCLE.BIN', 'System Volume Information'
}

def calculate_md5(file_path, block_size=65536):
    """Generates a unique MD5 hash for the file content."""
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            for buf in iter(lambda: f.read(block_size), b''):
                hasher.update(buf)
        return hasher.hexdigest()
    except Exception as e:
        print(f"[SCAN ERROR] Could not hash {file_path}: {e}")
        return None

def run_scanner(root_directory: str):
    """
    Scans a directory recursively.
    RESUME CAPABILITY: Checks DB before hashing.
    """
    print(f"--- STARTING SCAN: {root_directory} ---")
    
    with Session(engine) as session:
        for subdir, dirs, files in os.walk(root_directory):
            # 1. Filter Ignored Directories (In-place modification)
            dirs[:] = [d for d in dirs if d not in IGNORE_LIST]

            for filename in files:
                filepath = os.path.join(subdir, filename)

                # 2. RESUME LOGIC: Check if file is already in DB
                existing = session.exec(select(FileRecord).where(FileRecord.path == filepath)).first()
                if existing:
                    # print(f"[SKIP] Already scanned: {filename}")
                    continue

                # 3. Process New File
                try:
                    file_size = os.path.getsize(filepath)
                    file_hash = calculate_md5(filepath)

                    if file_hash:
                        new_record = FileRecord(
                            filename=filename,
                            path=filepath,
                            size_bytes=file_size,
                            hash=file_hash
                        )
                        session.add(new_record)
                        session.commit()
                        print(f"[+] Indexed: {filename}")

                except OSError as e:
                    print(f"[LOCKED] Skipping busy file: {filepath}")
                    continue

    print("--- SCAN COMPLETE ---")
