"""Apply explicit private source-region corrections without approving records.

The decision file supplies source-backed table models, never guessed amounts.
No real academic prose or source-derived correction fixtures belong here.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import html
import re
import gold_layout as gold


def numeric_tokens(body):
    text = html.unescape(re.sub(r'<[^>]*>', ' ', body))
    tokens = []
    for match in re.finditer(r'(?<![A-Za-z0-9])[-−]?\d+(?:[,./-]\d+)*(?:\.\d+)?%?', text):
        value = match.group()
        if text[max(0, match.start()-1):match.start()] == '(' and text[match.end():match.end()+1] == ')':
            value = '(' + value + ')'
        tokens.append(value)
    tokens.extend(re.findall('[₹$£€]', text))
    return Counter(tokens)


def grid_valid(model):
    rows, columns = model.get('rows', 0), model.get('columns', 0)
    if not isinstance(rows, int) or not isinstance(columns, int) or not 0 < rows <= 500 or not 0 < columns <= 100:
        return False
    occupied = set()
    for cell in model.get('cells', []):
        r, c, rs, cs = (cell.get(k, default) for k, default in
                        [('row', -1), ('column', -1), ('rowspan', 1), ('colspan', 1)])
        if any(not isinstance(x, int) for x in (r, c, rs, cs)) or min(r, c) < 0 or min(rs, cs) < 1 or r + rs > rows or c + cs > columns:
            return False
        for y in range(r, r + rs):
            for x in range(c, c + cs):
                if (y, x) in occupied:
                    return False
                occupied.add((y, x))
    return len(occupied) == rows * columns


def correct_question(row, decision, actual_source_hash):
    result = deepcopy(row)
    record = result['import_record']
    before = record['rich_content']['question']['body_html']
    if record['stable_id'] != decision['stable_id'] or actual_source_hash != record['source_hash'] or actual_source_hash != decision['source_hash']:
        raise ValueError('Correction source identity differs')
    if hashlib.sha256(before.encode()).hexdigest() != decision['before_html_sha256']:
        raise ValueError('Stale question correction')
    blocks = result['question']['blocks']
    tables = [b for b in blocks if b['type'] == 'table']
    for edit in decision['tables']:
        model = deepcopy(edit['model'])
        if not grid_valid(model):
            raise ValueError('Invalid source-backed table grid')
        original = tables[edit['index']]
        if model['page'] != original['page'] or model['bbox'] != original['bbox']:
            raise ValueError('Correction source region differs')
        original.clear()
        original.update(model)
    tail = decision.get('remove_tail_heading', '')
    if tail:
        last = blocks[-1]
        if not last.get('html', '').endswith(tail):
            raise ValueError('Expected following-question heading not found')
        last['html'] = last['html'][:-len(tail)]
    after = '\n'.join(gold.table_html(b) if b['type'] == 'table' else
                      '<' + ('h4' if b['type'] == 'heading' else 'p') + '>' + b['html'] +
                      '</' + ('h4' if b['type'] == 'heading' else 'p') + '>' for b in blocks)
    if numeric_tokens(before) != numeric_tokens(after):
        raise ValueError('Numerical token multiset changed; source correction requires separate evidence')
    record['rich_content']['question']['body_html'] = after
    record['rich_content']['question']['structure']['blocks'] = deepcopy(blocks)
    record['rich_content']['question']['checks']['r012_numeric_multiset_unchanged'] = True
    # Existing integrity holds and failed checks remain. Structural correction
    # is not owner approval or independent human academic verification.
    result['question']['body_html'] = after
    result['question']['plain_text'] = html.unescape(re.sub('<[^>]+>', ' ', after))
    result['question']['r012_source_table_correction'] = dict(
        source_hash=actual_source_hash, review_status='Needs Review',
        independent_human_verification=False)
    return result
