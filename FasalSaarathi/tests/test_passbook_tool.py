"""
Unit and Flask Route Tests for Module 4: WhatsApp-Style Farm Passbook.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app
from tools.auth_tool import register_user
from tools.insurance_tool import save_insurance_policy
from tools.passbook_tool import (
    build_daily_passbook_briefing,
    clear_passbook_history,
    get_passbook_history,
    handle_passbook_reply,
    init_passbook_db,
)


class TestPassbookTool(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_passbook.db")
        init_passbook_db(self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_daily_briefing_unifies_profile_weather_compost_insurance_mandi(self):
        reg = register_user(
            name="Ramesh",
            phone="9876501234",
            pin_icons=["tomato", "sun", "tractor", "wheat"],
            persona="farmer",
            language="en",
            location_query="Kolar",
            db_path=self.db_path,
        )
        uid = reg["user"]["user_id"]
        save_insurance_policy(uid, "tomato", "horticulture", 2.0, db_path=self.db_path)

        mock_weather = {
            "status": "success",
            "is_live_data": True,
            "display_location": "Kolar, Karnataka",
            "coordinates": {"latitude": 13.13, "longitude": 78.13},
            "weather_code": 61,
            "weather_condition": "Slight rain",
            "current_temperature_c": 24.5,
            "rain_today_mm": 12.0,
            "rain_tomorrow_mm": 4.0,
            "wind_speed_kmh": 14.0,
            "wind_gusts_kmh": 22.0,
            "irrigation_action": "Skip watering today because 12 mm rain is expected.",
        }
        mock_mandi = {
            "status": "success",
            "commodity": "Tomato",
            "primary_mandi": "Kolar APMC",
            "primary_state": "Karnataka",
            "price_per_kg": 24.0,
            "modal_price": 2400,
            "trend": "Going Up (+12%)",
            "selling_advisory": "Prices rising — hold for 1-2 days if possible.",
        }

        res = build_daily_passbook_briefing(
            user_id=uid,
            db_path=self.db_path,
            weather_data=mock_weather,
            mandi_data=mock_mandi,
        )
        self.assertEqual(res["status"], "success")
        txt = res["message"]["text"]
        self.assertIn("Ramesh", txt)
        self.assertIn("Kolar, Karnataka", txt)
        self.assertIn("Skip watering today", txt)
        self.assertIn("1 active policy", txt)
        self.assertIn("₹24.0/kg", txt)
        self.assertEqual(res["stats"]["active_policies"], 1)

    def test_quick_reply_log_waste_and_per_user_history_isolation(self):
        r1 = handle_passbook_reply(
            user_id="user_a",
            action="log_waste",
            text="Added 2 kg vegetable peels",
            language="en",
            db_path=self.db_path,
        )
        self.assertEqual(r1["status"], "success")
        self.assertEqual(r1["stats"]["waste_kg"], 2.0)
        self.assertEqual(r1["stats"]["saved_inr"], 60)
        self.assertIn("dry leaves or cocopeat", r1["bot_message"]["text"])

        # User B must have completely isolated passbook history and zero waste
        hist_a = get_passbook_history("user_a", db_path=self.db_path)
        hist_b = get_passbook_history("user_b", db_path=self.db_path)
        self.assertEqual(len(hist_a), 2)
        self.assertEqual(len(hist_b), 0)

        clear_passbook_history("user_a", db_path=self.db_path)
        self.assertEqual(len(get_passbook_history("user_a", db_path=self.db_path)), 0)

    def test_flask_passbook_routes_end_to_end(self):
        flask_app.config["TESTING"] = True
        flask_app.config["USERS_DB_PATH"] = self.db_path
        client = flask_app.test_client()

        r_daily = client.get("/api/passbook/daily?language=hi")
        self.assertEqual(r_daily.status_code, 200)
        d = r_daily.get_json()
        self.assertEqual(d["status"], "success")
        self.assertIn("पासबुक", d["message"]["text"])

        r_reply = client.post(
            "/api/passbook/reply",
            json={"action": "log_waste", "language": "kn"},
        )
        self.assertEqual(r_reply.status_code, 200)
        rep = r_reply.get_json()
        self.assertEqual(rep["stats"]["waste_kg"], 1.0)
        self.assertIn("ಕೊಕೊಪೀಟ್", rep["bot_message"]["text"])

        hist = client.get("/api/passbook/history").get_json()
        self.assertGreaterEqual(len(hist["messages"]), 3)


if __name__ == "__main__":
    unittest.main()
