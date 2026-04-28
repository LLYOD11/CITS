from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models import get_db
from app.models.models import User, Activity
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(**user.dict()); db.add(db_user); db.commit(); db.refresh(db_user); return db_user

@router.get("/", response_model=List[UserResponse])
def list_users(tier: str = None, status: str = None, db: Session = Depends(get_db)):
    query = db.query(User)
    if tier: query = query.filter(User.tier == tier)
    if status: query = query.filter(User.status == status)
    return query.all()

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/{user_id}/activities")
def get_user_activities(user_id: int, db: Session = Depends(get_db)):
    return db.query(Activity).filter(Activity.user_id == user_id).order_by(Activity.created_at.desc()).limit(20).all()

@router.post("/{user_id}/status")
def update_status(user_id: int, status: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    user.status = status; db.commit()
    return {"message": "Status updated", "user_id": user_id, "status": status}
