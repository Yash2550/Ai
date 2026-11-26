# -*- coding: utf-8 -*-
"""
test_ai_system.py - Comprehensive Test Suite for GOMZI BOB AI API Selector,
Prompt Composer & Multilingual Voice-to-Prompt Engine.
"""

import os
import sys
import json
import unittest

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai_provider_service
from app import app


class TestAiSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_01_provider_catalog_registry(self):
        """Test provider catalog definitions, keys, and model lists."""
        providers = ai_provider_service.get_provider_status()
        self.assertGreaterEqual(len(providers), 5)
        p_ids = [p["id"] for p in providers]
        self.assertIn("gemini", p_ids)
        self.assertIn("openai", p_ids)
        self.assertIn("recraft", p_ids)
        self.assertIn("nanobanana", p_ids)
        self.assertIn("auto", p_ids)

        for p in providers:
            # Verify no complete unmasked secret keys are exposed
            if p["is_configured"] and p["id"] != "auto":
                self.assertIn("••••••••", p["masked_key"])
                self.assertLess(len(p["masked_key"]), 20)
            self.assertGreater(len(p["models"]), 0)

    def test_02_get_ai_providers_endpoint(self):
        """Test GET /api/ai/providers endpoint."""
        resp = self.client.get("/api/ai/providers")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(data.get("count", 0), 5)

    def test_03_get_ai_presets_endpoint(self):
        """Test GET /api/ai/presets endpoint."""
        resp = self.client.get("/api/ai/presets")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        presets = data.get("presets", [])
        self.assertGreaterEqual(len(presets), 6)
        preset_ratios = [p["aspect_ratio"] for p in presets]
        self.assertIn("3:1", preset_ratios)
        self.assertIn("1:1", preset_ratios)
        self.assertIn("7:11", preset_ratios)

    def test_04_test_connection_endpoint(self):
        """Test POST /api/ai/test-connection for Gemini, OpenAI, and Auto."""
        # Test Gemini
        resp = self.client.post("/api/ai/test-connection", json={"provider": "gemini"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("latency_ms", data)
        print(f"Gemini connection verified ({data['latency_ms']}ms)")

        # Test OpenAI
        resp2 = self.client.post("/api/ai/test-connection", json={"provider": "openai"})
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertTrue(data2.get("success"))
        print(f"OpenAI connection verified ({data2['latency_ms']}ms)")

        # Test Auto
        resp3 = self.client.post("/api/ai/test-connection", json={"provider": "auto"})
        self.assertEqual(resp3.status_code, 200)
        data3 = resp3.get_json()
        self.assertTrue(data3.get("success"))

    def test_05_multilingual_prompt_enhancement_gujarati(self):
        """
        Test POST /api/ai/enhance-prompt with Gujarati input:
        'મારે ગોમઝીનું એક કિલો વે પ્રોટીનનું લેબલ બનાવવું છે, બ્લેક અને ગોલ્ડ કલરમાં, ચોકલેટ ફ્લેવર રાખવાનું છે અને જાર નથી જોઈતો.'
        """
        payload = {
            "prompt": "મારે ગોમઝીનું એક કિલો વે પ્રોટીનનું લેબલ બનાવવું છે, બ્લેક અને ગોલ્ડ કલરમાં, ચોકલેટ ફ્લેવર રાખવાનું છે અને જાર નથી જોઈતો.",
            "language": "gu-IN",
            "aspect_ratio": "3:1"
        }
        resp = self.client.post("/api/ai/enhance-prompt", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("detected_brand"), "GOMZI NUTRITION")
        self.assertEqual(data.get("detected_product"), "Whey Protein")
        self.assertEqual(data.get("detected_flavor"), "Belgian Chocolate")
        self.assertEqual(data.get("detected_weight"), "1 kg | 30 Servings")
        
        enhanced = data.get("enhanced_prompt", "")
        self.assertIn("flat", enhanced.lower())
        self.assertIn("no 3d jar container mockup", enhanced.lower())
        self.assertIn("gold", enhanced.lower())
        self.assertIn("nutrition facts", enhanced.lower())
        print(f"Enhanced prompt from Gujarati: {len(enhanced)} chars")

    def test_06_multilingual_prompt_enhancement_hindi(self):
        """
        Test POST /api/ai/enhance-prompt with Hindi input:
        'मुझे गोमजी न्यूट्रिशन का दो किलो व्हे प्रोटीन का लेबल बनाना है, वैनिला फ्लेवर'
        """
        payload = {
            "prompt": "मुझे गोमजी न्यूट्रिशन का दो किलो व्हे प्रोटीन का लेबल बनाना है, वैनिला फ्लेवर",
            "language": "hi-IN",
            "aspect_ratio": "3:1"
        }
        resp = self.client.post("/api/ai/enhance-prompt", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("detected_brand"), "GOMZI NUTRITION")
        self.assertEqual(data.get("detected_product"), "Whey Protein")
        self.assertEqual(data.get("detected_weight"), "2 kg | 60 Servings")
        self.assertEqual(data.get("detected_flavor"), "French Vanilla")

    def test_07_frontend_dom_elements(self):
        """Verify all requested UI elements exist in templates/index.html."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            html = f.read()

        required_ids = [
            "aiProviderSelect",
            "aiModelSelect",
            "aiLanguageSelect",
            "aiPromptInput",
            "btnVoiceInput",
            "voiceRecordingTray",
            "interimTranscript",
            "btnEnhancePrompt",
            "btnGenerateArtwork",
            "aiEnhancedReviewCard",
            "aiReviewPromptTextarea",
            "btnApplyEnhancedPrompt",
            "btnAttachCanvas",
            "btnAttachLogo",
            "btnAttachUpload",
            "aiAspectRatioContainer",
            "aiModelMetaStrip"
        ]

        for req_id in required_ids:
            self.assertIn(f'id="{req_id}"', html, f"Missing required element id: {req_id}")

        # Verify languages in aiLanguageSelect
        self.assertIn('value="gu-IN"', html)
        self.assertIn('value="hi-IN"', html)
        self.assertIn('value="en-IN"', html)
        self.assertIn('value="en-US"', html)

        # Verify JS initialization
        self.assertIn("initAiStudioEngine()", html)
        self.assertIn("renderAiSettingsModule", html)
        print("All 17 frontend UI components & JS bindings successfully verified in index.html!")


if __name__ == "__main__":
    unittest.main()
