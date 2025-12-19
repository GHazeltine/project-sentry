import os
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine

sqlite_file_name = os.getenv("SENTRY_DB_PATH", "/data/sentry.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

class ScanMission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: float
    root_paths: str
    status: str = "PENDING"

class FileRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mission_id: int = Field(foreign_key="scanmission.id")
    drive_id: str = Field(index=True)
    path: str
    filename: str
    extension: str
    size_bytes: int
    created_at: float
    file_hash: Optional[str] = Field(index=True)
    visual_hash: Optional[str] = None
    tag: str  # <--- CRITICAL NEW FIELD

def init_db():
    SQLModel.metadata.create_all(engine)
