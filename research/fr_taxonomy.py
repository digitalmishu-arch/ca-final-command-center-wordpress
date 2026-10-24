"""Parse private captures of actual ICAI PDF contents, retaining exact evidence.

No generated topic names. Broken/multiline headings enter exceptions; a printed
page reference is never interpreted as a heading number. The WordPress shape
retains nested subtopics and the original complete numeric path.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re


def text_parts(result):
    return '\n'.join(c['text'] for c in result.get('content',[]) if c['type']=='text').split('-'*80)


def parse(evidence):
    groups={};exceptions=[]
    for collection in ('initial','continuation','last'):
        for item in evidence.get(collection,[]):
            key=(item['year'],item['module']);group=groups.setdefault(key,{'lines':{},'url':'','total':0})
            text=item['text'];url=re.search(r'\((https://resource\.cdn\.icai\.org/[^)]+)\)',text)
            if url:
                if group['url'] and group['url']!=url[1]:raise ValueError('Source URL changed across continuation')
                group['url']=url[1]
            total=re.search(r'Total lines: (\d+)',text)
            if total:group['total']=max(group['total'],int(total[1]))
            for line in text.splitlines():
                m=re.match(r'^L(\d+)@P(\d+)(?:-(\d+))?:\s*(.*)',line)
                if m:group['lines'][int(m[1])]=dict(pdf_page=int(m[2])+1,text=m[4],line=int(m[1]))
    nodes=[];editions=[]
    for (year,module),group in sorted(groups.items()):
        edition='fr-may2025-jan2026' if year=='2025' else 'fr-may'+year
        if not any(e['edition_key']==edition for e in editions):editions.append(dict(edition_key=edition,subject_code='FR',title='Financial Reporting — May '+year+' applicability',applicability='May/September 2025 and January 2026' if year=='2025' else 'May '+year+' onwards; maintain distinct subsequent editions',source_url='https://www.icai.org/post/sm-final-p1-may'+year,review_status='needs_review',publication_status='draft'))
        module_key=edition+'-m'+str(module)
        nodes.append(dict(node_key=module_key,edition_key=edition,subject_code='FR',parent_key='',node_type='module',title='Module '+str(module),heading_number=str(module),position=module,heading_origin='official',source_url=group['url'],source_location='Official module initial-pages PDF',review_status='needs_review',publication_status='draft'))
        chapter=None;unit=None;seen={};pending='';detailed=False
        ordered=[l for _,l in sorted(group['lines'].items())];skip=set()
        for index,line in enumerate(ordered):
            if index in skip:continue
            t=line['text'].strip()
            if re.search('DETAILED CONTENTS',t,re.I):detailed=True;continue
            if not detailed:continue
            # Join only a contents entry whose end is explicitly identified by
            # dot leaders and a printed page, or a wrapped chapter/unit title.
            if re.match(r'^(?:CHAPTER\s*[-–]?\s*\d+|UNIT\s+\d+|\d+\.\d+(?:\.\d+)*)\b',t,re.I):
                for j in range(index+1,min(index+6,len(ordered))):
                    if re.search(r'\.{3,}\s*\d+\.\d+\s*$',t):break
                    nxt=ordered[j]['text'].strip()
                    if '©' in nxt:continue
                    if re.match(r'^(?:CHAPTER|UNIT|Learning Outcomes|Chapter Overview|Unit Overview|Contents|\d+\.\d+)',nxt,re.I):break
                    if re.match(r'^(?:CHAPTER|UNIT)\s+\d+',t,re.I) and re.search(r'\.{3,}',nxt):break
                    if not re.match(r'^(?:CHAPTER|UNIT)\s+\d+',t,re.I) and not (re.search(r'\.{3,}',nxt) or len(nxt)>8):break
                    t+=' '+nxt;skip.add(j)
            c=re.match(r'^CHAPTER\s*[-–]?\s*(\d+)\s*[:–-]\s*(.+)',t,re.I)
            if c:
                number,title=c[1],c[2];key=module_key+'-ch'+number;chapter=key;unit=None;seen={};pending=''
                if not any(n['node_key']==key for n in nodes):nodes.append(dict(node_key=key,edition_key=edition,subject_code='FR',parent_key=module_key,node_type='chapter',title='Chapter '+number+': '+title,heading_number=number,position=int(number),heading_origin='official',source_url=group['url'],source_location='PDF p.'+str(line['pdf_page'])+'; contents line '+str(line['line']),review_status='needs_review',publication_status='draft'))
                continue
            u=re.match(r'^UNIT\s+(\d+)\s*[:–-]\s*(.+)',t,re.I)
            if u and chapter:
                unit=chapter+'-u'+u[1];seen={};pending=''
                if not any(n['node_key']==unit for n in nodes):nodes.append(dict(node_key=unit,edition_key=edition,subject_code='FR',parent_key=chapter,node_type='unit',title='Unit '+u[1]+': '+re.sub(r'\s*\.{2,}\s*\d+\.\d+\s*$','',u[2]),heading_number=u[1],position=int(u[1]),heading_origin='official',source_url=group['url'],source_location='PDF p.'+str(line['pdf_page']),review_status='needs_review',publication_status='draft'))
                continue
            if not chapter:continue
            # Contents entries have dot leaders AND a separate printed page.
            m=re.match(r'^(\d+\.\d+(?:\.\d+){0,4})\s+(.+?)\s*\.{3,}\s*(\d+\.\d+)\s*$',t)
            if not m:
                if re.match(r'^\d+\.\d+(?:\.\d+)*\s+',t):exceptions.append(dict(edition=edition,module=module,chapter=chapter,page=line['pdf_page'],code='multiline_or_ambiguous_contents_entry',evidence=t,source_url=group['url']))
                continue
            number,title,page=m.groups();base=unit or chapter;key=base+'-h'+number.replace('.','-')
            if key in seen:
                if seen[key]['title']!=title:exceptions.append(dict(edition=edition,code='conflicting_contents_heading',key=key,evidence=t))
                continue
            parent_number=number.rsplit('.',1)[0] if number.count('.')>1 else ''
            parent=base+'-h'+parent_number.replace('.','-') if parent_number else base
            if parent_number and parent not in seen:exceptions.append(dict(edition=edition,module=module,chapter=chapter,page=line['pdf_page'],code='missing_contents_parent',evidence=t,source_url=group['url']));continue
            node=dict(node_key=key,edition_key=edition,subject_code='FR',parent_key=parent,node_type='subtopic' if parent_number else 'topic',title=title,heading_number=number,printed_page=page,position=int(number.split('.')[-1]),heading_origin='official',source_url=group['url'],source_location='Contents PDF p.'+str(line['pdf_page'])+'; heading '+number+'; printed p.'+page,review_status='needs_review',publication_status='draft')
            seen[key]=node;nodes.append(node)
        if group['total'] and (not group['lines'] or max(group['lines'])<group['total']-1):exceptions.append(dict(edition=edition,module=module,code='incomplete_web_reader_capture',source_url=group['url']))
    # A short heading spread over lines is NOT filled by an AI guess. Keep an
    # explicit coverage gap so a reviewer can supply the exact source wording.
    return dict(editions=editions,nodes=nodes,exceptions=exceptions,origin='actual_official_pdf_contents_not_editorial',approval='needs_review')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('evidence');p.add_argument('--output',required=True);a=p.parse_args()
    result=parse(json.loads(Path(a.evidence).read_text()));Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'nodes':len(result['nodes']),'exceptions':len(result['exceptions'])}))
