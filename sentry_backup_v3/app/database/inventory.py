import sys
import os

# --- PATH HACK (MUST BE AT THE TOP) ---
# This tells Python: "Look for files in the project-sentry folder"
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)
# --------------------------------------

from sqlmodel import Session, select, func
from app.database.models import FileRecord, engine

def show_inventory():
    print("\n=== PROJECT SENTRY: DRIVE INVENTORY ===")
    
    with Session(engine) as session:
        # Get all unique drive IDs
        statement = select(FileRecord.drive_id).distinct()
        drive_ids = session.exec(statement).all()
        
        for d_id in drive_ids:
            # Get file count
            count = session.exec(select(func.count()).where(FileRecord.drive_id == d_id)).one()
            
            # Get a sample path to identify the drive name
            sample = session.exec(select(FileRecord).where(FileRecord.drive_id == d_id)).first()
            
            drive_name = "Unknown"
            if sample:
                # Try to extract readable name from path
                # Example: /media/greg/MyDrive/folder -> MyDrive
                parts = sample.path.split(os.sep)
                if len(parts) > 3 and parts[1] == "media":
                    drive_name = f"/media/{parts[2]}/{parts[3]}"
                else:
                    drive_name = os.path.dirname(sample.path)

            print(f"Drive ID: {d_id}")
            print(f"   Name:  {drive_name}")
            print(f"   Files: {count}")
            print("-" * 40)

if __name__ == "__main__":
    show_inventory()
