#!/usr/bin/env python3
"""Capture one verified project PCSX2 interaction into the status-slice evidence."""
import argparse
import json
import shutil
import time
from pathlib import Path
from runtime_keys import send, KEYS

p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True)
p.add_argument('--settle',type=float,default=2)
p.add_argument('--label',required=True);p.add_argument('keys',nargs='*')
a=p.parse_args()
if any(k not in KEYS for k in a.keys):raise ValueError('Unknown input key')
if not 0<=a.settle<=30:raise ValueError('Invalid settle duration')
if not a.label.replace('-','').replace('_','').isalnum():raise ValueError('Invalid evidence label')
root=Path(__file__).resolve().parents[1];snaps=root/'build/runtime/snaps'
out=root/'build/status_slice/evidence'/(a.label+'.png')
if out.exists():raise ValueError('Evidence already exists')
before={p.name for p in snaps.glob('*.png')}
if a.keys:send(a.pid,a.keys)
time.sleep(a.settle)
send(a.pid,['screenshot'])
new=[p for p in snaps.glob('*.png') if p.name not in before]
if len(new)!=1:raise ValueError('Expected one new game screenshot')
shutil.copy2(new[0],out)
print(json.dumps(dict(path=str(out),keys=a.keys,pid=a.pid,original_path=str(new[0]))))
