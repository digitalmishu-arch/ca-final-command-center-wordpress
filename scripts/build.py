#!/usr/bin/env python3
"""Build a reproducible, installable plugin ZIP. Python is only a packaging tool."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import argparse
import hashlib

parser = argparse.ArgumentParser()
parser.add_argument('--output', default='dist/ca-final-command-center.zip')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
plugin = root / 'ca-final-command-center'
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for source in sorted(plugin.rglob('*')):
        if source.is_file():
            entry = ZipInfo(source.relative_to(root).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, source.read_bytes())
with ZipFile(output) as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    assert 'ca-final-command-center/ca-final-command-center.php' in names
    assert all(n.startswith('ca-final-command-center/') and '..' not in n.split('/') for n in names)
print(f'{output}: {len(names)} files; SHA-256 {hashlib.sha256(output.read_bytes()).hexdigest()}')
