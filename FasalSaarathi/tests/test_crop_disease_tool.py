"""
Unit & Integration Tests for KisanVaani Dual-Engine Leaf Disease Vision Doctor.
Verifies:
  1. Zero Latin / scientific names or technical pathology jargon in farmer outputs.
  2. 100% Offline Local PyTorch MobileNetV2 CNN + OpenCV detection with anonymized filenames & empty crop_hint.
  3. Unseen synthetic leaf symptom patterns (healthy leaf & white powder mildew).
  4. Honest rejection of non-leaf photos (grey wall, blue sky, white document) and missing files.
  5. Complete localization across all 6 languages (en, kn, hi, ta, te, mr) with 1L + 15L pump dosages.
  6. Online Gemini 2.5 Flash multimodal vision when GEMINI_API_KEY + network are available.
"""

import os
import shutil
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw

from tools.crop_disease_tool import analyze_leaf_image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(PROJECT_ROOT, "static", "sample_leaves")

FORBIDDEN_JARGON = (
    "hemileia", "vastatrix", "alternaria", "solani", "phytophthora", "infestans",
    "cercospora", "xanthomonas", "septoria", "oomycete", "necrotic", "chlorotic",
    "pustule", "conidia", "sporulation",
)


class TestCropDiseaseTool(unittest.TestCase):
    def _assert_zero_jargon(self, res: dict):
        self.assertEqual(res.get("scientific_name", ""), "")
        checked_fields = (
            "disease_name", "disease_name_en", "disease_name_kn", "disease_name_hi",
            "cause_simple", "pathogen_type", "symptoms_identified",
            "organic_prescription", "chemical_prescription", "application_protocol",
        )
        blob = " ".join(str(res.get(k, "")) for k in checked_fields).lower()
        for bad in FORBIDDEN_JARGON:
            self.assertNotIn(bad, blob, f"Forbidden scientific term '{bad}' leaked into output: {blob}")

    def test_missing_file_never_fakes_result(self):
        """A missing image path must return status='error', never guess from filename."""
        res = analyze_leaf_image("nonexistent_tomato_blight_coffee_rust.jpg", crop_hint="tomato", allow_online=False)
        self.assertEqual(res["status"], "error")
        self.assertNotIn("disease_name", res)

    def test_non_leaf_images_rejected(self):
        """Solid sky, grey concrete wall, and white paper images must be rejected as not_a_leaf."""
        non_leaves = [
            Image.new("RGB", (256, 256), color=(135, 195, 245)),  # blue sky
            Image.new("RGB", (256, 256), color=(140, 140, 140)),  # grey concrete
            Image.new("RGB", (256, 256), color=(248, 248, 245)),  # white paper document
        ]
        for img in non_leaves:
            res = analyze_leaf_image(img, crop_hint="tomato", allow_online=False)
            self.assertEqual(res["status"], "not_a_leaf", f"Expected non-leaf rejection, got: {res}")

    def test_offline_pytorch_cnn_anonymized_filenames_no_hint(self):
        """
        Copy sample leaves to random neutral filenames (img_a.jpg .. img_d.jpg) with crop_hint=''
        and allow_online=False. Must classify purely from pixels via local_pytorch_cnn.
        """
        cases = [
            ("coffee_rust.jpg", "img_a.jpg", "rust", False),
            ("tomato_blight.jpg", "img_b.jpg", "ring_spot", False),
            ("potato_late_blight.jpg", "img_c.jpg", "wet_rot", False),
            ("healthy_leaf.jpg", "img_d.jpg", "healthy", True),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            for src_name, anon_name, expected_group, expected_healthy in cases:
                src = os.path.join(SAMPLE_DIR, src_name)
                dst = os.path.join(tmpdir, anon_name)
                shutil.copyfile(src, dst)

                res = analyze_leaf_image(dst, crop_hint="", language="en", allow_online=False)
                self.assertEqual(res["status"], "success", f"Failed on {src_name}: {res}")
                self.assertEqual(res["analysis_mode"], "local_pytorch_cnn")
                self.assertEqual(
                    res["symptom_group"], expected_group,
                    f"Wrong offline group for anonymized {src_name}: got {res['symptom_group']} ({res['disease_name']})",
                )
                self.assertEqual(res["is_healthy"], expected_healthy)
                self.assertGreaterEqual(res["confidence_score"], 55.0)
                self._assert_zero_jargon(res)

    def test_unseen_synthetic_leaf_images_offline(self):
        """Brand-new unseen PIL leaf drawings must be classified from real pixel features."""
        # 1. Unseen healthy green leaf on dark soil background
        healthy_img = Image.new("RGB", (300, 300), color=(95, 75, 55))
        draw = ImageDraw.Draw(healthy_img)
        draw.ellipse((50, 40, 250, 260), fill=(55, 150, 50))
        res_h = analyze_leaf_image(healthy_img, crop_hint="chilli", language="en", allow_online=False)
        self.assertEqual(res_h["status"], "success")
        self.assertEqual(res_h["symptom_group"], "healthy")
        self.assertTrue(res_h["is_healthy"])
        self._assert_zero_jargon(res_h)

        # 2. Unseen leaf covered with white powdery patches
        powder_img = healthy_img.copy()
        pdraw = ImageDraw.Draw(powder_img)
        for box in [(85, 80, 145, 135), (155, 100, 215, 160), (105, 165, 180, 225)]:
            pdraw.ellipse(box, fill=(235, 238, 235))
        res_p = analyze_leaf_image(powder_img, crop_hint="grape", language="en", allow_online=False)
        self.assertEqual(res_p["status"], "success")
        self.assertEqual(res_p["symptom_group"], "white_powder")
        self.assertIn("15-litre", res_p["chemical_prescription"])
        self._assert_zero_jargon(res_p)

    def test_all_six_languages_plain_farmer_care(self):
        """Every supported language returns localized plain-language care with zero Latin terms."""
        sample_path = os.path.join(SAMPLE_DIR, "tomato_blight.jpg")
        expected_script_chars = {
            "en": "a",
            "kn": "\u0c9f",  # ಟ
            "hi": "\u091f",  # ट
            "ta": "\u0ba4",  # த
            "te": "\u0c1f",  # ట
            "mr": "\u091f",  # ट
        }
        for lang, ch in expected_script_chars.items():
            res = analyze_leaf_image(sample_path, crop_hint="tomato", language=lang, allow_online=False)
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["language"], lang)
            self.assertIn(ch, res["disease_name"], f"Expected {lang} script in {res['disease_name']}")
            self.assertTrue(bool(res["cause_simple"]))
            self.assertTrue(bool(res["organic_prescription"]))
            self.assertTrue(bool(res["chemical_prescription"]))
            self._assert_zero_jargon(res)

    def test_online_gemini_vision_and_latin_scrubber(self):
        """Online Gemini 2.5 Flash path parses multimodal JSON and scrubs any accidental Latin terms."""
        from unittest.mock import patch
        sample_path = os.path.join(SAMPLE_DIR, "coffee_rust.jpg")
        mock_gemini_payload = {
            "is_leaf": True,
            "crop": "Coffee",
            "disease_name": "Orange Powder Leaf Rust (Hemileia vastatrix)",
            "symptom_group": "rust",
            "cause_simple": "Fungus — spreads in damp weather",
            "confidence_score": 89,
            "severity": "medium",
            "symptoms_identified": "Round orange powdery spots under the leaf.",
            "organic_prescription": "Spray 5% neem seed water (750 g crushed seeds per 15-litre pump).",
            "chemical_prescription": "Hexaconazole 5% liquid — 2 ml per litre (30 ml per 15-litre pump).",
            "application_protocol": "Spray under the leaves on a dry morning.",
            "_model": "gemini-2.5-flash",
        }
        with patch("tools.crop_disease_tool._analyze_with_gemini_vision", return_value=mock_gemini_payload):
            res = analyze_leaf_image(sample_path, crop_hint="coffee", language="en", allow_online=True)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["analysis_mode"], "gemini_multimodal_vision")
        self.assertEqual(res["engine_model"], "gemini-2.5-flash")
        self.assertEqual(res["disease_name"], "Orange Powder Leaf Rust")
        self._assert_zero_jargon(res)

    def test_crop_specific_treatments_differ_across_crops(self):
        """Different crops with the same symptom group must receive crop-specific disease & medicine advice."""
        sample_path = os.path.join(SAMPLE_DIR, "tomato_blight.jpg")
        rice_res = analyze_leaf_image(sample_path, crop_hint="rice", language="en", allow_online=False)
        onion_res = analyze_leaf_image(sample_path, crop_hint="onion", language="en", allow_online=False)
        tomato_res = analyze_leaf_image(sample_path, crop_hint="tomato", language="en", allow_online=False)

        self.assertEqual(rice_res["status"], "success")
        self.assertEqual(onion_res["status"], "success")
        self.assertEqual(tomato_res["status"], "success")
        self.assertNotEqual(rice_res["chemical_prescription"], onion_res["chemical_prescription"])
        self.assertNotEqual(rice_res["chemical_prescription"], tomato_res["chemical_prescription"])
        self.assertIn("Tricyclazole", rice_res["chemical_prescription"])
        self.assertIn("sticker", onion_res["application_protocol"].lower())
        self._assert_zero_jargon(rice_res)
        self._assert_zero_jargon(onion_res)
        self._assert_zero_jargon(tomato_res)


if __name__ == "__main__":
    unittest.main()
