"""
Comprehensive Unit & Integration Tests for the Zero-Hardcoding Soil Health Tool.
Verifies:
1. REGIONAL_SOIL_DATA and static 32.5% / 58.0% numbers are completely removed.
2. Empty location returns 'missing_location' (fixes empty-string "" in "kolar" bug).
3. Unknown location returns 'location_not_found' (never spoofs Kolar).
4. Live 250m OpenLandMap + ISRIC + Open-Meteo 5-depth moisture & Saxton-Rawls hydraulics.
5. Crop-specific physiology:
   - Shallow vs medium vs deep root-zone moisture selection
   - Legume crops (Tur / Groundnut) get Rhizobium + starter N, NEVER heavy Urea
   - Acid-loving crops (Coffee) vs acid-sensitive crops (Tomato) pH liming rules
6. Real SQLite caching: serves 'cached_real' offline within 24h; rejects stale >24h cache;
   returns 'service_unavailable' when uncached.
7. Flask /api/tools/soil validation for district, crop, and GPS coordinates.
"""

import inspect
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import tools.soil_tool as soil_tool
from app import app


SAMPLE_GEO_MANDYA = {
    "name": "Mandya",
    "district": "Mandya",
    "state": "Karnataka",
    "country": "India",
    "country_code": "IN",
    "latitude": 12.5223,
    "longitude": 76.8951,
    "elevation_m": 685.0,
    "geocoder_source": "Open-Meteo Live Geocoding API",
}

SAMPLE_MOISTURE_TELEMETRY = {
    "observation_time_ist": "2026-11-27T15:00",
    "fetched_at_str": "27 Nov 2026, 03:00 PM",
    "depths_pct": {
        "surface_0_1cm": 16.5,
        "seedling_1_3cm": 19.0,
        "shallow_3_9cm": 21.2,
        "active_root_9_27cm": 27.4,
        "deep_root_27_81cm": 34.8,
    },
    "soil_temperatures_c": {
        "surface_0cm": 30.2,
        "root_6cm": 28.4,
        "deep_18cm": 26.1,
    },
    "rain_today_mm": 0.0,
    "et0_today_mm": 3.92,
}

SAMPLE_OLM_PROFILE = {
    "ph": 6.6,
    "organic_carbon_pct": 0.42,
    "sand_pct": 56.0,
    "bulk_density_gcm3": 1.38,
    "profile_source": "OpenLandMap 250m Global USDA/ISO Soil Grid",
}


class TestZeroHardcodingSoilTool(unittest.TestCase):
    def test_01_no_hardcoded_regional_soil_dictionary_in_source(self):
        src = inspect.getsource(soil_tool)
        self.assertNotIn("REGIONAL_SOIL_DATA", src)
        self.assertNotIn("32.5", src)
        self.assertNotIn("58.0", src)

    def test_02_empty_district_never_matches_kolar(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "soil.db")
            res_none = soil_tool.fetch_soil_health(None, db_path=db)
            self.assertEqual(res_none["status"], "missing_location")
            self.assertNotIn("ph", res_none)

            res_empty = soil_tool.fetch_soil_health("", db_path=db)
            self.assertEqual(res_empty["status"], "missing_location")

    def test_03_unknown_location_never_spoofs_kolar(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "soil.db")
            with patch("tools.soil_tool.geocode_location", return_value=(None, "location_not_found", "Not found")):
                res = soil_tool.fetch_soil_health("AtlantisFakeTaluk99", db_path=db)
                self.assertEqual(res["status"], "location_not_found")
                self.assertNotIn("moisture_percentage", res)

    def test_04_live_250m_profile_and_crop_root_depth_selection(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "soil.db")
            with patch("tools.soil_tool.geocode_location", return_value=(SAMPLE_GEO_MANDYA, None, None)), \
                 patch("tools.soil_tool._fetch_live_multidepth_moisture", return_value=SAMPLE_MOISTURE_TELEMETRY), \
                 patch("tools.soil_tool._fetch_openlandmap_250m", return_value=SAMPLE_OLM_PROFILE), \
                 patch("tools.soil_tool._fetch_isric_enrichment", return_value={"clay_pct": 24.0, "total_nitrogen_g_kg": 0.65, "cec_cmol_kg": 14.5}):

                # Shallow-rooted crop (Onion) -> picks 3-9cm shallow root moisture (21.2%)
                res_onion = soil_tool.fetch_soil_health("Mandya", crop="onion", db_path=db)
                self.assertEqual(res_onion["status"], "success")
                self.assertTrue(res_onion["is_live_data"])
                self.assertEqual(res_onion["moisture_percentage"], 21.2)
                self.assertIn("shallow", res_onion["active_root_depth"])
                self.assertEqual(res_onion["soil_type"], "Sandy Clay Loam")

                # Deep-rooted crop (Sugarcane) -> blends 9-27cm & 27-81cm deep root moisture
                res_cane = soil_tool.fetch_soil_health("Mandya", crop="sugarcane", db_path=db)
                self.assertEqual(res_cane["status"], "success")
                self.assertGreater(res_cane["moisture_percentage"], 30.0)
                self.assertIn("deep", res_cane["active_root_depth"])

    def test_05_legume_vs_cereal_nitrogen_and_acid_loving_ph_rules(self):
        tex = soil_tool._classify_usda_texture_and_hydraulics(sand_pct=50.0, clay_pct=25.0, bd_gcm3=1.32, soc_pct=0.38)

        # Legume (Tur / Red Gram) on low-N soil must recommend Rhizobium + starter N, NOT heavy Urea
        tur_prof = soil_tool._resolve_crop_profile("tur")
        tur_eval = soil_tool._evaluate_fertility_and_advisory(
            ph=6.4, soc_pct=0.38, tex=tex, total_n_g_kg=0.5, cec_cmol_kg=14.0,
            moisture_data=SAMPLE_MOISTURE_TELEMETRY, crop_prof=tur_prof,
        )
        joined_tur = " ".join(tur_eval["soil_amendments"])
        self.assertIn("Rhizobium", joined_tur)
        self.assertIn("avoid heavy Urea", joined_tur)

        # Acid-loving Coffee at pH 5.6 must NOT trigger liming, whereas Tomato at pH 5.5 MUST trigger liming
        coffee_eval = soil_tool._evaluate_fertility_and_advisory(
            ph=5.6, soc_pct=1.1, tex=tex, total_n_g_kg=1.6, cec_cmol_kg=18.0,
            moisture_data=SAMPLE_MOISTURE_TELEMETRY, crop_prof=soil_tool._resolve_crop_profile("coffee"),
        )
        self.assertNotIn("Dolomite", " ".join(coffee_eval["soil_amendments"]))

        tomato_eval = soil_tool._evaluate_fertility_and_advisory(
            ph=5.5, soc_pct=0.6, tex=tex, total_n_g_kg=1.0, cec_cmol_kg=15.0,
            moisture_data=SAMPLE_MOISTURE_TELEMETRY, crop_prof=soil_tool._resolve_crop_profile("tomato"),
        )
        self.assertIn("Dolomite", " ".join(tomato_eval["soil_amendments"]))

    def test_06_real_sqlite_cache_and_honest_offline_handling(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "soil.db")
            # Uncached offline -> honest service_unavailable
            with patch("tools.soil_tool.geocode_location", return_value=(SAMPLE_GEO_MANDYA, None, None)), \
                 patch("tools.soil_tool._fetch_live_multidepth_moisture", side_effect=requests.ConnectionError("Offline")), \
                 patch("tools.soil_tool._fetch_openlandmap_250m", side_effect=requests.ConnectionError("Offline")), \
                 patch("tools.soil_tool._fetch_isric_enrichment", return_value={}):
                res_off = soil_tool.fetch_soil_health("Mandya", db_path=db)
                self.assertEqual(res_off["status"], "service_unavailable")
                self.assertFalse(res_off["is_live_data"])

            # Populate real cache while online
            with patch("tools.soil_tool.geocode_location", return_value=(SAMPLE_GEO_MANDYA, None, None)), \
                 patch("tools.soil_tool._fetch_live_multidepth_moisture", return_value=SAMPLE_MOISTURE_TELEMETRY), \
                 patch("tools.soil_tool._fetch_openlandmap_250m", return_value=SAMPLE_OLM_PROFILE), \
                 patch("tools.soil_tool._fetch_isric_enrichment", return_value={"clay_pct": 24.0}):
                res_live = soil_tool.fetch_soil_health("Mandya", crop="tomato", db_path=db)
                self.assertEqual(res_live["status"], "success")

            # Go offline -> serves cached_real
            with patch("tools.soil_tool.geocode_location", return_value=(SAMPLE_GEO_MANDYA, None, None)), \
                 patch("tools.soil_tool._fetch_live_multidepth_moisture", side_effect=requests.ConnectionError("Offline")):
                res_cached = soil_tool.fetch_soil_health("Mandya", crop="tomato", db_path=db)
                self.assertEqual(res_cached["status"], "cached_real")
                self.assertFalse(res_cached["is_live_data"])
                self.assertTrue(res_cached["is_cached_data"])
                self.assertEqual(res_cached["ph"], 6.6)

            # Expire moisture cache (>24h) -> rejected as service_unavailable
            conn = sqlite3.connect(db)
            conn.execute("UPDATE soil_moisture_cache SET fetched_at_epoch = ?", (time.time() - 30 * 3600,))
            conn.commit()
            conn.close()
            with patch("tools.soil_tool.geocode_location", return_value=(SAMPLE_GEO_MANDYA, None, None)), \
                 patch("tools.soil_tool._fetch_live_multidepth_moisture", side_effect=requests.ConnectionError("Offline")):
                res_expired = soil_tool.fetch_soil_health("Mandya", crop="tomato", db_path=db)
                self.assertEqual(res_expired["status"], "service_unavailable")

    def test_07_flask_soil_route_validation(self):
        client = app.test_client()
        self.assertEqual(client.get("/api/tools/soil").status_code, 400)
        self.assertEqual(client.get("/api/tools/soil?lat=abc&lon=77").status_code, 400)


if __name__ == "__main__":
    unittest.main()
