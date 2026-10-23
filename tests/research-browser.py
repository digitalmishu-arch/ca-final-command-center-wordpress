#!/usr/bin/env python3
"""Optional private browser check; never uploads source files or screenshots.
Usage: python tests/research-browser.py work/research/run-final work/research/sources
Requires Playwright and local Chromium; no hosting or public CI input.
"""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright, expect

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('package');parser.add_argument('sources')
args=parser.parse_args();package=Path(args.package).resolve();sources=Path(args.sources).resolve()
private=(Path(__file__).resolve().parents[1]/'work').resolve()
assert private in package.parents and private in sources.parents
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(package)))
Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1024,'height':1366});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:'+str(server.server_port)+'/review.html')
        assert page.locator('#question option').count()==121
        expect(page.locator('#title')).to_contain_text('FR')
        page.locator('#pdf').set_input_files(sources/'FR.pdf')
        expect(page.locator('#file-status')).to_contain_text('SHA-256 matches')
        assert page.locator('#viewer').get_attribute('src').endswith('#page=2')
        page.get_by_text('Suggested-answer page',exact=True).click()
        assert page.locator('#viewer').get_attribute('src').endswith('#page=12')
        page.locator('#decision').select_option('location_checked')
        page.locator('#note').fill('TEST ONLY private review');page.locator('#save').click()
        with page.expect_download() as d:
            page.locator('#export').click()
        assert d.value.suggested_filename=='private-review-decisions.csv'
        page.locator('#pdf').set_input_files(sources/'IDT.pdf')
        expect(page.locator('#file-status')).to_contain_text('mismatch')
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('() => document.documentElement.scrollWidth<=window.innerWidth')
        assert not errors,errors
        browser.close()
    print('Private browser checks passed: 121 options, PDF hash match/mismatch, question/answer navigation, review download, mobile width, no JavaScript errors')
finally:
    server.shutdown();server.server_close()
