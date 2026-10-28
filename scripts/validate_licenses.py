"""Verify pinned third-party license bytes for the supported Windows/Linux build trees."""
import hashlib
import json
from pathlib import Path


def validate(root):
    """Read the source inventory; raise ValueError for missing/changed required texts.

    Takes a repository Path, returns counts, does not load native code, fonts or
    network resources. No units or thread ownership requirements; read-only.
    Sources: Cargo.lock and the pinned native source/license inventory.
    """
    data = json.loads((root / 'third_party/license-inventory.json').read_text(encoding='utf-8'))
    if data['unresolvedRequiredLicenseText']:
        raise ValueError('Missing license text for supported build target')
    count = 0
    def walk(value):
        nonlocal count
        if isinstance(value, dict):
            if 'path' in value and 'sha256' in value and value['path'].startswith('third_party/'):
                path = (root / value['path']).resolve()
                if not path.is_relative_to((root / 'third_party').resolve()):
                    raise ValueError('License path outside third_party')
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != value['sha256'] or len(raw) != value['bytes']:
                    raise ValueError('License fingerprint changed: ' + value['path'])
                count += 1
            for item in value.values(): walk(item)
        elif isinstance(value, list):
            for item in value: walk(item)
    walk(data)
    return dict(status='LICENSE_SOURCE_BYTES_VERIFIED',files=count,targets=data['requiredTargets'],
                unbuiltTargetMissing=len(data['missingCargoLicenseText']))


if __name__ == '__main__':
    print(json.dumps(validate(Path(__file__).resolve().parents[1])))
