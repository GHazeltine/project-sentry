import os
import hashlib
import sqlite3

class Scanner:
    """
    Module B: The Surveyor
    Responsibility: Index files, calculate cryptographic hashes, and build the map.
    """
    
    def __init__(self, db_path="sentry_index.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.setup_db()
        
    def setup_db(self):
        # We drop the table every time to ensure a fresh scan for the current session.
        # In a permanent deployment, we might keep this, but for now, fresh is safer.
        self.cursor.execute("DROP TABLE IF EXISTS files")
        self.cursor.execute('''
            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT,
                filename TEXT,
                size INTEGER,
                file_hash TEXT,
                tag TEXT
            )
        ''')
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON files (file_hash)")
        self.conn.commit()

    def calculate_hash(self, filepath, block_size=65536):
        """
        Generates a BLAKE2b hash for the file.
        Efficiently reads in chunks to handle large video files without crashing RAM.
        """
        hasher = hashlib.blake2b()
        try:
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(block_size)
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except OSError:
            return None

    def scan_directory(self, root_path, tag):
        """
        Walks the directory, hashes files, and logs them to the DB.
        tag: 'MASTER' (Gold Drive) or 'TARGET' (Drive to clean)
        """
        print(f"   -> Indexing {tag} zone: {root_path}")
        
        count = 0
        batch = []
        
        for root, dirs, files in os.walk(root_path):
            # Optimization: Skip hidden system folders immediately
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['$RECYCLE.BIN', 'System Volume Information']]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                full_path = os.path.join(root, file)
                
                try:
                    size = os.path.getsize(full_path)
                    # Skip empty files (size 0)
                    if size == 0:
                        continue
                        
                    file_hash = self.calculate_hash(full_path)
                    
                    if file_hash:
                        batch.append((full_path, file, size, file_hash, tag))
                        count += 1
                        
                        # Batch insert every 1000 files for speed
                        if len(batch) >= 1000:
                            self.cursor.executemany("INSERT INTO files (path, filename, size, file_hash, tag) VALUES (?, ?, ?, ?, ?)", batch)
                            self.conn.commit()
                            batch = []
                            print(f"      ...indexed {count} files...", end='\r')
                            
                except (OSError, PermissionError):
                    print(f"      [!] Skipped (Access Denied): {file}")
                    continue

        # Commit leftovers
        if batch:
            self.cursor.executemany("INSERT INTO files (path, filename, size, file_hash, tag) VALUES (?, ?, ?, ?, ?)", batch)
            self.conn.commit()
            
        print(f"\n   ✅ Complete. Indexed {count} files in {tag}.")

    def close(self):
        self.conn.close()
