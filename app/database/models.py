import os
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine

class ScanMission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: float = Field(default=None) 
    root_paths: str
    status: str = Field(default="PENDING")

class FileRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mission_id: int = Field(foreign_key="scanmission.id")
    drive_id: str = Field(index=True)  # <--- The Critical Field
    path: str
    filename: str
    extension: str
    size_bytes: int
    created_at: float
    file_hash: str = Field(index=True)
    is_scanned: bool = Field(default=False)

# Database Setup (persistable path via env var)
sqlite_file_name = os.getenv("SENTRY_DB_PATH", "/data/sentry.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

def init_db():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()
    print("Database tables created successfully.")

