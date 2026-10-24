#!/usr/bin/env python3
"""Private navigation/ledger-load smoke test; never records owner approvals."""
import argparse,json
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright,expect
p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('sources');a=p.parse_args()
root=Path(a.package).resolve();sources=Path(a.sources).resolve();private=Path(__file__).resolve().parents[1]/'work'
assert private in root.parents and private in sources.parents
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root)));Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as runtime:
  browser=runtime.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1024,'height':1366});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:'+str(server.server_port)+'/review.html')
  rows=json.loads((root/'review.json').read_text());index=next(i for i,q in enumerate(rows) if q['subject']=='FR' and q['reference']=='11' and not q['subreference'])
  page.locator('#question').select_option(str(index));expect(page.locator('#evidence')).to_contain_text('Ind AS 102')
  page.locator('#pdf').set_input_files(sources/'FR.pdf');expect(page.locator('#file-status')).to_contain_text('Exact source hash verified')
  page.locator('#start').click();assert page.locator('#viewer').get_attribute('src').endswith('#page=4')
  page.locator('#ledger').set_input_files(root/'corrections-ledger.json');expect(page.locator('#status')).to_contain_text('Ledger loaded and hash history verified')
  with page.expect_download() as d:page.locator('#download').click()
  assert d.value.suggested_filename.startswith('corrections-ledger-')
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('() => document.documentElement.scrollWidth<=window.innerWidth');assert not errors,errors
  browser.close()
 print('Layout reviewer browser passed: heading/boundaries, exact PDF hash, ledger history load/download, phone width. No owner approval created.')
finally:server.shutdown();server.server_close()
