import json,re
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'localization/review_remaining_20260920'
def prepare():
 base={r['id']:r for r in map(json.loads,(ROOT/'localization/semantic_revision_v3/changes.jsonl').open())}
 groups={}
 for r in map(json.loads,(ROOT/'outputs/translation_review_20260920/corpus.jsonl').open()):
  if r['kind']!='rtb_literal':continue
  r=dict(r);r['target']=base.get(r['id'],{}).get('target',r['target'])
  if Path(r['path']).name in ['ft_%02d.rtb'%i for i in list(range(1,17))+[99]] and r['function'] not in ['<module>','_staffroll']:continue
  key=(r['source'],r['target']);groups.setdefault(key,[]).append(r)
 def order(item):
  r=item[1][0];p=Path(r['path']).stem
  return (0 if p.startswith('f') else 1 if p[0] in 'thord' else 2,p,int(r['id'].split(':')[-1],16))
 units=[]
 for n,((src,tgt),rs) in enumerate(sorted(groups.items(),key=order),1):
  units.append(dict(unit=n,source=src,target=tgt,contexts=[dict(id=r['id'],function=r['function']) for r in rs]))
 (OUT/'units.json').write_text(json.dumps(units,ensure_ascii=False,indent=2))
 print('Units',len(units),'locations',sum(len(r['contexts']) for r in units))
def show(start,end):
 for r in json.loads((OUT/'units.json').read_text())[start-1:end]:
  c=r['contexts'][0];print(r['unit'],c['id'].split('/')[-1],c['function'],r['source'].replace('\n',' / '),'=>',r['target'].replace('\n',' / '))
if __name__=='__main__':
 import sys
 if sys.argv[1]=='prepare':prepare()
 else:show(int(sys.argv[1]),int(sys.argv[2]))
