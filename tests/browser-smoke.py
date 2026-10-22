from pathlib import Path
from playwright.sync_api import sync_playwright
import json, uuid
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    context=browser.new_context(viewport={'width':1180,'height':900},device_scale_factor=1)
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:8092/wp-login.php',wait_until='networkidle')
    page.locator('#user_login').fill('student_a')
    page.locator('#user_pass').fill('cafcc-disposable-only')
    page.locator('#wp-submit').click()
    page.wait_for_load_state('networkidle')
    page.goto('http://127.0.0.1:8092/?page_id=4',wait_until='networkidle')
    page.wait_for_function("document.querySelector('[data-cafcc-explorer]') && !document.querySelector('[data-cafcc-explorer]').hasAttribute('aria-busy')")
    print('initial:',page.locator('.cc-feedback').inner_text())
    print('subjects:',page.locator('[data-filter=subject_id] option').all_text_contents())
    page.locator('[data-filter=subject_id]').select_option(label='FR — Financial Reporting')
    page.wait_for_load_state('networkidle')
    page.wait_for_function("document.querySelectorAll('[data-filter=chapter_id] option').length>1")
    chapter=page.locator('[data-filter=chapter_id] option').evaluate_all("options=>options.find(n=>n.textContent.startsWith('Chapter 11:')).value")
    page.locator('[data-filter=chapter_id]').select_option(chapter)
    page.wait_for_load_state('networkidle')
    page.wait_for_function("document.querySelectorAll('[data-filter=unit_id] option').length===8")
    unit=page.locator('[data-filter=unit_id] option').evaluate_all("options=>options.find(n=>n.textContent.includes('Unit 4')).value")
    page.locator('[data-filter=unit_id]').select_option(unit)
    page.wait_for_load_state('networkidle')
    page.wait_for_function("!document.querySelector('[data-cafcc-explorer]').hasAttribute('aria-busy')")
    assert page.locator('.cc-question-list').inner_text().find('No verified, published questions')>=0
    assert page.locator('[data-filter=unit_id] option').count()==8
    assert page.locator('[data-filter=topic_id] option').count()>=3
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    page.screenshot(path='docs/previews/ipad-explorer.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path='docs/previews/phone-explorer.png',full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    page.locator('[data-filter=subject_id]').select_option(label='AFM — Advanced Financial Management')
    page.wait_for_load_state('networkidle')
    page.wait_for_function("document.querySelectorAll('[data-filter=chapter_id] option').length===16")
    assert page.locator('[data-filter=unit_id]').input_value()==''
    assert page.locator('[data-filter=topic_id]').input_value()==''
    assert not errors,errors
    print(json.dumps({'browser':'Chromium','checks':['real WordPress login','FR dependent chapter/unit/topic options','empty verified-question state','iPad/phone no horizontal overflow','subject change clears descendants','no JavaScript page errors'],'errors':errors}))
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
    # Exercise a synthetic test question through the real student UI. It is never packaged.
    manager.evaluate("""async()=>{const cfg=CAFCCManager;const r=await fetch(cfg.url+'admin/questions',{headers:{'X-WP-Nonce':cfg.nonce}});const data=await r.json();const q=data.items.find(n=>n.stable_key==='TEST-QUESTION-001');const result=await fetch(cfg.url+'admin/questions/'+q.id,{method:'PATCH',headers:{'X-WP-Nonce':cfg.nonce,'Content-Type':'application/json'},body:JSON.stringify({review_status:'verified',publication_status:'published'})});if(!result.ok)throw new Error(await result.text());}""")
    page.goto('http://127.0.0.1:8092/?page_id=4',wait_until='networkidle')
    page.wait_for_function("document.querySelectorAll('.cc-question').length===1")
    assert 'TEST ONLY connected question' in page.locator('.cc-question').inner_text()
    page.get_by_role('button',name='Show Answer',exact=True).click()
    page.wait_for_function("document.querySelector('.cc-answer-panel').textContent.includes('independently authored solution')")
    assert page.get_by_role('link',name='View Official Answer',exact=True).count()==1
    assert 'PRIVATE DRAFT ANSWER' not in page.locator('.cc-answer-panel').inner_text()
    page.locator('.cc-card-actions select').select_option('needs_revision')
    page.wait_for_function("document.querySelector('.cc-feedback').textContent.includes('saved')")
    page.reload(wait_until='networkidle')
    page.wait_for_function("document.querySelector('.cc-card-actions select')?.value==='needs_revision'")
    assert not errors,errors
    print(json.dumps({'admin_and_student_checks':['real admin login and manager rendering','CSV file preview and commit through UI','reviewed question rendering','authored solution and official answer link','draft answer hidden','practice status persists after reload'],'errors':errors}))
    admin_context.close()
    context.close()
    browser.close()
