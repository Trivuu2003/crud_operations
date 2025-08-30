from __future__ import annotations

from sqlalchemy import func

from .config import settings
from .db import session_scope
from .models import Base, User
from .security import hash_password
from .db import engine


def run() -> None:
    Base.metadata.create_all(bind=engine)
    admin_emails = [e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()]
    if not admin_emails:
        print("No ADMIN_EMAILS provided; skipping seeding")
        return
    with session_scope() as session:
        for email in admin_emails:
            existing = session.query(User).filter(func.lower(User.email) == email).first()
            if existing:
                continue
            user = User(
                email=email,
                first_name="Admin",
                last_name="User",
                password_hash=hash_password("Admin1234"),
                plan="Pro",
            )
            session.add(user)
        print(f"Seeded admin users: {', '.join(admin_emails)}")


if __name__ == "__main__":
    run()


