"""Integrate two pending user textures into v4 without changing unrelated bytes."""
import sys,json,zipfile
from pathlib import Path
from localization_pipeline import ROOT,sha,hed_tree,write_json
from iso_archive_stage import iso_inventory,exact,overlay
from ui_texture_codec import parse,serialize,unpack_indices
import build_user_translation_import as verifier
sys.path.insert(0,str(ROOT/'build/python_psd'))
import numpy as np
BASE=ROOT/'build/user_ui_test_v5/Poison Pink (Japan) - Korean user UI test v5.iso'
BASE_SHA='e47cb3f57e0196a3e195024c3971d45b2be1146c18ebba21694a1d2629abce90'
B=ROOT/'build/user_ui_test_v6';ISO=B/'Poison Pink (Japan) - Korean user UI test v6.iso'
assert not B.exists();B.mkdir()
inv=iso_inventory(BASE);files={e['path']:e for e in inv['files']};patches=[];entries=[];sources=[]
with BASE.open('rb') as f:
 h=files['DATA/STATUS.HED'];d=files['DATA/STATUS.DAT'];f.seek(h['lba']*2048);members={e['path']:e for e in hed_tree(exact(f,h['size']))[0]}
 for name in ['user_sys045_v2']:
  rp=ROOT/'reports'/(name+'.json');r=json.loads(rp.read_text());assert r['status']=='prepared_not_applied_to_iso';asset=r['pending_assets'][0];data=(ROOT/asset['replacement']).read_bytes();assert sha(data)==asset['sha256'];e=members[asset['member']];pos=d['lba']*2048+e['offset'];f.seek(pos);old=exact(f,e['size']);assert sha(old)==r['previous_texture_sha256'];om=parse(old);nm=parse(data)
  assert len(old)==len(data) and om['header']==nm['header'] and om['palette']==nm['palette'] and nm['bpp']==8
  mask=np.zeros((nm['height'],nm['width']),bool)
  for x,y,w,h in r['edit_rectangles_xywh']:mask[y:y+h,x:x+w]=True
  ni=np.frombuffer(unpack_indices(nm),np.uint8).reshape(mask.shape).copy();oi=np.frombuffer(unpack_indices(om),np.uint8).reshape(mask.shape);ni[~mask]=oi[~mask];nm['indices']=ni.tobytes();data=serialize(nm);assert np.array_equal(ni[~mask],oi[~mask])
  dest=B/'textures/STATUS'/asset['member'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  patches.append(dict(offset=pos,data=data,expected_sha256=sha(old)));entries.append(dict(member=asset['member'],offset=pos,size=len(data),before_sha256=sha(old),after_sha256=sha(data),outside_edit_regions_preserved=True));sources.append((name,rp,r))
print('Building v6: revised equipment labels',flush=True)
result=overlay(BASE,ISO,patches,BASE_SHA);assert iso_inventory(ISO)==inv
print('Comparing entire ISO and re-reading updated texture member',flush=True)
verifier.BASE_HASH=BASE_SHA;verified=verifier.verify_stream(BASE,ISO,patches,result['output_sha256'])
with ISO.open('rb') as f:
 for e in entries:f.seek(e['offset']);assert sha(exact(f,e['size']))==e['after_sha256']
r=dict(status='applied_to_iso',date='2026-09-30',iso_path=str(ISO.relative_to(ROOT)),base_iso=str(BASE.relative_to(ROOT)),iso=result,replacements=entries,whole_iso_verification=verified,runtime_verified=False)
write_json(B/'report.json',r);write_json(ROOT/'reports/user_ui_test_v6.json',r);(B/'SHA256SUMS.txt').write_text(result['output_sha256']+'  '+ISO.name+'\n')
side=Path(str(ISO)+'.pcsx2');assert json.loads((side/'manifest.json').read_text())['iso_sha256']==result['output_sha256']
with zipfile.ZipFile(B/'PCSX2_대화표시_호환패키지.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(side.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(side))
with zipfile.ZipFile(B/'PCSX2_대화표시_호환패키지.zip') as z:assert z.testzip() is None

assert verified['passed']
(B/'먼저읽기.txt').write_text('사용자 UI 테스트 v6 — 2026-09-30\n최신 sys045 수정 PSD 반영. v5의 나머지 작업 유지. 전체 ISO 변경 범위 검사 통과. 게임 실행 미검증.\n새 ISO로 부팅하세요. 기존 CRC7502FF83 대화 표시 호환 패치는 계속 사용하세요.\n')
for name,rp,ar in sources:
 ar['applied_assets']=ar.pop('pending_assets');ar.update(status='applied_to_iso',iso_built=True,iso_path=r['iso_path'],integration_report='reports/user_ui_test_v6.json');write_json(rp,ar);write_json(ROOT/'build'/name/'report.json',ar)
 doc=ROOT/'outputs'/name/'먼저읽기.txt';doc.write_text(doc.read_text()+'\n위 적용 대기 기록을 대체: '+r['iso_path']+' 통합 완료.\n')
pf=ROOT/'localization/pipeline.json';cfg=json.loads(pf.read_text());cfg['latest_experimental_build']=dict(path=r['iso_path'],sha256=result['output_sha256'],pcsx2_sidecar=r['iso_path']+'.pcsx2',report='reports/user_ui_test_v6.json',runtime_verified=False);cfg['static_checks']['user_ui_test_v6_entire_iso_verified']=True;write_json(pf,cfg)
hp=ROOT/'HANDOVER.md';s=hp.read_text().replace('## 최신 실행 ISO: 사용자 UI 중간 테스트 v5','## 이전 기반 ISO: 사용자 UI 중간 테스트 v5',1).replace('## 적용 대기: sys045 수정본 v2','## 준비 당시 기록 (v6 반영 완료): sys045 수정본 v2',1)
section=f"## 최신 실행 ISO: 사용자 UI 중간 테스트 v6 (2026-09-30)\n\n`{r['iso_path']}`\nSHA-256: `{result['output_sha256']}`.\n\nv5 기반에 최신 sys045 v2 수정본 반영. 전체 ISO 계획 밖 바이트 동일 및 문구 영역 밖 인덱스 보존 확인. 게임 실행 미검증. 호환 sidecar/ZIP 동봉. reports/user_ui_test_v6.json 참조.\n\n"
hp.write_text(s.replace('\n\n','\n\n'+section,1))
print(json.dumps(dict(iso=r['iso_path'],sha256=result['output_sha256'],verification=verified),ensure_ascii=False),flush=True)
