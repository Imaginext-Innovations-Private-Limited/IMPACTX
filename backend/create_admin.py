
from getpass import getpass
from werkzeug.security import generate_password_hash
from database import get_db_connection

print("===== Serenify Admin Account Setup =====")

full_name = input("Enter admin name: ").strip()
email = input("Enter admin email: ").strip().lower()
password = getpass("Enter admin password: ")
confirm_password = getpass("Confirm admin password: ")

if not full_name or not email or not password:
    print("All fields are required.")
    raise SystemExit

if password != confirm_password:
    print("Passwords do not match.")
    raise SystemExit

if len(password) < 8:
    print("Password must contain at least 8 characters.")
    raise SystemExit

password_hash = generate_password_hash(password)

connection = get_db_connection()
cursor = connection.cursor()

try:
    cursor.execute(
        "SELECT admin_id FROM admins WHERE email = %s",
        (email,)
    )

    if cursor.fetchone():
        print("An admin account with this email already exists.")
    else:
        cursor.execute("""
            INSERT INTO admins (full_name, email, password_hash)
            VALUES (%s, %s, %s)
        """, (full_name, email, password_hash))

        connection.commit()
        print("Admin account created successfully!")

except Exception as e:
    connection.rollback()
    print("Error:", e)

finally:
    cursor.close()
    connection.close()
