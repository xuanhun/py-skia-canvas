"""Full run comparison negative controls, with a mock PNG decoder to stay stdlib-only."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.compare_runs import compare_runs


class RunComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.left = self.make_run("left")
        self.right = self.make_run("right")

    def make_run(self, name, pixels=b"\0\0\0\0", metric=1, renderer="GPU"):
        directory = self.base / name
        directory.mkdir(exist_ok=True)
        artifacts = {}
        for kind, data in (("rgba", pixels), ("png", b"mock-png")):
            (directory / kind).write_bytes(data)
            artifacts[kind] = {"path": kind, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        report = {"schema": "py-skia-canvas-test-run/v1", "status": "ORACLE_CAPTURED", "role": "node-oracle",
                  "fixtureSha256": "same-fixture", "environment": {"platform": "test", "host": "host"},
                  "cases": [{"id": "test", "mode": "default", "width": 1, "height": 1, "status": "CAPTURED",
                             "pixelFormat": "RGBA8-unpremultiplied-readback", "backend": {"renderer": renderer},
                             "observations": {"metric": metric}, "artifacts": artifacts}]}
        (directory / "run.json").write_text(json.dumps(report), encoding="utf-8")
        return directory

    def compare(self):
        with patch("scripts.compare_runs.decoded_png", return_value=((1, 1), b"\0\0\0\0")):
            return compare_runs(self.left, self.right)

    def test_same_oracle_never_claims_python_parity(self):
        result = self.compare()
        self.assertEqual("MATCHED_RECORDS", result["status"])
        self.assertNotIn("PARITY_PASSED", json.dumps(result))

    def test_fractional_canvas_records_actual_artifact_dimensions(self):
        for directory in (self.left,self.right):
            path=directory/'run.json';report=json.loads(path.read_text())
            report['cases'][0].update(width=1.25,height=1.5,artifactDimensions={'rgba':[1,1],'png':[1,1]})
            path.write_text(json.dumps(report),encoding='utf-8')
        self.assertEqual('MATCHED_RECORDS',self.compare()['status'])

    def test_artifact_dimensions_mismatch_is_not_hidden(self):
        path=self.right/'run.json';report=json.loads(path.read_text())
        report['cases'][0]['artifactDimensions']={'rgba':[1,1],'png':[1,1]}
        path.write_text(json.dumps(report),encoding='utf-8')
        self.assertEqual('DIFFERENT_OR_INCOMPLETE',self.compare()['status'])

    def test_a_single_transparent_rgb_delta_fails(self):
        self.make_run("right", pixels=b"\1\0\0\0")
        result = self.compare()
        self.assertEqual("DIFFERENT_OR_INCOMPLETE", result["status"])
        self.assertEqual(1, result["cases"][0]["rgba"]["changedPixels"])

    def test_metric_delta_fails_with_identical_images(self):
        self.make_run("right", metric=1.00000000001)
        self.assertEqual("DIFFERENT_OR_INCOMPLETE", self.compare()["status"])

    def test_cpu_does_not_pass_as_default_gpu(self):
        self.make_run("right", renderer="CPU")
        self.assertEqual("DIFFERENT_OR_INCOMPLETE", self.compare()["status"])

    def test_missing_cases_fail(self):
        path = self.right / "run.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["cases"] = []
        path.write_text(json.dumps(report), encoding="utf-8")
        self.assertEqual("DIFFERENT_OR_INCOMPLETE", self.compare()["status"])

    def test_font_file_change_fails_even_with_same_family_names(self):
        path = self.right / "run.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["environment"]["fontResourcesSha256"] = "changed-font-bytes"
        path.write_text(json.dumps(report), encoding="utf-8")
        self.assertEqual("DIFFERENT_OR_INCOMPLETE", self.compare()["status"])

    def test_tampered_environment_artifact_is_rejected(self):
        path = self.right / "run.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["environment"]["manifest"] = {"path": "environment.json", "bytes": 2,
                                                "sha256": hashlib.sha256(b"{}").hexdigest()}
        (self.right / "environment.json").write_bytes(b"tampered")
        path.write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "integrity mismatch"):
            self.compare()


if __name__ == "__main__":
    unittest.main()
