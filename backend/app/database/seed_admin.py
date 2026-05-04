from sqlalchemy.orm import Session
from ..database.session import SessionLocal
from ..models.entities import User
from ..core.security import get_password_hash
from sqlalchemy import select

def seed_admin():
    db = SessionLocal()
    try:
        # Check if admin exists
        admin_email = "admin@vixa.online"
        existing = db.scalar(select(User).where(User.email == admin_email))
        if existing:
            print(f"Admin {admin_email} already exists.")
            return
        
        admin = User(
            email=admin_email,
            name="Vixa Admin",
            password_hash=get_password_hash("vixa_admin_2026"),
            role='admin',
            is_active=True
        )
        db.add(admin)
        db.commit()
        print(f"Admin {admin_email} created successfully.")
    except Exception as e:
        print(f"Error seeding admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
