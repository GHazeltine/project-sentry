import os
import sqlite3

class Reaper:
    """
    Module D: The Executioner
    Responsibility: Analyze the database for duplicates and delete them.
    Safety Rule: NEVER delete from a path tagged 'MASTER'.
    """
    
    def __init__(self, master_path, db_path="sentry_index.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.master_path = master_path

    def analyze(self):
        """
        Finds files in TARGET that have a matching hash in MASTER.
        Returns a list of file paths to delete.
        """
        print("\n💀 ANALYZING DATABASE...")
        
        # The Golden Query:
        # Find files tagged 'TARGET' whose hash ALSO exists in 'MASTER'
        query = '''
            SELECT t.path, t.size, t.filename 
            FROM files t
            JOIN files m ON t.file_hash = m.file_hash
            WHERE t.tag = 'TARGET' 
            AND m.tag = 'MASTER'
        '''
        
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        
        # Deduplicate the list (in case multiple masters match one target)
        # We store just the path to delete
        kill_list = list(set([row[0] for row in results]))
        
        # Calculate stats
        total_size = sum([row[1] for row in results]) / (1024 * 1024 * 1024) # in GB
        
        print(f"   -> Found {len(kill_list)} confirmed duplicates.")
        print(f"   -> Potential Space Reclamation: {total_size:.2f} GB")
        
        return kill_list

    def execute(self, kill_list):
        """
        Deletes the files in the kill_list.
        """
        print(f"\n⚡ INITIALIZING DELETION PROTOCOL...")
        deleted_count = 0
        reclaimed_bytes = 0
        errors = 0
        
        for filepath in kill_list:
            # SAFETY CHECK: LAST LINE OF DEFENSE
            # Ensure we are NOT deleting from the Master drive
            if self.master_path in filepath:
                print(f"   🛑 CRITICAL SAFETY STOP: Attempted to delete from Master: {filepath}")
                continue

            try:
                # Get size before deleting for stats
                size = os.path.getsize(filepath)
                os.remove(filepath)
                
                deleted_count += 1
                reclaimed_bytes += size
                
                if deleted_count % 100 == 0:
                    print(f"   ...deleted {deleted_count} files...", end='\r')
                    
            except OSError as e:
                errors += 1
                print(f"   [ERR] Could not delete {filepath}: {e}")

        reclaimed_gb = reclaimed_bytes / (1024 * 1024 * 1024)
        print(f"\n\n============================================")
        print(f"✅ REAPER MISSION COMPLETE")
        print(f"🗑️  Files Deleted: {deleted_count}")
        print(f"💾 Space Reclaimed: {reclaimed_gb:.2f} GB")
        print(f"⚠️  Errors: {errors}")
        print(f"============================================")
