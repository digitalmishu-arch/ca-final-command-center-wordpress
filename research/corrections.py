"""Append-only, source/section/reference-scoped owner ledger with hash chaining.

The private browser downloads a new ledger file; CLI validation uses canonical
hashes. Decisions do not publish WordPress records. Conflicting approved changes
require an explicit supersedes event instead of silently replacing history.
"""
import hashlib
import json
from datetime import datetime, timezone


def digest(value):
    def canonical(v):
        if isinstance(v,float) and v.is_integer():return int(v)
        if isinstance(v,list):return [canonical(x) for x in v]
        if isinstance(v,dict):return {k:canonical(x) for k,x in v.items()}
        return v
    return hashlib.sha256(json.dumps(canonical(value),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def validate(ledger):
    previous=''
    for event in ledger.get('events',[]):
        payload={k:v for k,v in event.items() if k!='event_hash'}
        if payload.get('previous_hash')!=previous or digest(payload)!=event.get('event_hash'):
            raise ValueError('Corrections ledger history/hash chain is invalid')
        if not all(event.get(k) for k in ['source_sha256','section','reference','actor','decision','timestamp']):
            raise ValueError('Correction requires exact source/section/reference and reviewer provenance')
        previous=event['event_hash']
    return True


def append(ledger, event):
    validate(ledger)
    payload={**event,'timestamp':event.get('timestamp') or datetime.now(timezone.utc).isoformat(),
             'previous_hash':ledger.get('events',[])[-1]['event_hash'] if ledger.get('events') else ''}
    key=lambda e:(e['source_sha256'],e['section'],e['reference'],e.get('subreference',''))
    prior=[e for e in ledger.get('events',[]) if key(e)==key(payload) and e['decision']=='approved']
    if prior and payload['decision']=='approved' and payload.get('supersedes')!=prior[-1]['event_hash']:
        raise ValueError('An approved correction exists; explicitly supersede its event hash')
    payload['event_hash']=digest(payload)
    result={**ledger,'version':1,'events':ledger.get('events',[])+[payload]};validate(result)
    return result


def applicable(ledger, source_hash, section, ref, subref=''):
    validate(ledger)
    events=[e for e in ledger.get('events',[]) if (e['source_sha256'],e['section'],e['reference'],e.get('subreference',''))==(source_hash,section,ref,subref)]
    return events[-1] if events else None


def metrics(records, ledger):
    """Separate exact agreements on owner-approved labelled fields only."""
    fields={'boundary_agreement':'boundary','chapter_agreement':'chapter_key',
            'unit_topic_agreement':'unit_topic_keys','answer_location_coverage':'answer_locations'}
    result={}
    for name,field in fields.items():
        eligible=[]
        for r in records:
            e=applicable(ledger,r['source_sha256'],r['section'],r['reference'],r.get('subreference',''))
            if e and e['actor']=='owner' and e['decision']=='approved' and field in e.get('labels',{}) and (field!='answer_locations' or e['labels'][field]):eligible.append((r,e['labels'][field]))
        correct=sum(r.get('metric_values',{}).get(field)==expected for r,expected in eligible)
        result[name]={'agreement':correct,'labelled_sample':len(eligible),
                      'percentage':round(correct/len(eligible)*100,2) if eligible else None,
                      'scope':'Owner-labelled fields only; unavailable without an approved benchmark'}
    pending=sum(r.get('owner_state')!='approved' for r in records)
    result['manual_review']={'count':pending,'total':len(records),'percentage':round(pending/len(records)*100,2) if records else None}
    verified_answers=sum(1 for r in records if (ev:=applicable(ledger,r['source_sha256'],r['section'],r['reference'],r.get('subreference',''))) and ev['actor']=='owner' and ev['decision']=='approved' and ev.get('labels',{}).get('answer_locations') and ev['labels']['answer_locations']==r.get('metric_values',{}).get('answer_locations'))
    result['answer_location_verification_coverage']={'verified':verified_answers,'total':len(records),'percentage':round(verified_answers/len(records)*100,2) if records else None}
    result['global_accuracy']=None
    return result
