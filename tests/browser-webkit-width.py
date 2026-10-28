"""Owned disposable WordPress only: investigate WebKit's root-vs-element width."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.webkit.launch();page=b.new_page(viewport={'width':1180,'height':820},has_touch=True,reduced_motion='reduce')
 page.goto('http://127.0.0.1:8092/wp-login.php',wait_until='networkidle');page.locator('#user_login').fill('student_a');page.locator('#user_pass').fill('cafcc-disposable-only');page.locator('#wp-submit').click();page.wait_for_load_state('networkidle')
 page.goto('http://127.0.0.1:8092/?cafcc_view=mcq',wait_until='networkidle');page.locator('[data-mcq-list] button').first.click();page.locator('[name=mcq-option][value=B]').check();page.get_by_role('button',name='Check Answer',exact=True).click();page.wait_for_function("document.querySelector('[data-mcq-feedback]').textContent.length>0")
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300)
 def dimensions():return page.evaluate('''()=>{const box=n=>{const r=n.getBoundingClientRect(),s=getComputedStyle(n);return {tag:n.tagName,cls:n.className,id:n.id,left:r.left,right:r.right,width:r.width,scroll:n.scrollWidth,client:n.clientWidth,overflow:s.overflow,position:s.position,padding:s.padding,margin:s.margin,min:s.minWidth,display:s.display,text:n.textContent.slice(0,65)}};return {viewport:innerWidth,scrollX,visual:visualViewport.width,root:box(document.documentElement),body:box(document.body),portal:box(document.querySelector('.cc-portal')),overflow:[...document.querySelectorAll('*')].filter(n=>{const r=n.getBoundingClientRect();return r.width&&(r.right+scrollX>innerWidth+1||r.left+scrollX<0||n.scrollWidth>n.clientWidth+2)}).map(box).slice(0,50)}}''')
 report={'original':dimensions()};page.screenshot(path=str(ROOT/'docs/previews/v07-webkit-width-original.png'),full_page=True)
 for name,script in [('zero_scroll','scrollTo(0,scrollY)'),('body_flow_root',"document.body.style.display='flow-root'"),('body_width',"document.body.style.width='100%'"),('portal_layout',"document.querySelector('.cc-portal').style.contain='layout'")]:
  page.evaluate(script);page.wait_for_timeout(150);report[name]=dimensions()
 page.reload(wait_until='networkidle');report['fresh_phone']=dimensions();print(json.dumps(report));b.close()
