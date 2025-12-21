import os
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine

# 1. Drive Model
class Drive(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    device: str
    mountpoint: str
    label: Optional[str] = None
    size: str
    
# 2. Mission Model
class ScanMission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: float
    status: str
    root_paths: Optional[str] = None

# 3. File Record Model
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
    tag: str
    is_flagged: bool = Field(default=False, index=True)

# --- CONFIGURATION MATCHING DOCKER-COMPOSE.YML ---
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://sentry_admin:sentry_secure_pass@sentry-db:5432/sentry_v3"
)

engine = create_engine(DATABASE_URL)

def init_db():
    SQLModel.metadata.create_all(engine)
