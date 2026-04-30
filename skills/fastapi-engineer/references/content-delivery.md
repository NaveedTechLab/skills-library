# Content Delivery System Implementation

## Content Models and Schemas

### Database Model (models/content.py)
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, LargeBinary
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    instructor_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    materials = relationship("Material", back_populates="course")
    enrollments = relationship("Enrollment", back_populates="course")

class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String, index=True)
    description = Column(Text)
    file_path = Column(String)  # Path to stored file
    file_size = Column(Integer)  # Size in bytes
    content_type = Column(String)  # MIME type
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    course = relationship("Course", back_populates="materials")
    views = relationship("ContentView", back_populates="material")

class ContentView(Base):
    __tablename__ = "content_views"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())
    duration_seconds = Column(Integer)  # How long user spent viewing

    material = relationship("Material", back_populates="views")
    user = relationship("User")
```

### Pydantic Schemas (schemas/content.py)
```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MaterialBase(BaseModel):
    title: str
    description: Optional[str] = None
    order: int = 0

class MaterialCreate(MaterialBase):
    course_id: int

class Material(MaterialBase):
    id: int
    course_id: int
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None

class Course(CourseBase):
    id: int
    instructor_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    materials: List[Material] = []

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    id: int
    file_path: str
    content_type: str
    file_size: int
    message: str
```

## Content Router Implementation (routers/content.py)
```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from pathlib import Path
from .. import models, schemas, database, utils
from ..config import settings
from fastapi.responses import FileResponse
import mimetypes

router = APIRouter()

# Ensure upload directory exists
upload_dir = Path(settings.UPLOAD_FOLDER)
upload_dir.mkdir(parents=True, exist_ok=True)

@router.post("/upload", response_model=schemas.UploadResponse)
async def upload_content(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(utils.get_current_user)
):
    # Validate file size
    if len(await file.read()) > settings.MAX_CONTENT_LENGTH:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_CONTENT_LENGTH} bytes"
        )

    # Reset file pointer
    await file.seek(0)

    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{utils.generate_unique_id()}{file_extension}"
    file_path = upload_dir / unique_filename

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create material record
    material = models.Material(
        title=file.filename,
        description="Uploaded content",
        file_path=str(file_path),
        file_size=os.path.getsize(file_path),
        content_type=file.content_type or mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    )

    db.add(material)
    db.commit()
    db.refresh(material)

    return schemas.UploadResponse(
        id=material.id,
        file_path=material.file_path,
        content_type=material.content_type,
        file_size=material.file_size,
        message="File uploaded successfully"
    )

@router.get("/materials/{material_id}")
async def get_material(
    material_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(utils.get_current_user)
):
    material = db.query(models.Material).filter(models.Material.id == material_id).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Track view
    view = models.ContentView(
        material_id=material.id,
        user_id=current_user.id
    )
    db.add(view)
    db.commit()

    file_path = Path(material.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        media_type=material.content_type,
        filename=file_path.name,
        headers={
            "Content-Disposition": f"inline; filename={file_path.name}",
            "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
        }
    )

@router.get("/courses/{course_id}/materials", response_model=List[schemas.Material])
def get_course_materials(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(utils.get_current_user)
):
    materials = (
        db.query(models.Material)
        .filter(models.Material.course_id == course_id)
        .order_by(models.Material.order)
        .all()
    )

    return materials

@router.post("/courses/{course_id}/materials", response_model=schemas.Material)
def create_material(
    course_id: int,
    material: schemas.MaterialCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(utils.get_current_user)
):
    # Verify course exists and user has permission
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check if user is instructor of the course
    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to add materials to this course")

    db_material = models.Material(**material.dict())
    db.add(db_material)
    db.commit()
    db.refresh(db_material)

    return db_material
```

## Content Utilities (utils/file_handlers.py)
```python
import uuid
import hashlib
import os
from pathlib import Path
from typing import Optional
import mimetypes

def generate_unique_id() -> str:
    """Generate a unique identifier for file uploads"""
    return str(uuid.uuid4())

def validate_file_type(filename: str, allowed_types: list) -> bool:
    """Validate file type against allowed extensions"""
    file_ext = Path(filename).suffix.lower()
    return file_ext in allowed_types

def get_file_size(filepath: str) -> int:
    """Get file size in bytes"""
    return os.path.getsize(filepath)

def get_content_type(filepath: str) -> str:
    """Get content type from file extension"""
    content_type, _ = mimetypes.guess_type(filepath)
    return content_type or "application/octet-stream"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    # Remove any path components
    filename = os.path.basename(filename)
    # Replace any non-alphanumeric characters except common ones
    sanitized = "".join(c for c in filename if c.isalnum() or c in "._- ")
    return sanitized.strip()

def cleanup_temp_files(directory: str, max_age_hours: int = 24):
    """Clean up temporary files older than specified hours"""
    import time
    current_time = time.time()

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            file_age_hours = (current_time - os.path.getctime(filepath)) / 3600
            if file_age_hours > max_age_hours:
                os.remove(filepath)
```