"""
Unit and Flask Route Tests for Module 3: PMFBY Crop Insurance Shield.
"""

from contextlib import closing
import io
import os
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app
from tools.insurance_tool import (
    calculate_pmfby_quote,
    create_claim_dossier,
    delete_insurance_policy,
    evaluate_weather_claim_alert,
    init_insurance_db,
    list_claim_dossiers,
    list_insurance_policies,
    save_insurance_policy,
)


class TestInsuranceTool(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_insurance.db")
        init_insurance_db(self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_pmfby_season_caps_and_languages(self):
        q_kharif = calculate_pmfby_quote("paddy", "kharif", 2.0, language="en")
        self.assertEqual(q_kharif["status"], "success")
        self.assertEqual(q_kharif["farmer_premium_pct"], 2.0)
        self.assertEqual(q_kharif["sum_insured_inr"], 64000)
        self.assertEqual(q_kharif["farmer_premium_inr"], 1280)

        q_rabi = calculate_pmfby_quote("wheat", "rabi", 1.0, language="hi")
        self.assertEqual(q_rabi["farmer_premium_pct"], 1.5)
        self.assertIn("रबी", q_rabi["season_label"])

        q_hort = calculate_pmfby_quote("tomato", "horticulture", 1.0, language="kn")
        self.assertEqual(q_hort["farmer_premium_pct"], 5.0)
        self.assertIn("ಟೊಮೆಟೊ", q_hort["crop_name"])

    def test_72h_weather_trigger_hail_rain_and_safe(self):
        # Storm / Hail WMO code 96 must trigger RED_72H_CLAIM
        hail_weather = {
            "status": "success",
            "is_live_data": True,
            "display_location": "Mandya, Karnataka",
            "coordinates": {"latitude": 12.52, "longitude": 76.90},
            "weather_code": 96,
            "weather_condition": "Thunderstorm with slight hail",
            "current_temperature_c": 24.0,
            "rain_today_mm": 52.0,
            "rain_tomorrow_mm": 15.0,
            "wind_speed_kmh": 32.0,
            "wind_gusts_kmh": 62.0,
            "last_updated": "28 Nov 2026",
            "source": "Open-Meteo",
        }
        red = evaluate_weather_claim_alert("Mandya", language="en", weather_data=hail_weather)
        self.assertEqual(red["status"], "success")
        self.assertEqual(red["alert_level"], "RED_72H_CLAIM")
        self.assertIn("72 hours", red["advisory"])

        # Clear mild day must be GREEN_SAFE
        safe_weather = dict(hail_weather, weather_code=0, weather_condition="Clear sky", rain_today_mm=0.0, wind_speed_kmh=8.0, wind_gusts_kmh=14.0)
        green = evaluate_weather_claim_alert("Mandya", language="en", weather_data=safe_weather)
        self.assertEqual(green["alert_level"], "GREEN_SAFE")

        # Missing location must never hardcode/spoof a default location
        missing = evaluate_weather_claim_alert("", weather_data=None)
        self.assertEqual(missing["status"], "missing_location")

    def test_policy_vault_and_claim_dossier_persistence(self):
        saved = save_insurance_policy("usr_demo", "tomato", "horticulture", 1.5, db_path=self.db_path)
        self.assertEqual(saved["status"], "success")
        pol_id = saved["policy"]["id"]

        policies = list_insurance_policies("usr_demo", db_path=self.db_path)
        self.assertEqual(len(policies), 1)
        self.assertEqual(policies[0]["crop"], "tomato")

        mock_weather = {
            "status": "success",
            "is_live_data": True,
            "display_location": "Kolar, Karnataka",
            "coordinates": {"latitude": 13.13, "longitude": 78.13},
            "weather_code": 65,
            "weather_condition": "Heavy rain",
            "current_temperature_c": 22.0,
            "rain_today_mm": 48.5,
            "rain_tomorrow_mm": 5.0,
            "wind_speed_kmh": 22.0,
            "wind_gusts_kmh": 38.0,
        }
        dossier = create_claim_dossier(
            user_id="usr_demo",
            location_query="Kolar",
            policy_id=pol_id,
            photo_url="/static/uploads/test_damage.jpg",
            notes="Heavy rain lodged tomato plants",
            db_path=self.db_path,
            weather_data=mock_weather,
        )
        self.assertEqual(dossier["status"], "success")
        self.assertEqual(dossier["claim"]["weather_event"], "HEAVY_RAIN_FLOODING")
        self.assertAlmostEqual(dossier["claim"]["gps_lat"], 13.13)

        claims = list_claim_dossiers("usr_demo", db_path=self.db_path)
        self.assertEqual(len(claims), 1)

        deleted = delete_insurance_policy("usr_demo", pol_id, db_path=self.db_path)
        self.assertEqual(deleted["status"], "success")
        self.assertEqual(len(list_insurance_policies("usr_demo", db_path=self.db_path)), 0)

    def test_flask_insurance_routes_and_photo_upload(self):
        flask_app.config["TESTING"] = True
        flask_app.config["USERS_DB_PATH"] = self.db_path
        upload_dir = os.path.join(self.tmpdir.name, "uploads")
        flask_app.config["UPLOAD_FOLDER"] = upload_dir
        client = flask_app.test_client()

        q = client.get("/api/insurance/quote?crop=onion&season=horticulture&acres=2&language=en")
        self.assertEqual(q.status_code, 200)
        self.assertEqual(q.get_json()["farmer_premium_pct"], 5.0)

        p = client.post("/api/insurance/policy", json={"crop": "paddy", "season": "kharif", "acres": 3})
        self.assertEqual(p.status_code, 201)
        pol_id = p.get_json()["policy"]["id"]

        # Create real in-memory PNG for claim upload
        buf = io.BytesIO()
        Image.new("RGB", (32, 32), color=(40, 140, 50)).save(buf, format="PNG")
        buf.seek(0)

        r_claim = client.post(
            "/api/insurance/claim-dossier",
            data={
                "location": "",
                "policy_id": pol_id,
                "notes": "Flooded paddy field",
                "photo": (buf, "field_damage.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(r_claim.status_code, 201)
        claim = r_claim.get_json()["claim"]
        self.assertTrue(claim["photo_url"].startswith("/static/uploads/claim_"))

        claims_res = client.get("/api/insurance/claims").get_json()
        self.assertEqual(len(claims_res["claims"]), 1)


if __name__ == "__main__":
    unittest.main()
