import os
import hashlib
import sqlite3
# Import the new AI Processor
from app.core.ai_processor import AIProcessor

class Scanner:
    """
    Module B: The Surveyor (AI Enhanced)
    Responsibility: Index files, calculate crypto hashes (CPU), and visual hashes (NPU).
    """
    
    def __init__(self, db_path="sentry_index.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.setup_db()
        # Initialize the AI Brain
        self.ai = AIProcessor()
        
    def setup_db(self):
        self.cursor.execute("DROP TABLE IF EXISTS files")
        # Added 'visual_hash' column
        self.cursor.execute('''
            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT,
                filename TEXT,
                size INTEGER,
                file_hash TEXT,
                visual_hash TEXT, 
                tag TEXT
            )
        ''')
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON files (file_hash)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_vis ON files (visual_hash)")
        self.conn.commit()

    def calculate_hash(self, filepath, block_size=65536):
        hasher = hashlib.blake2b()
        try:
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(block_size)
                    if not data: break
                    hasher.update(data)
            return hasher.hexdigest()
        except OSError:
            return None

    def scan_directory(self, root_path, tag):
        print(f"   -> Indexing {tag} zone: {root_path}")
        count = 0
        batch = []
        
        # Extensions that trigger the AI Processor
        visual_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')

        for root, dirs, files in os.walk(root_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['$RECYCLE.BIN']]
            
            for file in files:
                if file.startswith('.'): continue
                full_path = os.path.join(root, file)
                
                try:
                    size = os.path.getsize(full_path)
                    if size == 0: continue
                        
                    # 1. CPU Task: Exact Hash
                    file_hash = self.calculate_hash(full_path)
                    
                    # 2. NPU Task: Visual Hash (Only for images)
                    visual_hash = "N/A"
                    if file.lower().endswith(visual_exts):
                        visual_hash = self.ai.get_visual_hash(full_path)

                    if file_hash:
                        batch.append((full_path, file, size, file_hash, visual_hash, tag))
                        count += 1
                        
                        if len(batch) >= 1000:
                            self._commit_batch(batch)
                            batch = []
                            print(f"      ...indexed {count} files...", end='\r')
                            
                except (OSError, PermissionError):
                    continue

        if batch:
            self._commit_batch(batch)
            
        print(f"\n   ✅ Complete. Indexed {count} files in {tag}.")

    def _commit_batch(self, batch):
        self.cursor.executemany(
            "INSERT INTO files (path, filename, size, file_hash, visual_hash, tag) VALUES (?, ?, ?, ?, ?, ?)", 
            batch
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
