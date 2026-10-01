#!/usr/bin/env python3
"""Compile explicit dialogue review decisions against immutable revision v3."""
import json,re,collections
from pathlib import Path
from korean_sentence_probe import encode_korean,decode_korean
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'localization/review_remaining_20260920'
OUT=ROOT/'localization/semantic_revision_v4'
def width(t):return sum(1 if ord(c)<128 else 2 for c in t)
def main():
 OUT.mkdir(exist_ok=True)
 units=json.loads((WORK/'units.json').read_text());edits={};origin={}
 for p in sorted(WORK.glob('edits_*.txt'))+[WORK/'final_adjustments.txt']:
  seen=set()
  for line in p.read_text().splitlines():
   if not line.strip():continue
   a,b=line.split('|',1);n=int(a);assert n not in seen;seen.add(n)
   assert 1<=n<=len(units)
   if p.name!='final_adjustments.txt':assert n not in edits
   edits[n]=b.replace('\\n','\n');origin[n]=p.name
 # These malformed/dialect fragments have been read but are not confidently resolved.
 pending={1262:'キサンハヨコッチャ segmentation unresolved',1565:'モッサイ sense unresolved',9395:'タベレ and argument omitted; avoid inventing who eats whom',10035:'ラクトチガウ unresolved',6776:'諸事 likely stylized homophone; interpretation unresolved'}
 for n in pending:edits.pop(n,None)
 # Explicitly reviewed spellings, only when the corresponding Japanese proper noun occurs.
 terms=[('テージ',{'테지':'테이지'}),
 ('シュテイン',{'슈테인':'슈타인'}),
 ('バスチョ',{'바스쵸':'바스초'}),
 ('スンウェイ',{'선웨이':'순웨이','순 웨이':'순웨이'}),
 ('シャンロン',{'샹론':'샹룽','샹롱':'샹룽'}),
 ('ツァイアー',{'자이어':'차이어'}),
 ('ラナンキュラス',{'라난큐라스':'라난큘러스'}),
 ('クニークルス',{'쿠니 크루즈':'쿠니클루스','쿠니크루즈':'쿠니클루스'}),
 ('キャンサギガス',{'캔서 기가스':'캔서기가스','캔사기 가스':'캔서기가스','캔사기가스':'캔서기가스'}),
 ('アクアコクレア',{'아쿠아 코 클레어':'아쿠아 코클레어','아쿠아코클레아':'아쿠아 코클레어','아쿠아 코클레아':'아쿠아 코클레어'}),
 ('双撃',{'협공':'쌍격'}),
 ('エル・ステーラ',{'엘 스텔라':'엘스테라','엘 스테라':'엘스테라'}),
 ('デス・ファルクス',{'데스 팔크스':'데스팔크스'}),
 ('クリスティーナ・センペル',{'크리스티나 셈페르':'크리스티나 센펠'})]
 mapping=json.loads((ROOT/'reports/system_messages_v1.json').read_text())['mapping']
 corpus={r['id']:r for r in map(json.loads,(ROOT/'outputs/translation_review_20260920/corpus.jsonl').open())}
 prior={r['id']:r for r in map(json.loads,(ROOT/'localization/semantic_revision_v3/changes.jsonl').open())}
 rows=[];issues=[];decisions=[]
 for u in units:
  n=u['unit'];t=edits.get(n,u['target']);reason='원문·연속 대화 문맥 대조; 인물 말투 및 오역 수정'
  for source,replacements in terms:
   if source not in u['source']:continue
   for before,after in replacements.items():t=t.replace(before,after)
  if t==u['target']:continue
  if n not in edits:reason='원문 고유명사 및 채용된 전투 UI 용어와 표기 통일'
  try:
   raw=encode_korean(t,mapping);assert decode_korean(raw,mapping)==t
   assert len(raw)<=255
  except (ValueError,AssertionError) as ex:issues.append(dict(unit=n,issue=str(ex) or 'capacity/roundtrip',target=t))
  widths=[width(l) for l in t.split('\n')]
  if max(widths)>36:issues.append(dict(unit=n,issue='line_width',widths=widths,target=t))
  decisions.append(dict(unit=n,source=u['source'],before=u['target'],target=t,contexts=len(u['contexts']),authoring=origin.get(n,'source-gated spelling normalization')))
  for c in u['contexts']:
   r=corpus[c['id']];assert r['source']==u['source'];assert prior.get(r['id'],r)['target']==u['target']
   rows.append(dict(id=r['id'],source=r['source'],before=u['target'],target=t,reason=reason,path=r['path'],kind='rtb_literal',capacity=255,encoded_bytes=width(t),line_width_units=widths,unit=n))
 assert len({r['id'] for r in rows})==len(rows)
 rows.sort(key=lambda r:r['id'])
 (OUT/'changes.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
 (OUT/'decisions.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2)+'\n')
 pending_rows=[dict(unit=n,source=units[n-1]['source'],current_target=units[n-1]['target'],reason=why,action='existing translation retained; no speculative replacement') for n,why in pending.items()]
 (OUT/'pending_context.json').write_text(json.dumps(pending_rows,ensure_ascii=False,indent=2)+'\n')
 pre=dict(count=len(rows),changed_units=len(decisions),reviewed_units=len(units),reviewed_locations=sum(len(u['contexts']) for u in units),changed_files=len(set(r['path'] for r in rows)),kinds={'rtb_literal':len(rows)},issues=issues,pending_units=len(pending_rows),full_game_semantic_review=False,dialogue_readthrough_complete=True,runtime_verified=False,reviewed_scene_files=sorted(set(c['id'].split(':')[0] for u in units for c in u['contexts'])))
 (OUT/'preflight.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in pre.items() if k!='reviewed_scene_files'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
