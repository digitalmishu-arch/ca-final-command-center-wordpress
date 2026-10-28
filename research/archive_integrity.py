"""Conservative layout holds beyond numeric-token equality.

Keep extracted evidence. Never invent an equation or repair a monetary value
from these diagnostics. A token inventory does not prove cell association.
"""
import re
import unicodedata


def inspect(rich):
    issues = []
    for i, block in enumerate(rich.get('blocks', [])):
        if block.get('type') != 'table':
            continue
        cells = block['cells']
        def add(code):
            issues.append(dict(code=code, page=block['page'], bbox=block['bbox'], table_index=i))
        if any(any(unicodedata.category(ch) in ('Cc', 'Co', 'Cn') and ch not in '\n\r\t' or ch == '\ufffd' for ch in c['text']) for c in cells):
            add('unsupported_pdf_formula_or_font_glyph')
        for cell in cells:
            if cell['column'] == 0 and re.search(r'\s[-−–—]\s*$', cell['text']) and any(c['row'] == cell['row'] and c['column'] > 0 and not c['text'].strip() for c in cells):
                add('amount_placeholder_column_assignment_requires_review')
                break
        for cell in cells:
            if cell['column'] > 0 and len([s for s in cell['text'].splitlines() if re.search(r'\d', s)]) >= 3 and not block.get('row_method'):
                add('multi_amount_cell_row_associations_require_review')
                break
    return issues


def hold(row):
    """Add holds without changing source text, permanent identity or approval."""
    record = row['import_record']
    diagnostics = []
    for kind in ('question', 'answer'):
        rich = row.get(kind)
        if not rich:
            continue
        issues = inspect(rich)
        if not issues:
            continue
        checks = record['rich_content'][kind]['checks']
        checks['numeric_token_passed'] = checks.get('numeric_token_passed', checks.get('passed', False))
        checks['passed'] = False
        checks['structural_conflicts'] = issues
        for issue in issues:
            code = ('question_integrity_failed_' if kind == 'question' else 'answer_formatting_conflict_') + issue['code'] + '_page_' + str(issue['page'])
            if code not in record['blocking_exceptions']:
                record['blocking_exceptions'].append(code)
            diagnostics.append(dict(stable_id=record['stable_id'], kind=kind, **issue))
    return diagnostics
