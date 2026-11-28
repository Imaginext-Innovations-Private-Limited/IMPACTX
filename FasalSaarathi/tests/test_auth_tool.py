"""
Unit and Flask Route Tests for Module 1: Picture-PIN Login & Farmer Profile.
"""

from contextlib import closing
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app
from tools.auth_tool import (
    get_guest_profile,
    get_user_profile,
    init_auth_db,
    login_user,
    register_user,
    update_user_profile,
)


class TestAuthTool(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_users.db")
        init_auth_db(self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_register_hashes_pin_and_login_succeeds(self):
        res = register_user(
            name="Ramesh",
            phone="+91 9876543210",
            pin_icons=["tomato", "sun", "tractor", "wheat"],
            persona="farmer",
            language="kn",
            location_query="Kolar",
            primary_crop="tomato",
            db_path=self.db_path,
        )
        self.assertEqual(res["status"], "success")
        user = res["user"]
        self.assertEqual(user["phone"], "9876543210")
        self.assertEqual(user["language"], "kn")
        self.assertEqual(user["location_query"], "Kolar")
        self.assertNotIn("pin_icons", user)

        # Verify PIN is stored hashed in SQLite, never plaintext
        with closing(sqlite3.connect(self.db_path)) as conn:
            stored_hash = conn.execute(
                "SELECT pin_icons FROM users WHERE user_id = ?", (user["user_id"],)
            ).fetchone()[0]
        self.assertNotIn("tomato", stored_hash)
        self.assertTrue(stored_hash.startswith("pbkdf2:") or stored_hash.startswith("scrypt:"))

        # Login with matching icons succeeds
        login_ok = login_user("9876543210", ["tomato", "sun", "tractor", "wheat"], db_path=self.db_path)
        self.assertEqual(login_ok["status"], "success")
        self.assertEqual(login_ok["user"]["user_id"], user["user_id"])

        # Login with wrong icon order fails
        login_bad = login_user("9876543210", ["sun", "tomato", "tractor", "wheat"], db_path=self.db_path)
        self.assertEqual(login_bad["status"], "unauthorized")

    def test_duplicate_phone_and_invalid_pin_rejected(self):
        register_user("Asha", "9123456789", ["water", "sprout", "sun", "tomato"], db_path=self.db_path)
        dup = register_user("Asha 2", "9123456789", ["water", "sprout", "sun", "tomato"], db_path=self.db_path)
        self.assertEqual(dup["status"], "duplicate_phone")

        short_pin = register_user("Ravi", "9988776655", ["water", "sun"], db_path=self.db_path)
        self.assertEqual(short_pin["status"], "error")

        bad_icon = register_user("Ravi", "9988776655", ["water", "sun", "pizza", "wheat"], db_path=self.db_path)
        self.assertEqual(bad_icon["status"], "error")

    def test_guest_and_profile_update(self):
        guest = get_guest_profile(db_path=self.db_path)
        self.assertEqual(guest["status"], "success")
        self.assertTrue(guest["user"]["is_guest"])

        reg = register_user(
            name="Meena",
            phone="9000011111",
            pin_icons=["sprout", "water", "sun", "tomato"],
            persona="terrace",
            language="hi",
            location_query="Pune",
            db_path=self.db_path,
        )
        uid = reg["user"]["user_id"]
        upd = update_user_profile(
            uid,
            {"location_query": "Nashik", "language": "mr", "primary_crop": "onion", "lat": 19.9975, "lon": 73.7898},
            db_path=self.db_path,
        )
        self.assertEqual(upd["status"], "success")
        fetched = get_user_profile(uid, db_path=self.db_path)
        self.assertEqual(fetched["location_query"], "Nashik")
        self.assertEqual(fetched["language"], "mr")
        self.assertEqual(fetched["primary_crop"], "onion")
        self.assertAlmostEqual(fetched["lat"], 19.9975)

    def test_flask_auth_routes_end_to_end(self):
        flask_app.config["TESTING"] = True
        flask_app.config["USERS_DB_PATH"] = self.db_path
        client = flask_app.test_client()

        # Login page renders
        page = client.get("/login")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Picture-PIN", page.data)

        # Initially unauthenticated
        me0 = client.get("/api/auth/me").get_json()
        self.assertFalse(me0["authenticated"])

        # Register via API sets session
        r_reg = client.post(
            "/api/auth/register",
            json={
                "name": "Kavitha",
                "phone": "9448012345",
                "pin_icons": ["tomato", "water", "sprout", "sun"],
                "persona": "terrace",
                "language": "ta",
                "location_query": "Coimbatore",
                "primary_crop": "methi",
            },
        )
        self.assertEqual(r_reg.status_code, 201)

        me1 = client.get("/api/auth/me").get_json()
        self.assertTrue(me1["authenticated"])
        self.assertEqual(me1["user"]["name"], "Kavitha")
        self.assertEqual(me1["user"]["persona"], "terrace")

        # Update profile
        r_upd = client.post("/api/auth/profile", json={"location_query": "Madurai", "language": "kn"})
        self.assertEqual(r_upd.status_code, 200)
        self.assertEqual(r_upd.get_json()["user"]["location_query"], "Madurai")

        # Logout clears session
        client.post("/api/auth/logout")
        me2 = client.get("/api/auth/me").get_json()
        self.assertFalse(me2["authenticated"])

        # Guest login works
        r_guest = client.post("/api/auth/guest")
        self.assertEqual(r_guest.status_code, 200)
        self.assertTrue(r_guest.get_json()["user"]["is_guest"])


if __name__ == "__main__":
    unittest.main()
