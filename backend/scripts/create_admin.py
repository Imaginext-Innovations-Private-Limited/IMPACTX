
from getpass import getpass
from datetime import datetime, timezone

from app.database import db
from app.utils.security import hash_password


def create_admin():

    print("\n===== AquaWatch Admin Setup =====\n")

    name = input("Enter admin name: ").strip()
    email = input("Enter admin email: ").strip().lower()

    if not name or not email:
        print("Name and email are required.")
        return

    existing_user = db.users.find_one({"email": email})

    if existing_user:
        print("This email already exists.")
        print("No account was changed.")
        return

    password = getpass("Enter admin password (minimum 12 characters): ")
    confirm_password = getpass("Confirm admin password: ")

    if len(password) < 12:
        print("Password must contain at least 12 characters.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    admin = {
        "name": name,
        "email": email,
        "password": hash_password(password),
        "role": "admin",
        "created_at": datetime.now(timezone.utc)
    }

    db.users.insert_one(admin)

    print("\nAdmin account created successfully!")
    print("Name:", name)
    print("Email:", email)
    print("Role: admin")


if __name__ == "__main__":
    create_admin()
