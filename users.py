from __future__ import annotations

from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import User
from .schemas import UserCreate, UserOut, UserUpdate
from .security import hash_password


def create_user(db: Session, payload: UserCreate) -> User:
    existing = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        first_name=payload.first_name,
        last_name=payload.last_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    from .security import verify_password

    user = db.query(User).filter(func.lower(User.email) == email.lower()).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id.cast(str) == str(user_id)).first()


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.plan is not None:
        user.plan = payload.plan
    if payload.addons is not None:
        user.addons = payload.addons
    if payload.notification_prefs is not None:
        user.notification_prefs = payload.notification_prefs
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def list_users(db: Session, skip: int = 0, limit: int = 20) -> Tuple[int, List[User]]:
    total = db.query(func.count(User.id)).scalar() or 0
    items = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return total, items


