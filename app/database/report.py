import sys
import os
from datetime import datetime
from sqlmodel import Session, select, func
from app.database.models import FileRecord, engine

def generate_report():
    """Generates a text report and returns the filename."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f"mission_report_{timestamp}.txt"
    
    with Session(engine) as session:
        statement = (
            select(FileRecord.file_hash, func.count(FileRecord.id))
            .group_by(FileRecord.file_hash)
            .having(func.count(FileRecord.id) > 1)
        )
        duplicates = session.exec(statement).all()
        
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(f"PROJECT SENTRY - DUPLICATE FILE REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write(f"Total Duplicate Sets Found: {len(duplicates)}\n")
            f.write("="*60 + "\n\n")

            if not duplicates:
                f.write("No duplicates found.\n")
            else:
                for file_hash, count in duplicates:
                    if not file_hash: continue
                    f.write(f"MATCH GROUP (Hash: {file_hash[:8]}... | Count: {count})\n")
                    
                    files = session.exec(select(FileRecord).where(FileRecord.file_hash == file_hash)).all()
                    for file_record in files:
                        size_mb = file_record.size_bytes / (1024 * 1024)
                        f.write(f"   - {file_record.path} ({size_mb:.2f} MB)\n")
                    f.write("-" * 40 + "\n")
    
    return report_filename

if __name__ == "__main__":
    # --- PATH HACK FOR DIRECT RUNNING ---
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    sys.path.append(parent_dir)
    # ------------------------------------
    name = generate_report()
    print(f"Report generated: {name}")
