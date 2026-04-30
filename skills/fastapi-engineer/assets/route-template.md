# FastAPI Route Template

Use this template for creating new API routes in your FastAPI application.

## Basic Route Template

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database
from ..utils.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[schemas.YourModel])
def get_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve items.
    """
    items = db.query(models.YourModel).offset(skip).limit(limit).all()
    return items

@router.post("/", response_model=schemas.YourModel)
def create_item(
    item: schemas.YourModelCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create an item.
    """
    db_item = models.YourModel(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/{item_id}", response_model=schemas.YourModel)
def get_item(
    item_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get an item by ID.
    """
    item = db.query(models.YourModel).filter(models.YourModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.put("/{item_id}", response_model=schemas.YourModel)
def update_item(
    item_id: int,
    item_update: schemas.YourModelUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update an item.
    """
    item = db.query(models.YourModel).filter(models.YourModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    for key, value in item_update.dict(exclude_unset=True).items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item

@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete an item.
    """
    item = db.query(models.YourModel).filter(models.YourModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return {"message": "Item deleted successfully"}
```

## Usage Instructions

1. Replace `YourModel`, `YourModelCreate`, and `YourModelUpdate` with your actual model names
2. Adjust the router prefix in `APIRouter()` if needed
3. Modify the database queries according to your needs
4. Add appropriate authentication/authorization as needed
5. Update the response models to match your Pydantic schemas