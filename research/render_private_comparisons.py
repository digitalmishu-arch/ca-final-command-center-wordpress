"""Render private comparison HTML on a temporary loopback-only worker server.

Never invoked by public CI; outputs remain beside the private source evidence.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import shutil
import threading
from playwright.sync_api import sync_playwright


def render(root):
    root=Path(root).resolve();output=root/'private-visual-previews';output.mkdir(exist_ok=True)
    class PrivateHandler(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
        def end_headers(self):self.send_header('Cache-Control','private, no-store');super().end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(PrivateHandler,directory=str(root)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,**({'executable_path':shutil.which('chromium')} if shutil.which('chromium') else {}),args=['--no-sandbox','--disable-dev-shm-usage'])
            page=browser.new_page(viewport={'width':1440,'height':1000})
            for file in sorted((root/'table-comparisons').glob('*.html')):
                page.goto('http://127.0.0.1:'+str(server.server_port)+'/table-comparisons/'+file.name,wait_until='networkidle')
                page.evaluate('document.fonts.ready');page.wait_for_timeout(120)
                page.screenshot(path=str(output/(file.stem+'.png')),full_page=True)
            browser.close()
    finally:server.shutdown();server.server_close()
    print('Private comparison screenshots:',len(list(output.glob('*.png'))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('private_package_directory');render(p.parse_args().private_package_directory)
