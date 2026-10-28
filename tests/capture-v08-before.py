"""Exact v0.7 authored baseline; injected failure is not a hosting diagnosis."""
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from urllib.parse import unquote
import shutil
OUT=Path(__file__).resolve().parents[1]/'docs/previews';OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,**({'executable_path':shutil.which('chromium')}if shutil.which('chromium')else{}),args=['--no-sandbox','--disable-dev-shm-usage']);page=b.new_page(viewport={'width':820,'height':1180},has_touch=True);page.goto('http://127.0.0.1:8092/wp-login.php');page.locator('#user_login').fill('student_a');page.locator('#user_pass').fill('cafcc-disposable-only');page.locator('#wp-submit').click();page.wait_for_load_state('networkidle')
 for view in ['explorer','practice','dashboard','mcq']:
  page.goto('http://127.0.0.1:8092/?cafcc_view='+view+('&search=TEST-V07-READER-1'if view=='explorer'else''),wait_until='networkidle');page.screenshot(path=str(OUT/f'v08-before-{view}-ipad.png'),full_page=True,animations='disabled')
 def unavailable(route):
  if '/cafcc/v6/study/' in unquote(route.request.url):route.fulfill(status=503,content_type='text/html',body='<h1>Error establishing a database connection</h1>')
  else:route.continue_()
 page.route('**/*',unavailable);page.goto('http://127.0.0.1:8092/?cafcc_view=explorer&search=TEST-V07-READER-1',wait_until='networkidle');expect(page.locator('.cc-study-feedback')).to_contain_text('Unexpected token');page.screenshot(path=str(OUT/'v08-before-notes-service-error.png'),full_page=True,animations='disabled');b.close()
print('PASS: independently authored v0.7 before screenshots and simulated non-JSON failure captured; no Hostinger/source-derived content.')
