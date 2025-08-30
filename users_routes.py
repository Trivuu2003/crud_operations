from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .config import settings
from .deps import db_session
from .models import User
from .schemas import PaginatedUsers, UserOut, UserUpdate
from .security import get_current_user
from .users import delete_user, list_users, update_user


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    user = update_user(db, current_user, payload)
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(db: Session = Depends(db_session), current_user: User = Depends(get_current_user)):
    delete_user(db, current_user)
    return None


@router.get("", response_model=PaginatedUsers)
def admin_list_users(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    admin_list = [e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()]
    if current_user.email.lower() not in admin_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    total, items = list_users(db, skip, limit)
    return {"total": total, "items": items}


