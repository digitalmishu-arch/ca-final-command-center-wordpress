#!/usr/bin/env python3
"""Public CODE artifact only. Actual research outputs are never CI artifacts."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
root=Path(__file__).resolve().parents[1]
paths=[p for p in (root/'research').iterdir() if p.is_file() and p.suffix in {'.py','.html','.json','.txt'}]
paths+=[root/'docs/RESEARCH-ACCURACY.md',root/'docs/RESEARCH-V04.md']
out=root/'dist/research-tools-v04.zip';out.parent.mkdir(exist_ok=True)
with ZipFile(out,'w',ZIP_DEFLATED) as z:
    for p in sorted(paths):z.write(p,p.relative_to(root))
with ZipFile(out) as z:
    assert z.testzip() is None
    assert all(not p.endswith('.pdf') and not p.startswith('work/') for p in z.namelist())
print('Public research code artifact created; no private outputs or PDFs included.')
