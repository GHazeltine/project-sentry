import sys
import os
from datetime import datetime

# --- PATH HACK ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)
# -----------------

from sqlmodel import Session, select, func
from app.database.models import FileRecord, engine

def generate_report():
    report_filename = f"mission_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    print("Analyzing Database... please wait.")
    
    with Session(engine) as session:
        # 1. Find hashes that appear more than once
        statement = (
            select(FileRecord.file_hash, func.count(FileRecord.id))
            .group_by(FileRecord.file_hash)
            .having(func.count(FileRecord.id) > 1)
        )
        duplicates = session.exec(statement).all()
        
        if not duplicates:
            print("No duplicates found.")
            return

        # 2. Write to File
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(f"PROJECT SENTRY - DUPLICATE FILE REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write(f"Total Duplicate Sets Found: {len(duplicates)}\n")
            f.write("="*60 + "\n\n")

            for file_hash, count in duplicates:
                if not file_hash: continue
                
                f.write(f"MATCH GROUP (Hash: {file_hash[:8]}... | Count: {count})\n")
                
                files = session.exec(select(FileRecord).where(FileRecord.file_hash == file_hash)).all()
                for file_record in files:
                    size_mb = file_record.size_bytes / (1024 * 1024)
                    f.write(f"   - {file_record.path} ({size_mb:.2f} MB)\n")
                
                f.write("-" * 40 + "\n")
    
    print(f"✅ Success! Report saved to: {report_filename}")
    print(f"   Found {len(duplicates)} sets of duplicates.")

if __name__ == "__main__":
    generate_report()
