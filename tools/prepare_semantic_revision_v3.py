#!/usr/bin/env python3
import json,csv,hashlib
from pathlib import Path
from collections import defaultdict,Counter
from korean_sentence_probe import encode_korean,decode_korean
from status_db_codec import SCHEMAS
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'localization/semantic_revision_v3'

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 corpus=[json.loads(l) for l in (ROOT/'outputs/translation_review_20260920/corpus.jsonl').open()]
 byid={r['id']:r for r in corpus}; scenes=defaultdict(list)
 for r in corpus:scenes[(r['path'],r['function'])].append(r)
 prior=[json.loads(l) for l in (ROOT/'outputs/translation_review_20260920/corrections.jsonl').open()]
 edits={r['id']:dict(id=r['id'],source=r['source'],before=r['target'],target=r['proposed_target'],reason=r['reason'],path=r['path'],kind=r['kind']) for r in prior}
 for ident,r in edits.items():
  if r['source']=='教皇の聖杖':
   r['target']='교황의 성스런 봉';r['reason']+='; 이름칸18바이트에 맞춘 축약, 원뜻은 교황의 성스러운 지팡이'
 for line in '\n'.join(p.read_text().strip() for p in sorted((ROOT/'localization/review_20260920').glob('scene_rewrite_*.txt'))).splitlines():
  ident,target=line.split('|',1);target=target.replace('\\n','\n');r=byid[ident]
  for x in scenes[(r['path'],r['function'])]:
   if (x['source'],x['target'])==(r['source'],r['target']) and x['target']!=target:
    edits[x['id']]=dict(id=x['id'],source=x['source'],before=x['target'],target=target,reason='테이지 이벤트01~16 및 99 장면 전체 원문 대조 및 인물 말투 정리',path=x['path'],kind=x['kind'])
 mapping=json.loads((ROOT/'reports/system_messages_v1.json').read_text())['mapping'];issues=[]
 for r in edits.values():
  cap=255
  if r['kind']=='db_field':
   p,s,i,f=r['id'].split(':');cap=next(x[2]-1 for x in SCHEMAS[Path(p).stem][int(s)] if x[0]==f)
  r['capacity']=cap;r['encoded_bytes']=sum(1 if ord(c)<128 else 2 for c in r['target'])
  try:
   raw=encode_korean(r['target'],mapping);assert decode_korean(raw,mapping)==r['target'];assert len(raw)<=cap
  except (ValueError,AssertionError) as e:issues.append(dict(id=r['id'],target=r['target'],issue=str(e) or 'capacity'))
  r['line_width_units']=[sum(1 if ord(c)<128 else 2 for c in l) for l in r['target'].split('\n')]
 rows=sorted(edits.values(),key=lambda x:x['id'])
 with (OUT/'changes.jsonl').open('w') as f:
  for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
 (OUT/'preflight.json').write_text(json.dumps(dict(count=len(rows),kinds=dict(Counter(r['kind'] for r in rows)),issues=issues,full_game_semantic_review=False,reviewed_scene_files=['ft_%02d.rtb'%i for i in list(range(1,17))+[99]],runtime_verified=False),ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(count=len(rows),issues=issues,long_dialogue_lines=[dict(id=r['id'],target=r['target'],widths=r['line_width_units']) for r in rows if r['kind']=='rtb_literal' and max(r['line_width_units'])>36]),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
