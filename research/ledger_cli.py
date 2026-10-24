#!/usr/bin/env python3
"""Append a private reviewed correction without overwriting any history.
Usage: python research/ledger_cli.py ledger.json event.json --output work/new-ledger.json
"""
import argparse
import json
from pathlib import Path
import corrections

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ledger');p.add_argument('event');p.add_argument('--output',required=True);a=p.parse_args()
    output=Path(a.output).resolve();private=Path(__file__).resolve().parents[1]/'work'
    if private.resolve() not in output.parents or output.exists():p.error('Use a NEW output file under private work/; previous ledgers cannot be overwritten.')
    ledger=corrections.append(json.loads(Path(a.ledger).read_text()),json.loads(Path(a.event).read_text()))
    with output.open('x',encoding='utf-8') as f:json.dump(ledger,f,indent=2,ensure_ascii=False)
    print('New ledger saved; prior events retained. No publication or WordPress changes.')
