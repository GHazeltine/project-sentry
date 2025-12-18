import os
import hashlib
from typing import List
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
        # Log locked files but don't crash
        # print(f"[LOCKED] Could not read {file_path}")
        return None

def run_scanner(target_paths: List[str]):
    """
    Scans a LIST of directories recursively.
    """
    print(f"--- STARTING MULTI-TARGET SCAN ---")
    print(f"Targets: {target_paths}")
    
    with Session(engine) as session:
        for root_directory in target_paths:
            if not os.path.exists(root_directory):
                print(f"[ERROR] Path not found: {root_directory}")
                continue

            for subdir, dirs, files in os.walk(root_directory):
                # 1. Filter Ignored Directories
                dirs[:] = [d for d in dirs if d not in IGNORE_LIST]

                for filename in files:
                    filepath = os.path.join(subdir, filename)

                    # 2. RESUME LOGIC: Check DB first
                    existing = session.exec(select(FileRecord).where(FileRecord.path == filepath)).first()
                    if existing:
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

                    except OSError:
                        # Skip locked/system files quietly
                        continue

    print("--- SCAN COMPLETE ---")
