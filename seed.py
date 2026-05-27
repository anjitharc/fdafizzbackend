"""
Seed script to create initial data for the Food Delivery App.
Run this script after setting up the database and running migrations.

Usage: python seed.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.zone import Zone
from app.utils.security import hash_password


def seed_database():
    """Create initial seed data."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Check if master admin already exists
        existing_admin = db.query(User).filter(User.role == UserRole.MASTER_ADMIN).first()
        if existing_admin:
            print("Master admin already exists. Skipping seed.")
            return

        # Create Master Admin
        admin = User(
            name="Master Admin",
            email="admin@fda.com",
            phone="9999999999",
            password_hash=hash_password("admin123"),
            role=UserRole.MASTER_ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.flush()

        # Create a sample zone
        sample_zone = Zone(
            name="Downtown Zone",
            coordinates=[
                {"lat": 12.9500, "lng": 77.5800},
                {"lat": 12.9500, "lng": 77.6200},
                {"lat": 12.9800, "lng": 77.6200},
                {"lat": 12.9800, "lng": 77.5800},
            ],
            created_by=admin.id,
        )
        db.add(sample_zone)
        db.flush()

        # Create a sample Zone Manager
        zone_manager = User(
            name="Zone Manager 1",
            email="manager@fda.com",
            phone="8888888888",
            password_hash=hash_password("manager123"),
            role=UserRole.ZONE_MANAGER,
            zone_id=sample_zone.id,
            is_active=True,
        )
        db.add(zone_manager)

        # Create a sample Delivery Staff
        delivery_staff = User(
            name="Delivery Person 1",
            email="delivery@fda.com",
            phone="7777777777",
            password_hash=hash_password("delivery123"),
            role=UserRole.DELIVERY_STAFF,
            is_active=True,
        )
        db.add(delivery_staff)

        db.commit()

        print("=" * 50)
        print("Database seeded successfully!")
        print("=" * 50)
        print("\nDefault Accounts:")
        print("-" * 50)
        print(f"Master Admin:    admin@fda.com / admin123")
        print(f"Zone Manager:    manager@fda.com / manager123")
        print(f"Delivery Staff:  delivery@fda.com / delivery123")
        print(f"\nSample Zone:     Downtown Zone (ID: {sample_zone.id})")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
