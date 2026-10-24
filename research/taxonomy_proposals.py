"""Propose REVIEW-ONLY navigation from observed ICAI contents metadata.

This does not classify questions. Printed chapter.page references outrank an
incomplete captured heading sequence. Missing units/wrapped titles are held.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path

def propose(sources,catalogue,word_budget=180):
    nodes=catalogue['nodes'];chapters={};children=collections.defaultdict(list)
    for n in nodes:
        if n['node_type']=='chapter':
            m=re.search(r'Chapter\s*(\d+)',n['title'],re.I)
            if m:chapters[(n['subject_code'],n['edition_key'],n.get('parent_key',''),int(m[1]))]=n
        if n['node_type']=='unit':children[n['parent_key']].append(n)
    proposed=[];exceptions=[];coverage=[]
    for source in sources:
        code=source['subject'];edition=source.get('edition_key',code.lower()+'-may2026');module=source['module'];candidates=collections.defaultdict(list)
        for line in sorted(source['lines'].values(),key=lambda r:r['line']):
            text=line['text'];m=re.match(r'^(\d+(?:\.\d+)*)(?:[.)])?\s+(.+?)\.{3,}\s*(\d+)\.(\d+)\s*$',text)
            if not m:continue
            number,title,chapter_no,page=m.groups();title=re.sub(r'\s+',' ',title).strip();chapter_no=int(chapter_no)
            if title.lower() in ('introduction','overview','meaning','definitions','definition','conclusion','summary'):continue
            matches=[n for key,n in chapters.items() if key[0]==code and key[1]==edition and key[3]==chapter_no and (code!='IDT' or key[2].endswith('-m'+str(module)))]
            if len(matches)!=1:exceptions.append(dict(source_url=source['url'],page=line['page'],section=number,title=title,reason='chapter_or_edition_unresolved'));continue
            ch=matches[0]
            if len(title)>170 or len(title.split())>12:exceptions.append(dict(source_url=source['url'],page=line['page'],section=number,title=title,reason='needs_editorial_paraphrase'));continue
            entry=dict(chapter=ch,section=number,title=title,line=line['line'],page=line['page'],printed_page=chapter_no.__str__()+'.'+page)
            candidates[ch['node_key']].append(entry)
        # Balanced source budget: cover each chapter before selecting extra detail.
        selected=[];words=0;groups=list(candidates.values());index=0
        while any(index<len(g) for g in groups):
            for group in groups:
                if index>=len(group):continue
                e=group[index];cost=len(e['title'].split())
                if words+cost<=word_budget:selected.append(e);words+=cost
            index+=1
        selected.sort(key=lambda e:(e['chapter']['position'],[int(x) for x in e['section'].split('.')],e['line']))
        made={};resolved=0
        for e in selected:
            ch=e['chapter'];key=edition+'-tocv04-'+hashlib.sha256((source['url']+'|'+ch['node_key']+'|'+e['section']+'|'+e['title']).encode()).hexdigest()[:16]
            units=children[ch['node_key']]
            if units:
                exceptions.append(dict(source_url=source['url'],page=e['page'],section=e['section'],title=e['title'],reason='official_unit_parent_needs_owner_mapping',candidate_parent_keys=[u['node_key'] for u in units],edition_key=edition,chapter_key=ch['node_key']));continue
            parent_section=e['section'].rsplit('.',1)[0] if '.' in e['section'] else None
            parent=made.get((ch['node_key'],parent_section));node_type='subtopic' if parent and parent['node_type']=='topic' else 'topic';parent_key=parent['node_key'] if node_type=='subtopic' else ch['node_key']
            n=dict(node_key=key,edition_key=edition,subject_code=code,parent_key=parent_key,node_type=node_type,title=e['title'],position=int(e['section'].split('.')[-1])*100,heading_origin='editorial',source_url=source['url'],source_location=f"TOC PDF p.{e['page']}; printed {e['printed_page']}; section {e['section']}; retrieved 2026-10-24. Editorial navigation proposal.",review_status='needs_review',publication_status='draft')
            made[(ch['node_key'],e['section'])]=n;proposed.append(n);resolved+=1
        coverage.append(dict(subject=code,module=module,source_url=source['url'],proposed_nodes=resolved,derived_label_words=words,word_budget=word_budget,source_snapshot_sha256=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest(),snapshot_is_not_pdf_byte_hash=True))
    return dict(nodes=proposed,exceptions=exceptions,sources=coverage,review_status='needs_review',publication_status='draft',note='Proposed editorial navigation, never an assertion that these are ICAI-numbered units. Short factual TOC labels only; no question/answer prose. Unit-ambiguous entries are held instead of guessed.')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--metadata',required=True);p.add_argument('--catalogue',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=propose(json.loads(Path(a.metadata).read_text()),json.loads(Path(a.catalogue).read_text()));Path(a.output).write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n');print(json.dumps(dict(nodes=len(r['nodes']),exceptions=len(r['exceptions']),subjects=dict(collections.Counter(n['subject_code'] for n in r['nodes'])))))
