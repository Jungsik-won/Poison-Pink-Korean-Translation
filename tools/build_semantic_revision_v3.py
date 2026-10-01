#!/usr/bin/env python3
"""Apply reviewed semantic edits to current ISO; preserve assets and all untargeted text."""
import json,struct
from collections import defaultdict
from pathlib import Path
from localization_pipeline import sha,file_hash,hed_tree,write_json
from iso_archive_stage import iso_inventory,exact,overlay
from korean_sentence_probe import encode_korean,decode_korean
import rtb_codec as rtb
import status_db_codec as db
import build_user_translation_import as verifier
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/korean_integrated_20260920/Poison Pink (Japan) - Korean integrated 20260920.iso'
BASE_SHA='2adb730382015a49d69d850445a7d8950fb9efdc313610c9610259d7acea942c'
OUT=ROOT/'build/semantic_revision_v3'
OUTPUT=OUT/'Poison Pink (Japan) - Korean dialogue revision v3.iso'
INPUT=ROOT/'localization/semantic_revision_v3'

def ops(model):return [o for f in model['functions'] for o in f['instructions'] if o['opcode']==0x33]
def main():
 if OUTPUT.exists():raise ValueError('Completed ISO already exists')
 preflight=json.loads((INPUT/'preflight.json').read_text());assert not preflight['issues']
 rows=[json.loads(l) for l in (INPUT/'changes.jsonl').open()];assert len(rows)==preflight['count']
 ids={r['id'] for r in rows};assert len(ids)==len(rows)
 metadata={}
 for l in (ROOT/'localization/imports/20260917_corrected/plan.jsonl').open():
  r=json.loads(l)
  if r['id'] in ids:metadata[r['id']]=r['metadata']
 assert set(metadata)==ids
 mapping=json.loads((ROOT/'reports/system_messages_v1.json').read_text())['mapping']
 bypath=defaultdict(list)
 for r in rows:
  m=metadata[r['id']];assert m['source']==r['source'] and m['path']==r['path']
  raw=encode_korean(r['target'],mapping);assert decode_korean(raw,mapping)==r['target'];assert len(raw)<=r['capacity']
  bypath[r['path']].append(r)
 inv=iso_inventory(BASE);files={e['path']:e for e in inv['files']};patches=[];checks=[];hed_checks=[]
 with BASE.open('rb') as fp:
  for archive in ('DMAP','STATUS'):
   he=files['DATA/'+archive+'.HED'];de=files['DATA/'+archive+'.DAT'];fp.seek(he['lba']*2048)
   hed=exact(fp,he['size']);newhed=bytearray(hed);members=hed_tree(hed)[0];ordered=sorted(members,key=lambda e:e['offset'])
   limits={e['path']:ordered[i+1]['offset'] if i+1<len(ordered) else de['size'] for i,e in enumerate(ordered)}
   for e in members:
    path=e['path']
    if path not in bypath:continue
    pos=de['lba']*2048+e['offset'];fp.seek(pos);current=exact(fp,e['size'])
    original=(ROOT/'extracted/original/raw'/archive/path).read_bytes()
    for r in bypath[path]:assert sha(original)==metadata[r['id']]['member_sha256']
    if path.endswith('.rtb'):
     orig=rtb.parse(original);before=rtb.parse(current);oldops=ops(orig);beforeops=ops(before)
     assert rtb.control_signature(orig)==rtb.control_signature(before)
     assert len(oldops)==len(beforeops);indexes={o['offset']:i for i,o in enumerate(oldops)};edits={}
     for r in bypath[path]:
      m=metadata[r['id']];i=indexes[m['opcode_offset']];assert oldops[i]['args'][0]==m['raw_hex']
      prior=bytes.fromhex(beforeops[i]['args'][0]);assert prior==encode_korean(r['before'],mapping),(r['id'],'stale translation')
      assert beforeops[i]['offset'] not in edits
      edits[beforeops[i]['offset']]=(prior,encode_korean(r['target'],mapping))
     modified=rtb.replace_strings(current,edits,sha(current));after=rtb.parse(modified)
     assert rtb.control_signature(before)==rtb.control_signature(after)
     afterops=ops(after);assert len(beforeops)==len(afterops)
     for a,b in zip(beforeops,afterops):assert bytes.fromhex(b['args'][0])==edits.get(a['offset'],(None,bytes.fromhex(a['args'][0])))[1]
    else:
     kind=Path(path).stem;before=db.parse(current,kind);original_fields=dict(db.text_fields(db.parse(original,kind)))
     fields=dict(db.text_fields(before));edits={}
     for r in bypath[path]:
      m=metadata[r['id']];key=(m['section'],m['record'],m['field'])
      assert original_fields[key]['value'].hex()==m['raw_hex'];assert key not in edits
      assert fields[key]['value']==encode_korean(r['before'],mapping),(r['id'],'stale translation')
      edits[key]=(fields[key]['value'],encode_korean(r['target'],mapping))
     modified=db.replace_text(current,kind,edits,sha(current));after=db.parse(modified,kind)
     assert db.nontext_signature(before)==db.nontext_signature(after)
    span=max(len(current),len(modified));assert e['offset']+span<=limits[path],(path,'insufficient verified member padding')
    fp.seek(pos);oldspan=exact(fp,span)
    assert not any(oldspan[len(current):]),(path,'nonzero member padding')
    patches.append(dict(offset=pos,data=modified+bytes(span-len(modified)),expected_sha256=sha(oldspan)))
    struct.pack_into('<I',newhed,e['index']*44+4,len(modified))
    checks.append(dict(path=path,archive=archive,offset=pos,before_bytes=len(current),after_bytes=len(modified),
      before_sha256=sha(current),after_sha256=sha(modified),corrections=len(bypath[path]),
      nontext_preserved=True,untargeted_text_preserved=True))
   original_entries,_=hed_tree(hed);final_entries,_=hed_tree(bytes(newhed))
   sizes={c['path']:c['after_bytes'] for c in checks if c['archive']==archive}
   assert final_entries==[dict(e,size=sizes.get(e['path'],e['size'])) for e in original_entries]
   if bytes(newhed)!=hed:patches.append(dict(offset=he['lba']*2048,data=bytes(newhed),expected_sha256=sha(hed)))
   hed_checks.append(dict(archive=archive,only_reviewed_member_sizes_changed=True))
 assert len(checks)==len(bypath)
 print('Validated',len(rows),'edits in',len(checks),'members. Writing ISO.',flush=True)
 result=overlay(BASE,OUTPUT,patches,BASE_SHA)
 assert iso_inventory(OUTPUT)==inv
 verifier.BASE_HASH=BASE_SHA
 print('Checking entire ISO and re-reading every changed member.',flush=True)
 verification=verifier.verify_stream(BASE,OUTPUT,patches,result['output_sha256'])
 with OUTPUT.open('rb') as fp:
  for c in checks:
   fp.seek(c['offset']);assert sha(exact(fp,c['after_bytes']))==c['after_sha256']
 report=dict(iso_path=str(OUTPUT.relative_to(ROOT)),iso=result,base_iso=str(BASE.relative_to(ROOT)),
   base_iso_sha256=BASE_SHA,changes_sha256=file_hash(INPUT/'changes.jsonl'),corrections=len(rows),
   changed_members=checks,archive_checks=hed_checks,whole_iso_verification=verification,
   font_and_elf_unchanged=True,user_artwork_unchanged=True,runtime_verified=False,full_game_semantic_review=False,
   reviewed_scene_files=preflight['reviewed_scene_files'])
 write_json(ROOT/'reports/semantic_revision_v3.json',report)
 print(json.dumps(dict(iso=report['iso_path'],sha256=result['output_sha256'],verification=verification,corrections=len(rows)),ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
