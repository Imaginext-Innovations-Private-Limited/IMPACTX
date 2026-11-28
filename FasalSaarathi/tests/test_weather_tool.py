"""
Comprehensive Unit & Integration Tests for the Zero-Hardcoding Weather Tool.
Verifies:
1. No hardcoded LOCATION_COORDINATES dictionary or 27.5°C fake fallback in source.
2. Empty location returns 'missing_location' (never defaults to Kolar).
3. Unknown/nonexistent village returns 'location_not_found' (never spoofs Kolar).
4. Live geocoding resolution for arbitrary districts/villages/PIN codes & GPS coordinates.
5. Full agro-meteorological calculation: ET0, net water balance, 6-hour spray window, 7-day forecast.
6. Real SQLite caching: offline fallback serves ONLY genuine recent cached Open-Meteo data,
   rejecting expired (>24h) cache and returning 'service_unavailable' when uncached.
7. Dynamic morphological location extraction across all 6 languages without city lists.
"""

import inspect
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import tools.weather_tool as weather_tool
from agent.advisor_agent import FarmAdvisorAgent
from app import app


SAMPLE_OPEN_METEO_PAYLOAD = {
    "latitude": 12.522,
    "longitude": 76.895,
    "elevation": 685.0,
    "current": {
        "time": "2026-11-27T14:00",
        "temperature_2m": 29.4,
        "relative_humidity_2m": 58,
        "apparent_temperature": 31.1,
        "precipitation": 0.0,
        "rain": 0.0,
        "weather_code": 2,
        "wind_speed_10m": 11.2,
        "wind_gusts_10m": 16.5,
        "wind_direction_10m": 85,
    },
    "hourly": {
        "time": [
            "2026-11-27T14:00",
            "2026-11-27T15:00",
            "2026-11-27T16:00",
            "2026-11-27T17:00",
            "2026-11-27T18:00",
            "2026-11-27T19:00",
        ],
        "temperature_2m": [29.4, 30.1, 29.0, 27.5, 25.8, 24.5],
        "relative_humidity_2m": [58, 55, 60, 66, 72, 76],
        "precipitation_probability": [10, 15, 20, 15, 10, 5],
        "precipitation": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "wind_speed_10m": [11.2, 12.0, 11.8, 10.5, 9.0, 8.2],
        "wind_gusts_10m": [16.5, 17.8, 17.0, 15.0, 13.2, 12.0],
        "et0_fao_evapotranspiration": [0.55, 0.52, 0.41, 0.25, 0.11, 0.06],
        "soil_temperature_0cm": [31.2, 31.8, 30.5, 28.4, 26.5, 25.1],
        "soil_moisture_0_to_1cm": [0.24, 0.23, 0.23, 0.22, 0.22, 0.22],
        "soil_moisture_3_to_9cm": [0.29, 0.29, 0.28, 0.28, 0.28, 0.28],
    },
    "daily": {
        "time": [
            "2026-11-27",
            "2026-11-28",
            "2026-11-29",
            "2026-11-30",
            "2026-12-01",
            "2026-12-02",
            "2026-12-03",
        ],
        "weather_code": [2, 3, 61, 61, 2, 1, 0],
        "temperature_2m_max": [30.5, 29.8, 27.4, 27.9, 29.1, 30.0, 30.4],
        "temperature_2m_min": [18.2, 18.9, 19.4, 19.0, 18.1, 17.6, 17.4],
        "precipitation_sum": [0.0, 1.2, 8.5, 4.2, 0.0, 0.0, 0.0],
        "precipitation_probability_max": [20, 35, 75, 60, 15, 10, 5],
        "wind_speed_10m_max": [12.5, 14.0, 18.2, 15.6, 11.8, 10.9, 10.5],
        "wind_gusts_10m_max": [18.0, 21.0, 29.5, 24.0, 17.5, 16.0, 15.5],
        "et0_fao_evapotranspiration": [4.35, 3.95, 2.80, 3.10, 4.15, 4.40, 4.55],
        "uv_index_max": [7.5, 6.8, 5.2, 5.9, 7.2, 7.6, 7.8],
    },
}


class TestZeroHardcodingWeatherTool(unittest.TestCase):
    def test_01_no_hardcoded_coordinates_or_fake_fallback_in_source(self):
        src = inspect.getsource(weather_tool)
        self.assertNotIn("LOCATION_COORDINATES", src)
        self.assertNotIn("fallback_simulated", src)
        self.assertNotIn("27.5", src)

    def test_02_missing_location_never_defaults_to_kolar(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "cache.db")
            res = weather_tool.fetch_live_weather(None, db_path=db)
            self.assertEqual(res["status"], "missing_location")
            self.assertFalse(res["is_live_data"])
            self.assertNotIn("current_temperature_c", res)

            res_blank = weather_tool.fetch_live_weather("   ", db_path=db)
            self.assertEqual(res_blank["status"], "missing_location")

    def test_03_unknown_location_returns_not_found_never_spoofs_kolar(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "cache.db")
            mock_empty = MagicMock(status_code=200)
            mock_empty.json.return_value = {"results": []}

            mock_nom_empty = MagicMock(status_code=200)
            mock_nom_empty.json.return_value = []

            with patch("tools.weather_tool.requests.get", side_effect=[mock_empty, mock_nom_empty]):
                res = weather_tool.fetch_live_weather("NonExistentVillageXYZ999", db_path=db)
                self.assertEqual(res["status"], "location_not_found")
                self.assertEqual(res["requested_location"], "NonExistentVillageXYZ999")
                self.assertNotIn("current_temperature_c", res)

    def test_04_live_geocoding_and_agro_telemetry_computation(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "cache.db")
            geo_resp = MagicMock(status_code=200)
            geo_resp.json.return_value = {
                "results": [
                    {
                        "name": "Mandya",
                        "admin2": "Mandya",
                        "admin1": "Karnataka",
                        "country": "India",
                        "country_code": "IN",
                        "latitude": 12.5223,
                        "longitude": 76.8951,
                        "elevation": 685.0,
                    }
                ]
            }
            wx_resp = MagicMock(status_code=200)
            wx_resp.json.return_value = SAMPLE_OPEN_METEO_PAYLOAD

            with patch("tools.weather_tool.requests.get", side_effect=[geo_resp, wx_resp]):
                res = weather_tool.fetch_live_weather("Mandya", db_path=db)

            self.assertEqual(res["status"], "success")
            self.assertTrue(res["is_live_data"])
            self.assertEqual(res["location"], "Mandya")
            self.assertEqual(res["state"], "Karnataka")
            self.assertAlmostEqual(res["coordinates"]["latitude"], 12.5223, places=3)
            self.assertEqual(res["current_temperature_c"], 29.4)
            self.assertEqual(res["et0_today_mm"], 4.35)
            self.assertEqual(res["net_water_balance_mm"], -4.35)
            self.assertEqual(res["topsoil_moisture_pct"], 24.0)
            self.assertTrue(res["safe_to_spray_now"])
            self.assertEqual(res["spray_code"], "IDEAL_FOR_SPRAYING")
            self.assertEqual(len(res["daily_forecast"]), 7)

            # Now simulate network outage: must serve REAL cached Mandya telemetry, labeled cached_real
            with patch("tools.weather_tool.requests.get", side_effect=requests.ConnectionError("Offline")):
                cached_res = weather_tool.fetch_live_weather("Mandya", db_path=db)

            self.assertEqual(cached_res["status"], "cached_real")
            self.assertFalse(cached_res["is_live_data"])
            self.assertTrue(cached_res["is_cached_data"])
            self.assertEqual(cached_res["current_temperature_c"], 29.4)
            self.assertEqual(cached_res["location"], "Mandya")

    def test_05_uncached_offline_returns_honest_service_unavailable(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "cache.db")
            with patch("tools.weather_tool.requests.get", side_effect=requests.ConnectionError("Offline")):
                # Pass direct GPS so geocoding succeeds, testing pure weather API offline behavior
                res = weather_tool.fetch_live_weather(lat=15.3647, lon=75.1240, db_path=db)
                self.assertEqual(res["status"], "service_unavailable")
                self.assertFalse(res["is_live_data"])
                self.assertNotIn("current_temperature_c", res)

    def test_06_stale_cache_older_than_24h_is_rejected(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "cache.db")
            weather_tool._save_cached_weather(13.0, 76.0, {"current_temperature_c": 26.0, "last_updated": "Old"}, db_path=db)
            # Backdate timestamp to 30 hours ago
            conn = sqlite3.connect(db)
            conn.execute("UPDATE weather_forecast_cache SET fetched_at_epoch = ?", (time.time() - 30 * 3600,))
            conn.commit()
            conn.close()

            with patch("tools.weather_tool.requests.get", side_effect=requests.ConnectionError("Offline")):
                res = weather_tool.fetch_live_weather(lat=13.0, lon=76.0, db_path=db)
                self.assertEqual(res["status"], "service_unavailable")

    def test_07_spray_hazard_detection_rain_and_wind(self):
        win_rainy = {"max_rain_prob_pct": 80, "total_rain_mm": 4.2, "max_wind_kmh": 10.0, "max_gust_kmh": 14.0}
        adv_rain = weather_tool._compute_agro_advisories(
            temp_c=26.0, humidity_pct=82, wind_kmh=9.0, gust_kmh=13.0,
            curr_precip_mm=0.0, rain_today_prob=80, rain_today_mm=12.0,
            rain_tom_prob=40, rain_tom_mm=2.0, et0_today_mm=2.5,
            win6h=win_rainy, daily_7d=[{"rain_mm": 12.0, "rain_prob_pct": 80}],
        )
        self.assertEqual(adv_rain["irrigation_code"], "DO_NOT_IRRIGATE")
        self.assertFalse(adv_rain["safe_to_spray_now"])
        self.assertEqual(adv_rain["spray_code"], "AVOID_SPRAYING")

        win_windy = {"max_rain_prob_pct": 5, "total_rain_mm": 0.0, "max_wind_kmh": 24.0, "max_gust_kmh": 31.0}
        adv_wind = weather_tool._compute_agro_advisories(
            temp_c=28.0, humidity_pct=55, wind_kmh=21.0, gust_kmh=28.0,
            curr_precip_mm=0.0, rain_today_prob=5, rain_today_mm=0.0,
            rain_tom_prob=10, rain_tom_mm=0.0, et0_today_mm=4.2,
            win6h=win_windy, daily_7d=[{"rain_mm": 0.0, "rain_prob_pct": 5}],
        )
        self.assertFalse(adv_wind["safe_to_spray_now"])
        self.assertEqual(adv_wind["spray_code"], "HIGH_WIND_DRIFT")

    def test_08_dynamic_multilingual_location_extraction_zero_city_list(self):
        agent = FarmAdvisorAgent(api_key="")
        self.assertEqual(agent._extract_location("Check weather in Raichur today"), "Raichur")
        self.assertEqual(agent._extract_location("Davanagere rain forecast"), "Davanagere")
        self.assertEqual(agent._extract_location("Weather for 571401"), "571401")
        self.assertEqual(agent._extract_location("ಮಂಡ್ಯದಲ್ಲಿ ಇಂದು ಮಳೆ ಇದೆಯೇ?"), "ಮಂಡ್ಯ")
        self.assertEqual(agent._extract_location("ತುಮಕೂರಿನಲ್ಲಿ ಹವಾಮಾನ ಹೇಗಿದೆ?"), "ತುಮಕೂರು")
        self.assertEqual(agent._extract_location("इंदौर में आज बारिश होगी क्या?"), "इंदौर")
        self.assertEqual(agent._extract_location("மதுரையில் இன்று மழை வருமா?"), "மதுரை")
        self.assertEqual(agent._extract_location("వరంగల్లో ఈరోజు వర్షం పడుతుందా?"), "వరంగల్")
        self.assertEqual(agent._extract_location("कोल्हापूरमध्ये आज पाऊस पडेल का?"), "कोल्हापूर")
        # Must return None when no location is given
        self.assertIsNone(agent._extract_location("What is the weather today?"))
        self.assertIsNone(agent._extract_location("क्या आज बारिश होगी?"))

    def test_09_flask_weather_route_gps_and_validation(self):
        client = app.test_client()
        self.assertEqual(client.get("/api/tools/weather").status_code, 400)
        self.assertEqual(client.get("/api/tools/weather?lat=invalid&lon=77").status_code, 400)


if __name__ == "__main__":
    unittest.main()
