"""Original fixtures in disposable WordPress: native WebKit selects must not widen the page."""
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.webkit.launch();page=b.new_page(viewport={'width':1180,'height':820},has_touch=True,reduced_motion='reduce')
 page.goto('http://127.0.0.1:8092/wp-login.php',wait_until='networkidle');page.locator('#user_login').fill('student_a');page.locator('#user_pass').fill('cafcc-disposable-only');page.locator('#wp-submit').click();page.wait_for_load_state('networkidle')
 page.goto('http://127.0.0.1:8092/?cafcc_view=mcq',wait_until='networkidle');page.locator('[data-mcq-list] button').first.click();page.locator('[name=mcq-option][value=B]').check();page.get_by_role('button',name='Check Answer',exact=True).click();page.wait_for_function("document.querySelector('[data-mcq-feedback]').textContent.length>0")
 for width,height,label in [(390,844,'phone'),(820,1180,'portrait'),(1180,820,'landscape')]:
  page.set_viewport_size({'width':width,'height':height})
  for theme in ['light','dark']:
   if page.locator('.cc-portal').get_attribute('data-cc-theme')!=theme:page.locator('.cc-theme-toggle').click()
   page.wait_for_function('document.documentElement.scrollWidth<=innerWidth')
   sizes=page.locator('.cc-mcq-filters').evaluate('f=>({width:f.clientWidth,scroll:f.scrollWidth,labels:[...f.querySelectorAll("label")].map(n=>({width:n.clientWidth,scroll:n.scrollWidth}))})')
   assert sizes['scroll']<=sizes['width']+1,sizes
   assert all(x['scroll']<=x['width']+1 for x in sizes['labels']),sizes
   page.screenshot(path=str(ROOT/f'docs/previews/v07-webkit-focused-{theme}-{label}.png'),full_page=True,animations='disabled')
 # The same native select still carries the full title and filters actual assigned tags.
 control=page.locator('[name=standard]');expect(control.locator('option[value="Ind AS 105"]')).to_contain_text('Non-current Assets');control.select_option('Ind AS 105');expect(page.locator('[data-mcq-list] .cc-mcq-result')).to_have_count(1)
 page.set_viewport_size({'width':390,'height':844});page.wait_for_function('document.documentElement.scrollWidth<=innerWidth');b.close()
print('PASS focused WebKit native filters: no page/label overflow in both themes and phone/tablet orientations; full option labels and actual standards filtering retained. No physical Safari claim.')
