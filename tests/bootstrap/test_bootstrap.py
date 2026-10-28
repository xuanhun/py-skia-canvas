"""Dependency-free bootstrap tests; no renderer, Node or GPU needed."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.compare_runs import json_differences, read_artifact, rgba_difference
from scripts.refresh_reference_index import build_indexes
from scripts.validate_bootstrap import validate, validate_fixtures


class InventoryTests(unittest.TestCase):
    def test_starter_documents_and_source_fingerprints(self):
        result = validate()
        self.assertEqual([], result["errors"])
        self.assertEqual("BOOTSTRAP_VALIDATED", result["status"])

    def test_inventory_is_deterministic(self):
        self.assertEqual(build_indexes(), build_indexes())

    def test_native_exports_are_unique_and_locatable(self):
        _, index = build_indexes()
        names = [entry["name"] for entry in index["nativeExports"]]
        self.assertEqual(len(names), len(set(names)))
        for entry in index["nativeExports"]:
            line = (ROOT / entry["source"]).read_text(encoding="utf-8").splitlines()[entry["line"] - 1]
            self.assertIn(f'"{entry["name"]}"', line)
        self.assertIn("Canvas", index["publicExports"])
        self.assertIn("FontLibrary", index["publicExports"])
        self.assertIn("App", index["publicExports"])

    def test_source_snapshot_excludes_old_private_packages(self):
        manifest, _ = build_indexes()
        self.assertEqual(49, len(manifest["files"]))
        self.assertFalse(any("node_modules" in item["path"] or "artifact-tool" in item["path"] for item in manifest["files"]))
        self.assertIn("references/upstream/** -text", (ROOT / ".gitattributes").read_text(encoding="utf-8"))


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / "tests/fixtures/scenarios.json").read_text(encoding="utf-8"))

    def test_meaningful_groups_with_gpu_default_and_cpu_diagnostic(self):
        self.assertEqual([], validate_fixtures(self.document))
        self.assertGreaterEqual(len(self.document["cases"]), 25)
        self.assertGreaterEqual(len({c["group"] for c in self.document["cases"]}), 10)
        self.assertEqual({"default", "cpu-setter", "constructor-false"}, {c["mode"] for c in self.document["cases"]})

    def test_duplicate_case_rejected(self):
        self.document["cases"].append(copy.deepcopy(self.document["cases"][0]))
        self.assertTrue(any("duplicate case" in error for error in validate_fixtures(self.document)))

    def test_unknown_resource_rejected(self):
        self.document["cases"][0]["ops"].append({"op": "set", "target": "ctx", "name": "fillStyle", "value": {"$ref": "missing"}})
        self.assertTrue(any("undeclared resource" in error for error in validate_fixtures(self.document)))

    def test_external_asset_rejected(self):
        self.document["cases"][0]["ops"].append({"op": "loadImage", "id": "image", "path": "../outside.svg"})
        self.assertTrue(any("tests/assets" in error for error in validate_fixtures(self.document)))

    def test_invalid_operation_and_number_tag_rejected(self):
        self.document["cases"][0]["ops"].append({"op": "eval", "value": {"$number": "not-a-number-tag"}})
        errors = validate_fixtures(self.document)
        self.assertTrue(any("unknown operation" in error for error in errors))
        self.assertTrue(any("invalid number tag" in error for error in errors))

    def test_same_reference_observation_requires_both_operands(self):
        self.document["cases"][0]["ops"].append({"op": "sameRef", "left": {"$ref": "ctx"}, "save": "same"})
        self.assertTrue(any("sameRef missing operand" in error for error in validate_fixtures(self.document)))


class ExactComparisonTests(unittest.TestCase):
    def test_numeric_values_allow_json_integer_float_representation_only(self):
        self.assertEqual([], json_differences({"width": 1}, {"width": 1.0}))
        self.assertTrue(json_differences(1, 1.00000000000001))

    def test_boolean_is_not_a_number(self):
        self.assertTrue(json_differences(True, 1))

    def test_negative_zero_and_special_tags_remain_distinct(self):
        self.assertTrue(json_differences({"$number": "-0"}, 0))
        self.assertEqual([], json_differences({"$number": "NaN"}, {"$number": "NaN"}))
        self.assertTrue(json_differences(float("nan"), float("nan")))
        self.assertTrue(json_differences(-0.0, 0.0))

    def test_missing_nested_metric_is_a_difference(self):
        self.assertTrue(json_differences({"lines": [{"width": 1}]}, {"lines": [{}]}))

    def test_rgba_exact_no_uint8_overflow(self):
        self.assertEqual({"changedPixels": 1, "changedChannels": 2, "maxChannelDelta": 255},
                         rgba_difference(bytes([0, 20, 0, 0]), bytes([255, 19, 0, 0]), 1, 1))

    def test_transparent_rgb_still_counts(self):
        self.assertEqual(1, rgba_difference(bytes([0, 0, 0, 0]), bytes([1, 0, 0, 0]), 1, 1)["changedPixels"])

    def test_wrong_dimensions_fail(self):
        with self.assertRaises(ValueError):
            rgba_difference(b"1234", b"1234", 2, 1)

    def test_artifact_hash_and_path_are_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = b"original"
            (root / "pixel.rgba").write_bytes(data)
            descriptor = {"path": "pixel.rgba", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            self.assertEqual(data, read_artifact(root, descriptor))
            (root / "pixel.rgba").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                read_artifact(root, descriptor)
            with self.assertRaises(ValueError):
                read_artifact(root, {**descriptor, "path": "../outside"})


if __name__ == "__main__":
    unittest.main()
