"""Real local WordPress UI, using authored synthetic fixtures only."""
from pathlib import Path
import re
import shutil
from urllib.parse import unquote
from playwright.sync_api import sync_playwright,expect

BASE='http://127.0.0.1:8092'
ROOT=Path(__file__).resolve().parents[1]


def login(page,user):
    page.goto(BASE+'/wp-login.php',wait_until='networkidle')
    page.locator('#user_login').fill(user);page.locator('#user_pass').fill('cafcc-disposable-only')
    page.locator('#wp-submit').click();page.wait_for_load_state('networkidle')


def ready(page):
    page.wait_for_function("() => document.querySelector('[data-cafcc-explorer]') && !document.querySelector('[data-cafcc-explorer]').hasAttribute('aria-busy')")


def select_fr(page):
    page.goto(BASE+'/?page_id=4',wait_until='networkidle');ready(page)
    page.locator('[data-filter=subject_id]').select_option(label='FR — Financial Reporting');ready(page)
    page.wait_for_function("() => document.querySelectorAll('[data-filter=chapter_id] option').length>1")
    chapter=page.locator('[data-filter=chapter_id] option').evaluate_all("opts=>opts.find(o=>o.textContent.startsWith('Chapter 5:')).value")
    page.locator('[data-filter=chapter_id]').select_option(chapter);ready(page)
    page.wait_for_function("() => document.querySelectorAll('[data-filter=unit_id] option').length>1")
    unit=page.locator('[data-filter=unit_id] option').evaluate_all("opts=>opts.find(o=>o.textContent.includes('Ind AS 16')).value")
    page.locator('[data-filter=unit_id]').select_option(unit);ready(page)
    page.locator('[data-filter=topic_id]').select_option(label='Straight-line depreciation — authored demo · Editorial tag');ready(page)
    page.locator('[data-filter=subtopic_id]').select_option(label='Calculate the stated example · Editorial tag');ready(page)
    expect(page.locator('.cc-question')).to_have_count(1)
    return page.locator('.cc-question')


with sync_playwright() as runtime:
    browser=runtime.chromium.launch(**({'executable_path':shutil.which('chromium')} if shutil.which('chromium') else {}),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
    context=browser.new_context(viewport={'width':1024,'height':1366});page=context.new_page();errors=[];answer_requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:answer_requests.append(r.url) if '/answers/' in unquote(r.url) else None)
    login(page,'student_a');card=select_fr(page)
    expect(card.locator('.cc-rich-content table')).to_have_count(1)
    assert not card.locator('.cc-answer-panel').is_visible();assert 'Work through the calculation' not in page.locator('body').inner_text();assert not answer_requests
    qid=card.get_attribute('data-question-id')
    preview=ROOT/'docs/previews';preview.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(preview/'v03-ipad-practice.png'),full_page=True)
    card.get_by_role('button',name='Show Answer',exact=True).focus();page.keyboard.press('Enter')
    expect(card.locator('.cc-answer-panel')).to_contain_text('Work through the calculation')
    expect(card.locator('.cc-answer-panel math')).to_have_count(1);assert len(answer_requests)==1
    page.screenshot(path=str(preview/'v03-ipad-answer.png'),full_page=True)
    card.get_by_role('button',name='Hide Answer',exact=True).click();assert not card.locator('.cc-answer-panel').inner_text()
    card.get_by_role('button',name='☆ Bookmark',exact=True).click();expect(card.locator('.cc-bookmark')).to_have_attribute('aria-pressed','true')
    card.locator('.cc-private-notes summary').click();card.locator('.cc-private-notes textarea').fill('PRIVATE NOTE A · authored preview');card.get_by_role('button',name='Save my note',exact=True).click();expect(page.locator('.cc-feedback')).to_contain_text('private note is saved')
    card.locator('.cc-card-actions select').select_option('needs_revision');expect(page.locator('.cc-feedback')).to_contain_text('progress is saved')
    page.reload(wait_until='networkidle');ready(page)
    # Filters are intentionally session-only; select the dependent path again.
    card=select_fr(page);expect(card.locator('.cc-bookmark')).to_have_attribute('aria-pressed','true');expect(card.locator('.cc-card-actions select')).to_have_value('needs_revision');expect(card.locator('.cc-private-notes textarea')).to_have_value('PRIVATE NOTE A · authored preview')
    for width in [375,390,768,1024,1440]:
        page.set_viewport_size({'width':width,'height':900});assert page.evaluate('() => document.documentElement.scrollWidth<=window.innerWidth'),width
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(preview/'v03-phone-practice.png'),full_page=True)
    # A separate login receives no A note/bookmark/completion.
    bcontext=browser.new_context(viewport={'width':1024,'height':900},reduced_motion='reduce');b=bcontext.new_page();login(b,'student_b');bcard=select_fr(b)
    expect(bcard.locator('.cc-bookmark')).to_have_attribute('aria-pressed','false');expect(bcard.locator('.cc-private-notes textarea')).to_have_value('');expect(bcard.locator('.cc-card-actions select')).to_have_value('not_started')
    bcard.locator('.cc-card-actions select').select_option('attempted');expect(b.locator('.cc-feedback')).to_contain_text('progress is saved')
    bcard.get_by_role('button',name='Show Answer',exact=True).click();expect(bcard.locator('.cc-answer-panel')).to_contain_text('Work through the calculation');assert bcard.locator('.cc-answer-panel').evaluate("e=>getComputedStyle(e).animationName")=='none'
    b.locator('[data-filter=bookmarked]').check();ready(b);expect(b.locator('.cc-question')).to_have_count(0)
    # Rich editor + explicit rights review: save withdraws text, approval restores it.
    admin_context=browser.new_context();admin=admin_context.new_page();login(admin,'test_admin');admin.goto(BASE+'/wp-admin/admin.php?page=cafcc-practice',wait_until='networkidle')
    admin.get_by_role('button',name=re.compile(r'^#\d+ · Q'+qid+r' · question')).click()
    admin.wait_for_function("() => window.tinymce && tinymce.get('pc_body_html') && tinymce.get('pc_body_html').initialized")
    admin.evaluate("() => tinymce.get('pc_body_html').insertContent('<p>Browser-authored test sentence.</p>')")
    admin.get_by_role('button',name='Save as Draft / Needs Review',exact=True).click();expect(admin.locator('#pc-feedback')).to_contain_text('Draft saved')
    page.reload(wait_until='networkidle');ready(page);card=select_fr(page);expect(card.locator('.cc-reference-note')).to_have_count(1);expect(card.locator('.cc-question-content')).to_have_count(0)
    admin.locator('#pc-confirm').check();admin.get_by_role('button',name='Approve this revision',exact=True).click();expect(admin.locator('#pc-feedback')).to_contain_text('Revision approved')
    page.reload(wait_until='networkidle');ready(page);card=select_fr(page);expect(card.locator('.cc-question-content')).to_contain_text('Browser-authored test sentence.');expect(card.locator('.cc-card-actions select')).to_have_value('needs_revision')
    assert not errors,errors
    admin_context.close();bcontext.close();context.close();browser.close()
print('Practice browser passed: dependent path, full text/table/MathML, no answer prefetch, keyboard Show Answer, bookmark/note/progress persistence, two-student isolation, rich-editor draft/approval, mobile/iPad widths and reduced motion.')
