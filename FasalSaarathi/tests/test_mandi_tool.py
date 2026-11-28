"""
Unit Tests for KisanVaani Zero-Hardcoding APMC Mandi Market Tool.
"""

import inspect
import os
import tempfile
import unittest
from unittest.mock import patch

import tools.mandi_tool as mandi_mod
from app import app
from tools.mandi_tool import fetch_mandi_prices, resolve_commodity

FORBIDDEN_TRADING_JARGON = (
    "strong_bullish", "liquidate promptly", "hold or divert", "staggered selling recommended",
)


class TestZeroHardcodingMandiTool(unittest.TestCase):
    def setUp(self):
        self._orig_db = mandi_mod.CACHE_DB_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        mandi_mod.CACHE_DB_PATH = os.path.join(self._tmpdir.name, "test_mandi_cache.db")

    def tearDown(self):
        mandi_mod.CACHE_DB_PATH = self._orig_db
        self._tmpdir.cleanup()

    def test_01_no_hardcoded_commodity_price_database_in_source(self):
        src = inspect.getsource(mandi_mod)
        self.assertNotIn("COMMODITY_MANDI_DATABASE", src)
        for old_fake_price in ("2850", "54200", "64500", "18200"):
            self.assertNotIn(old_fake_price, src)

    def test_02_empty_or_unknown_commodity_never_defaults_to_tomato(self):
        empty_res = fetch_mandi_prices("", "Kolar", allow_online=False)
        self.assertEqual(empty_res["status"], "missing_commodity")
        self.assertNotIn("modal_price", empty_res)

        unk_res = fetch_mandi_prices("uranium_ore_xyz", "Kolar", allow_online=False)
        self.assertEqual(unk_res["status"], "commodity_not_found")
        self.assertNotIn("modal_price", unk_res)

    def test_03_unknown_location_never_spoofs_kolar(self):
        with patch("tools.mandi_tool.geocode_location", return_value=(None, "location_not_found", "Not found")):
            res = fetch_mandi_prices("tomato", "AtlantisMars99999", allow_online=False)
        self.assertEqual(res["status"], "location_not_found")
        self.assertNotIn("modal_price", res)

    def test_04_multilingual_crop_resolution_all_six_languages(self):
        pairs = [
            ("ಟೊಮೆಟೊ", "tomato"),
            ("ಭತ್ತ", "paddy"),
            ("ಅಡಿಕೆ", "arecanut"),
            ("प्याज", "onion"),
            ("धान", "paddy"),
            ("தக்காளி", "tomato"),
            ("మిర్చి", "green_chilli"),
            ("कांदा", "onion"),
            ("Ragi", "ragi"),
            ("Tur", "tur"),
        ]
        for query, expected_key in pairs:
            resolved = resolve_commodity(query)
            self.assertIsNotNone(resolved, f"Failed to resolve {query}")
            self.assertEqual(resolved[0], expected_key)

    def test_05_live_distance_ranking_msp_and_plain_language_all_langs(self):
        fake_geo_farmer = {
            "latitude": 13.1367, "longitude": 78.1292,
            "name": "Kolar", "district": "Kolar", "state": "Karnataka",
        }
        fake_records = [
            {
                "mandi": "Chamarajanagar APMC", "district": "Chamarajanagar", "state": "Karnataka",
                "variety": "Hybrid", "min_price": 2500, "modal_price": 3000, "max_price": 3500,
                "arrival_date": "27/11/2026", "source_name": "Agmarknet APMC Daily Arrivals",
            },
            {
                "mandi": "Srinivasapur APMC", "district": "Kolar", "state": "Karnataka",
                "variety": "Hybrid", "min_price": 2200, "modal_price": 2600, "max_price": 2900,
                "arrival_date": "27/11/2026", "source_name": "Agmarknet APMC Daily Arrivals",
            },
            {
                "mandi": "Ramanagara APMC", "district": "Ramanagara", "state": "Karnataka",
                "variety": "Hybrid", "min_price": 3000, "modal_price": 3600, "max_price": 4000,
                "arrival_date": "27/11/2026", "source_name": "Agmarknet APMC Daily Arrivals",
            },
        ]
        fake_series = [("27/11/2026", 2688.0), ("25/11/2026", 2347.0)]
        fake_agm = {"national_avg_price": 2700, "one_day_ago_price": 2550, "two_day_ago_price": 2400, "msp_price": 2410, "reported_date": "27-11-2026"}

        def fake_geo(location_query=None, lat=None, lon=None):
            q = (location_query or "").lower()
            if "kolar" in q:
                return (fake_geo_farmer, None, None)
            if "ramanagara" in q:
                return ({"latitude": 12.7209, "longitude": 77.2799, "name": "Ramanagara", "state": "Karnataka"}, None, None)
            return ({"latitude": 11.9261, "longitude": 76.9437, "name": "Chamarajanagar", "state": "Karnataka"}, None, None)

        with patch("tools.mandi_tool.geocode_location", side_effect=fake_geo), \
             patch("tools.mandi_tool._fetch_datagov_ogd_api", return_value=[]), \
             patch("tools.mandi_tool._fetch_kisandeals_apmc_live", return_value=(fake_records, fake_series)), \
             patch("tools.mandi_tool._fetch_agmarknet_official_summary", return_value=fake_agm):
            for lang in ("en", "kn", "hi", "ta", "te", "mr"):
                res = fetch_mandi_prices("maize", "Kolar", language=lang, allow_online=True)
                self.assertEqual(res["status"], "success")
                self.assertTrue(res["is_live_data"])
                # Kolar district mandi (Srinivasapur APMC) must rank #1 for a Kolar farmer!
                self.assertEqual(res["primary_mandi"], "Srinivasapur APMC")
                self.assertEqual(res["trend_code"], "UP")
                self.assertEqual(res["msp_price"], 2410)
                blob = (res["trend"] + " " + res["selling_advisory"]).lower()
                for bad in FORBIDDEN_TRADING_JARGON:
                    self.assertNotIn(bad, blob)

        # Verify offline SQLite cache works immediately after live fetch!
        with patch("tools.mandi_tool.geocode_location", return_value=(fake_geo_farmer, None, None)):
            cached = fetch_mandi_prices("maize", "Kolar", language="en", allow_online=False)
        self.assertEqual(cached["status"], "cached_real")
        self.assertFalse(cached["is_live_data"])
        self.assertEqual(cached["primary_mandi"], "Srinivasapur APMC")

        # Uncached crop offline must return honest service_unavailable
        uncached = fetch_mandi_prices("turmeric", "", language="en", allow_online=False)
        self.assertEqual(uncached["status"], "service_unavailable")
        self.assertNotIn("modal_price", uncached)

    def test_06_flask_mandi_route_validation(self):
        client = app.test_client()
        r1 = client.get("/api/tools/mandi?commodity=")
        self.assertEqual(r1.status_code, 400)
        r2 = client.get("/api/tools/mandi?commodity=tomato&lat=bad&lon=77.5")
        self.assertEqual(r2.status_code, 400)


if __name__ == "__main__":
    unittest.main()
