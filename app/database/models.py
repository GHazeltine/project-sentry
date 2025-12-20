import os
from typing import Optional
from sqlmodel import SQLModel, Field, create_engine

# --- V3 DATABASE CONNECTION LOGIC ---
# This intelligently switches between SQLite (Old) and PostgreSQL (New)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/sentry.db")

# Postgres requires different arguments than SQLite
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

# Create the Engine
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

# --- DATA MODELS (Preserved V2 Structure) ---

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
    size_bytes: int             # Preserved
    created_at: float
    file_hash: Optional[str] = Field(index=True) # Preserved
    visual_hash: Optional[str] = None            # Ready for AI features
    tag: str                    # 'MASTER' or 'TARGET'
