"""Three owner decisions and immediate practice, using original fixtures only."""
from pathlib import Path
import shutil
from urllib.parse import unquote
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:8092'


def login(page,user):
    page.goto(BASE+'/wp-login.php',wait_until='networkidle');page.locator('#user_login').fill(user);page.locator('#user_pass').fill('cafcc-disposable-only');page.locator('#wp-submit').click();page.wait_for_load_state('networkidle')


with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,**({'executable_path':shutil.which('chromium')} if shutil.which('chromium') else {}),args=['--no-sandbox','--disable-dev-shm-usage'])
    admin=browser.new_page(viewport={'width':1024,'height':1366});admin.on('dialog',lambda d:d.accept());login(admin,'test_admin');admin.goto(BASE+'/wp-admin/admin.php?page=cafcc-studio',wait_until='networkidle')
    admin.locator('#studio-search').fill('TEST-V05-OWNER');expect(admin.locator('#studio-rows tr')).to_have_count(1);admin.locator('#studio-rows tr td button').first.click()
    expect(admin.get_by_role('textbox',name='Correct full question',exact=True)).to_contain_text('₹120');expect(admin.get_by_role('textbox',name='Correct full answer',exact=True)).to_contain_text('₹40')
    expect(admin.locator('.studio-owner-decisions button')).to_have_count(3);expect(admin.locator('[data-owner-action=publish]')).to_have_text('Publish')
    admin.screenshot(path=str(ROOT/'docs/previews/v05-owner-review-ipad.png'),full_page=True)
    admin.locator('[data-owner-action=publish]').click();expect(admin.locator('#studio-detail small')).to_contain_text('approved')
    if __import__('os').getenv('CAFCC_ADMIN_ONLY')=='1': browser.close();print('PASS v05 owner/admin browser regression');raise SystemExit(0)
    student=browser.new_page(viewport={'width':390,'height':844});calls=[];student.on('request',lambda r:calls.append(r.url) if '/answers/' in unquote(r.url) else None);login(student,'student_a');student.goto(BASE+'/?cafcc_view=explorer',wait_until='networkidle')
    student.locator('[data-filter=search]').fill('TEST-V05-OWNER');student.locator('[data-filter=search]').press('Enter');student.wait_for_function("document.querySelector('.cc-question')?.innerText.includes('₹120')")
    card=student.locator('.cc-question');expect(card).to_have_count(1);assert not calls;assert '₹40 per period' not in card.inner_text()
    card.get_by_role('button',name='Show Answer',exact=True).click();expect(card.locator('.cc-answer-panel')).to_contain_text('₹40 per period');assert len(calls)==1
    student.screenshot(path=str(ROOT/'docs/previews/v05-original-solution-phone.png'),full_page=True);card.get_by_role('button',name='Hide Answer',exact=True).click();expect(card.locator('.cc-answer-panel')).to_be_empty()
    student.goto(BASE+'/?cafcc_view=mcq',wait_until='networkidle');expect(student.locator('[data-mcq]')).to_be_visible();assert not student.locator('.cc-question').count()
    admin.goto(BASE+'/wp-admin/admin.php?page=cafcc-rights',wait_until='networkidle');admin.get_by_role('button',name='New permission',exact=True).click();expect(admin.locator('#rights-form')).to_contain_text('Permission reference (optional for physical attestation)');admin.screenshot(path=str(ROOT/'docs/previews/v05-private-rights-ipad.png'),full_page=True)
    browser.close()
print('V0.5 original-fixture browser passed: full question/answer owner preview, three decisions, immediate publication, no answer prefetch, deliberate Show/Hide Answer, private rights interface and a separate MCQ destination.')
