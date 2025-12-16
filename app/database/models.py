from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, create_engine

class ScanMission(SQLModel, table=True):
    """
    Represents a specific job the user requested.
    Example: "Scan /mnt/usb1 on Dec 16th"
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="ACTIVE")  # ACTIVE, PAUSED, COMPLETED
    root_paths: str  # Comma-separated list of folders scanned (e.g. "/mnt/usb1,/mnt/data")

class FileRecord(SQLModel, table=True):
    """
    The permanent record for every file found.
    This allows us to find duplicates across 4 different drives.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    mission_id: int = Field(foreign_key="scanmission.id")
    
    # File Metadata
    path: str = Field(index=True)  # Indexed for fast searching
    filename: str
    extension: str
    size_bytes: int
    created_at: float
    
    # The Fingerprint (For finding duplicates)
    file_hash: Optional[str] = Field(default=None, index=True)
    
    # Processing Status
    is_scanned: bool = Field(default=False)
    is_duplicate: bool = Field(default=False)
    
    # AI Results (Future proofing for the Hailo Chip)
    ai_tags: Optional[str] = Field(default=None)  # e.g. "person, car, dog"
    ai_confidence: float = Field(default=0.0)

# The Engine (The connection to the actual file)
sqlite_file_name = "sentry.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)

def create_db_and_tables():
    """Helper to initialize the database if it doesn't exist."""
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    # Test run to create the file
    create_db_and_tables()
    print("Database sentry.db created successfully.")
