import sqlite3
import os

def repair_database():
    db_file = "sentry.db"
    
    if not os.path.exists(db_file):
        print(f"❌ Error: {db_file} not found.")
        return

    print(f"🔧 Opening {db_file} for repair...")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 1. Force-Add the missing column
    try:
        print("   Adding missing column 'drive_id'...")
        cursor.execute("ALTER TABLE filerecord ADD COLUMN drive_id VARCHAR")
        conn.commit()
        print("   ✅ Column added.")
    except sqlite3.OperationalError:
        print("   ⚠️ Column 'drive_id' already exists. Skipping step.")

    # 2. Backfill the data (Repairing the empty IDs)
    print("   Analyzing paths to restore Drive IDs...")
    
    cursor.execute("SELECT id, path FROM filerecord")
    rows = cursor.fetchall()
    
    updates = []
    
    for row_id, path in rows:
        # Logic: Guess the drive name from the folder path
        # Example: /media/greg/My Book/photos -> My Book
        parts = path.split(os.sep)
        
        drive_name = "UNKNOWN_DRIVE"
        if len(parts) > 3 and parts[1] == "media":
            # Linux Standard: /media/user/DriveName
            drive_name = parts[3] 
        else:
            # Fallback: Just grab the root folder
            drive_name = "System_Root"
            
        updates.append((drive_name, row_id))

    # 3. Save the repaired data
    print(f"   Updating {len(updates)} records... (This might take a moment)")
    cursor.executemany("UPDATE filerecord SET drive_id = ? WHERE id = ?", updates)
    conn.commit()
    conn.close()
    
    print("✅ REPAIR COMPLETE. Your database is now compatible with Phase 3.")

if __name__ == "__main__":
    repair_database()
