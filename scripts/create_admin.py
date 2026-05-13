"""Create first admin user if none exists (run after migrations)."""
import os
import sys

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, UserRole
from app.security import hash_password


def main() -> None:
    email = os.environ.get("ADMIN_EMAIL", "admin@example.com").strip().lower()
    password = (os.environ.get("ADMIN_PASSWORD") or "").strip()
    if not password:
        print("ADMIN_PASSWORD must be set in the environment.", file=sys.stderr)
        sys.exit(1)
    db: Session = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print("Admin already exists:", email)
            return
        db.add(
            User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Administrator",
                role=UserRole.admin,
            )
        )
        db.commit()
        print("Created admin:", email)
    finally:
        db.close()


if __name__ == "__main__":
    main()
