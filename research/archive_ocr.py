"""Private resumable OCR evidence for image PDFs, separate from importable text.

OCR is not independent transcription verification. Original hashes/page geometry
are retained. No OCR figures or tables become publication-eligible automatically.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import json
import fitz
import archive_catalog as catalog
TESSDATA='/usr/share/tesseract-ocr/5/tessdata'
def process(source,output):
 out=Path(output)/source['source_hash'];out.mkdir(parents=True,exist_ok=True);original=Path(source['local_path']);assert catalog.sha(original.read_bytes())==source['source_hash'];pages=[];combined=fitz.open()
 with fitz.open(original)as doc:
  for n,page in enumerate(doc):
   path=out/('page-'+str(n+1).zfill(4)+'.pdf');meta=path.with_suffix('.json')
   if not(path.exists()and meta.exists()):
    pix=page.get_pixmap(dpi=180,alpha=False);raw=pix.pdfocr_tobytes(language='eng',tessdata=TESSDATA);ocr=fitz.open(stream=raw,filetype='pdf');aligned=fitz.open();target=aligned.new_page(width=page.rect.width,height=page.rect.height);target.show_pdf_page(target.rect,ocr,0);aligned.save(path);text=aligned[0].get_text();catalog.write(meta,dict(page=n+1,text=text,original_page_rect=list(page.rect),ocr_engine='Tesseract via PyMuPDF at 180 dpi',confidence='Not exposed by this OCR API; manual comparison required',publication_eligible=False,warning='Numbers, signs, tables, boundaries and answer identity are unverified OCR candidates.'))
   with fitz.open(path)as one:combined.insert_pdf(one)
   pages.append(json.loads(meta.read_text()))
  result=out/'ocr-review-only.pdf'
  if not result.exists():combined.save(result,garbage=4,deflate=True)
 return dict(file_id=source['file_id'],filename=source['filename'],collection_subject=source['collection_subject'],source_hash=source['source_hash'],original_pages=source['page_count'],ocr_pages=len(pages),ocr_pdf_path=str(result),ocr_pdf_sha256=catalog.sha(result.read_bytes()),page_metadata=[str((out/('page-'+str(n+1).zfill(4)+'.json')))for n in range(len(pages))],status='ocr_evidence_prepared_manual_verification_required',automatic_import=False)
def run(manifest,output):
 out=catalog.private(output);out.mkdir(parents=True,exist_ok=True);sources=[r for r in json.loads(Path(manifest).read_text())['records']if len(r['scanned_or_empty_pages'])>=r['page_count']*.8];results=[]
 with ProcessPoolExecutor(max_workers=2)as pool:
  for f in as_completed([pool.submit(process,r,out)for r in sources]):
   try:r=f.result()
   except Exception as e:r=dict(status='ocr_failed',error=str(e))
   results.append(r);catalog.write(out/'ocr-manifest.json',dict(records=results,pending=len(sources)-len(results),note='Review evidence only; OCR is not a publishable transcription.'));print(json.dumps({k:v for k,v in r.items()if k not in('page_metadata',)}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--output',required=True);a=p.parse_args();run(a.manifest,a.output)
