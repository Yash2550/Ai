import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')

class TestGoogleFlowAPI(unittest.TestCase):

    def test_aspect_ratio_mapping(self):
        import google_flow_api
        self.assertEqual(google_flow_api.map_aspect_ratio("1:1"), "1:1")
        self.assertEqual(google_flow_api.map_aspect_ratio("16:9"), "16:9")
        self.assertEqual(google_flow_api.map_aspect_ratio("3:1"), "16:9")
        self.assertEqual(google_flow_api.map_aspect_ratio("9:16"), "9:16")
        self.assertEqual(google_flow_api.map_aspect_ratio("auto"), "auto")
        print("[PASS] Google Flow aspect ratio mapping verified.")

    def test_missing_credentials_error(self):
        import google_flow_api
        with self.assertRaises(ValueError) as ctx:
            google_flow_api.generate_google_flow_image("Test prompt", api_token="", email="")
        self.assertIn("Google Flow API token is missing", str(ctx.exception))
        print("[PASS] Missing credentials error handled gracefully.")

    @patch("google_flow_api.requests.post")
    def test_mock_successful_generation(self, mock_post):
        import google_flow_api

        # Mock response from useapi.net /images endpoint
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "media": [
                {
                    "image": {
                        "generatedImage": {
                            "encodedImage": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                        }
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        result = google_flow_api.generate_google_flow_image(
            prompt="Luxury whey protein label",
            model="nano-banana-2-lite",
            aspect_ratio="1:1",
            count=1,
            api_token="user:test-token",
            email="test@gmail.com"
        )

        self.assertTrue(result["success"])
        self.assertEqual(len(result["images"]), 1)
        self.assertTrue(result["primary_data_uri"].startswith("data:image/jpeg;base64,"))
        print("[PASS] Mock Google Flow image generation works end-to-end.")

    def test_flask_endpoint_registration(self):
        import app
        client = app.app.test_client()

        # Test Canva endpoint with empty body
        resp = client.post("/api/canva/google-flow-generate", json={})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Prompt", resp.get_json()["error"])
        print("[PASS] Flask endpoint /api/canva/google-flow-generate registered and validates input.")

if __name__ == "__main__":
    unittest.main()
