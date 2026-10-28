"""Core probe evidence guards; no renderer, font decoder or GPU is used here."""
import hashlib
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.capture_core_probe import encode_numbers, verify_environment


class CoreProbeEvidenceTests(unittest.TestCase):
    def test_rust_json_negative_zero_is_tagged_like_node(self):
        value = {"zero": -0.0, "nested": [0.0, True, float("nan"), float("inf"), -float("inf")]}
        self.assertEqual({"zero": {"$number": "-0"}, "nested": [0.0, True, {"$number": "NaN"},
                         {"$number": "Infinity"}, {"$number": "-Infinity"}]}, encode_numbers(value))
        json.dumps(encode_numbers(value), allow_nan=False)

    def test_font_bytes_are_verified_before_probe_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            resource = directory / "resource.bin"
            resource.write_bytes(b"hash-only-test-resource")
            fonts = [{"path": str(resource), "bytes": resource.stat().st_size,
                      "sha256": hashlib.sha256(resource.read_bytes()).hexdigest()}]
            canonical = json.dumps({"fonts": fonts, "configuration": []}, sort_keys=True, separators=(",", ":"))
            document = {"schema": "py-skia-canvas-environment/v1", "fontFiles": fonts, "fontConfiguration": [],
                        "fontResourcesSha256": hashlib.sha256(canonical.encode()).hexdigest()}
            manifest = directory / "environment.json"
            manifest.write_text(json.dumps(document), encoding="utf-8")
            self.assertEqual(document, verify_environment(manifest)[1])
            resource.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "resource changed"):
                verify_environment(manifest)


if __name__ == "__main__":
    unittest.main()
