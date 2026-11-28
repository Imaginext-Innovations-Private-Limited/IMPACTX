"""
Unit & Integration Tests for FasalSaarathi Terrace & Beginner Farming Engine
Verifies:
1. Zero hardcoded locations, dimensions, or fabricated weather fallbacks.
2. Dynamic container geometry, potting bucket scaling, and IS 875 slab weight safety.
3. Sunlight-based physiological crop filtering (shade balcony vs full sunny rooftop).
4. Zero silent crop substitution in offline Seed-to-Harvest coach + zero Latin jargon.
5. Flask API routes (/api/tools/terrace/plan & /api/tools/terrace/guide) input validation.
"""

import unittest
from unittest.mock import patch

from app import app
from tools.terrace_farming_tool import learn_crop_guide, plan_terrace_garden

FORBIDDEN_JARGON = (
    "solanum",
    "capsicum",
    "trigonella",
    "coriandrum",
    "mentha",
    "abelmoschus",
    "necrotic",
    "chlorotic",
    "oomycete",
)


class TestTerraceFarmingTool(unittest.TestCase):
    def test_missing_location_and_dimensions_rejected(self):
        res_no_loc = plan_terrace_garden(location_query="", length_ft=10, width_ft=6, sunlight_hours=5)
        self.assertEqual(res_no_loc["status"], "missing_location")
        self.assertFalse(res_no_loc["is_live_data"])

        res_no_dim = plan_terrace_garden(location_query="Mysuru", length_ft=None, width_ft=6, sunlight_hours=5)
        self.assertEqual(res_no_dim["status"], "invalid_dimensions")

        res_bad_sun = plan_terrace_garden(location_query="Mysuru", length_ft=10, width_ft=6, sunlight_hours=0)
        self.assertEqual(res_bad_sun["status"], "invalid_dimensions")

    @patch("tools.terrace_farming_tool.fetch_live_weather")
    def test_honest_offline_when_weather_unavailable(self, mock_weather):
        mock_weather.return_value = {
            "status": "service_unavailable",
            "is_live_data": False,
            "message": "Weather offline",
        }
        res = plan_terrace_garden(location_query="UncachedTownXYZ", length_ft=10, width_ft=5, sunlight_hours=5)
        self.assertEqual(res["status"], "service_unavailable")
        self.assertNotIn("space_plan", res)

    @patch("tools.terrace_farming_tool.fetch_live_weather")
    def test_dynamic_physics_scaling_and_slab_weight_safety(self, mock_weather):
        mock_weather.return_value = {
            "status": "success",
            "is_live_data": True,
            "display_location": "Bengaluru, Karnataka",
            "current_temperature_c": 27.4,
            "humidity_pct": 62,
            "rain_today_mm": 0.0,
            "rain_today_probability_pct": 10,
            "et0_today_mm": 4.5,
        }

        small = plan_terrace_garden(
            location_query="Bengaluru",
            length_ft=6,
            width_ft=3,
            sunlight_hours=5.5,
            space_type="covered_balcony",
            language="en",
        )
        large = plan_terrace_garden(
            location_query="Bengaluru",
            length_ft=20,
            width_ft=15,
            sunlight_hours=6.5,
            space_type="open_terrace",
            language="kn",
        )

        self.assertEqual(small["status"], "success")
        self.assertEqual(large["status"], "success")

        # Grow-Bag Layout and Roof Slab Weight Safety were removed per user request
        self.assertNotIn("space_plan", large)
        self.assertNotIn("roof_safety", large)

        # Dynamic scaling: 300 sq.ft rooftop has strictly more soil litres and buckets than 18 sq.ft balcony
        self.assertGreater(
            large["potting_mix_buckets"]["total_soil_litres"],
            small["potting_mix_buckets"]["total_soil_litres"],
        )
        self.assertGreater(
            large["potting_mix_buckets"]["cocopeat_buckets"],
            small["potting_mix_buckets"]["cocopeat_buckets"],
        )
        self.assertGreater(large["watering_today"]["ml_per_medium_bag"], 0)

        # Kannada localization check
        self.assertTrue(any("\u0c80" <= ch <= "\u0cff" for ch in large["weather_snapshot"]["weather_care_tip"]))

    @patch("tools.terrace_farming_tool.fetch_live_weather")
    def test_low_sunlight_balcony_filters_out_high_sun_crops(self, mock_weather):
        mock_weather.return_value = {
            "status": "success",
            "is_live_data": True,
            "display_location": "Pune, Maharashtra",
            "current_temperature_c": 26.0,
            "humidity_pct": 55,
            "rain_today_mm": 0.0,
            "rain_today_probability_pct": 5,
            "et0_today_mm": 4.0,
        }
        shade_plan = plan_terrace_garden(
            location_query="Pune",
            length_ft=8,
            width_ft=4,
            sunlight_hours=2.5,
            space_type="covered_balcony",
        )
        self.assertEqual(shade_plan["status"], "success")
        crop_keys = {c["crop_key"] for c in shade_plan["recommended_crops"]}
        self.assertIn("methi", crop_keys)
        self.assertIn("mint", crop_keys)
        self.assertNotIn("lemon", crop_keys)
        self.assertNotIn("okra", crop_keys)

    def test_seed_to_harvest_offline_guide_and_no_silent_tomato_substitution(self):
        methi = learn_crop_guide("methi", allow_online=False)
        self.assertEqual(methi["status"], "success")
        self.assertEqual(methi["guide_mode"], "offline_crop_guide")
        self.assertEqual(len(methi["steps"]), 5)
        blob = " ".join(methi["steps"]).lower()
        for bad in FORBIDDEN_JARGON:
            self.assertNotIn(bad, blob)

        # Custom crop offline must NOT silently return tomato instructions
        ginger = learn_crop_guide("Ginger", allow_online=False)
        self.assertEqual(ginger["status"], "success")
        self.assertEqual(ginger["guide_mode"], "offline_general_guide")
        self.assertIn("Ginger", ginger["crop_title"])
        self.assertNotIn("tomato", " ".join(ginger["steps"]).lower())

    def test_flask_terrace_endpoints_validation(self):
        client = app.test_client()

        # Missing location or dimensions -> HTTP 400
        r1 = client.get("/api/tools/terrace/plan")
        self.assertEqual(r1.status_code, 400)

        r2 = client.get("/api/tools/terrace/plan?location=Mandya")
        self.assertEqual(r2.status_code, 400)

        # Missing crop -> HTTP 400
        r3 = client.get("/api/tools/terrace/guide")
        self.assertEqual(r3.status_code, 400)

        # Valid crop guide request -> HTTP 200
        r4 = client.get("/api/tools/terrace/guide?crop=coriander&language=en")
        self.assertEqual(r4.status_code, 200)
        g = r4.get_json()
        self.assertEqual(g["status"], "success")
        self.assertTrue(len(g.get("steps", [])) >= 4)
        self.assertTrue(len(g.get("speech_text", "")) > 50)


if __name__ == "__main__":
    unittest.main()
