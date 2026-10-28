"""Guard the read-only source boundary and non-overwriting development staging."""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.prepare_node_baseline import prepare
from scripts.refresh_reference_index import SNAPSHOT


class NodeStagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        snapshot = self.root / SNAPSHOT.relative_to(ROOT)
        shutil.copytree(SNAPSHOT, snapshot)
        shutil.copyfile(ROOT / "references/source-manifest.json", self.root / "references/source-manifest.json")

    def test_staging_preserves_every_byte_and_refuses_existing_evidence(self):
        destination = self.root / ".local/baseline"
        report = prepare(destination, self.root)
        self.assertEqual(49, len(report["files"]))
        for entry in report["files"]:
            self.assertEqual((self.root / entry["source"]).read_bytes(), (destination / entry["destination"]).read_bytes())
        with self.assertRaises(FileExistsError):
            prepare(destination, self.root)

    def test_modified_reference_is_rejected_before_staging(self):
        source = self.root / SNAPSHOT.relative_to(ROOT) / "src/lib.rs"
        source.write_bytes(source.read_bytes() + b"\n// altered\n")
        destination = self.root / ".local/baseline"
        with self.assertRaisesRegex(ValueError, "fingerprints changed"):
            prepare(destination, self.root)
        self.assertFalse(destination.exists())

    def test_nonlocal_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "strictly below"):
            prepare(self.root / "crates/canvas-core", self.root)


if __name__ == "__main__":
    unittest.main()
