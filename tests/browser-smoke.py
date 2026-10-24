from pathlib import Path
from playwright.sync_api import sync_playwright
import json, uuid
import shutil
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,**({'executable_path':shutil.which('chromium')} if shutil.which('chromium') else {}),args=['--no-sandbox','--disable-dev-shm-usage'])
    context=browser.new_context(viewport={'width':1180,'height':900},device_scale_factor=1)
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:8092/wp-login.php',wait_until='networkidle')
    page.locator('#user_login').fill('student_a')
    page.locator('#user_pass').fill('cafcc-disposable-only')
    page.locator('#wp-submit').click()
    page.wait_for_load_state('networkidle')
    page.goto('http://127.0.0.1:8092/?cafcc_view=explorer',wait_until='networkidle')
    page.wait_for_function("document.querySelector('[data-cafcc-explorer]') && !document.querySelector('[data-cafcc-explorer]').hasAttribute('aria-busy')")
    assert page.locator('[data-filter=subject_id] option').count()==7
    assert page.locator('[data-filter=topic_id]').is_enabled()
    assert page.locator('.cc-question').count()==0
    assert 'No verified, published questions' in page.locator('.cc-question-list').inner_text()
    page.locator('.cc-concept-input').fill('Embedded Derivatives')
    page.wait_for_function("document.querySelector('#cc-concept-results').textContent.includes('No reviewed questions')")
    assert not page.locator('#cc-concept-results button').count()
    for width in [390,768,1180]:
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    page.screenshot(path='docs/previews/v04-empty-ipad.png',full_page=True)
    assert not errors,errors
    print('Browser: honest empty states, no unavailable concept suggestions, usable independent selectors and responsive layout passed.')
    admin_context=browser.new_context(viewport={'width':1180,'height':900})
    manager=admin_context.new_page()
    manager.on('pageerror',lambda error:errors.append(str(error)))
    manager.goto('http://127.0.0.1:8092/wp-login.php',wait_until='networkidle')
    manager.locator('#user_login').fill('test_admin');manager.locator('#user_pass').fill('cafcc-disposable-only');manager.locator('#wp-submit').click();manager.wait_for_load_state('networkidle')
    manager.goto('http://127.0.0.1:8092/wp-admin/admin.php?page=cafcc-connected',wait_until='networkidle')
    manager.wait_for_function("document.querySelector('.cc-admin-feedback').textContent.includes('Catalogue loaded')")
    assert manager.locator('#cc-kind option').count()==11
    manager.locator('#cc-kind').select_option('taxonomy')
    manager.locator('[data-panel=imports]').click()
    manager.locator('#cc-import-type').select_option('hierarchy')
    browser_key='TEST-BROWSER-'+uuid.uuid4().hex[:12]
    csv='edition_key,subject_code,node_key,parent_key,node_type,title,position,heading_origin,source_url,source_location\r\nfr-may2026,FR,TEST-BROWSER-SUB,fr-may2026-m4-ch11-u4-derivative-contracts,subtopic,TEST ONLY browser import,900,editorial,,\r\n'
    manager.locator('#cc-csv').set_input_files({'name':'test-hierarchy.csv','mimeType':'text/csv','buffer':csv.replace('TEST-BROWSER-SUB',browser_key).encode()})
    manager.locator('#cc-preview').click()
    manager.wait_for_function("!document.querySelector('#cc-commit').disabled")
    assert 'rows validated' in manager.locator('#cc-import-preview').inner_text()
    manager.locator('#cc-commit').click()
    manager.wait_for_function("document.querySelector('.cc-admin-feedback').textContent.includes('imported')")
    assert 'Review records before publication' in manager.locator('.cc-admin-feedback').inner_text()
    # An old manager publication flag cannot bypass the new review gates.
    manager.evaluate("""async()=>{const cfg=CAFCCManager;const r=await fetch(cfg.url+'admin/questions',{headers:{'X-WP-Nonce':cfg.nonce}});const data=await r.json();const q=data.items.find(n=>n.stable_key==='TEST-QUESTION-001');const result=await fetch(cfg.url+'admin/questions/'+q.id,{method:'PATCH',headers:{'X-WP-Nonce':cfg.nonce,'Content-Type':'application/json'},body:JSON.stringify({review_status:'verified',publication_status:'published'})});if(!result.ok)throw new Error(await result.text());}""")
    page.goto('http://127.0.0.1:8092/?cafcc_view=explorer',wait_until='networkidle')
    page.wait_for_function("document.querySelector('[data-cafcc-explorer]') && !document.querySelector('[data-cafcc-explorer]').hasAttribute('aria-busy')")
    assert page.locator('.cc-question').count()==0
    assert not errors,errors
    print('Browser: actual CSV preview/commit retained; old manager cannot bypass separate Studio approvals.')
    admin_context.close()
    context.close()
    browser.close()
