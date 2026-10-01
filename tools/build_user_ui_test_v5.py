"""Integrate two pending user textures into v4 without changing unrelated bytes."""
import sys,json,zipfile
from pathlib import Path
from localization_pipeline import ROOT,sha,hed_tree,write_json
from iso_archive_stage import iso_inventory,exact,overlay
from ui_texture_codec import parse,serialize,unpack_indices
import build_user_translation_import as verifier
sys.path.insert(0,str(ROOT/'build/python_psd'))
import numpy as np
BASE=ROOT/'build/user_ui_test_v4/Poison Pink (Japan) - Korean user UI test v4.iso'
BASE_SHA='ace426201a5e31336ad3f4a6e26eb2b56099fc76683657abcba4fecc53738686'
B=ROOT/'build/user_ui_test_v5';ISO=B/'Poison Pink (Japan) - Korean user UI test v5.iso'
assert not B.exists();B.mkdir()
inv=iso_inventory(BASE);files={e['path']:e for e in inv['files']};patches=[];entries=[];sources=[]
with BASE.open('rb') as f:
 h=files['DATA/STATUS.HED'];d=files['DATA/STATUS.DAT'];f.seek(h['lba']*2048);members={e['path']:e for e in hed_tree(exact(f,h['size']))[0]}
 for name in ['user_csl_bg1_v1','user_sys045_v1']:
  rp=ROOT/'reports'/(name+'.json');r=json.loads(rp.read_text());assert r['status']=='prepared_not_applied_to_iso';asset=r['pending_assets'][0];data=(ROOT/asset['replacement']).read_bytes();assert sha(data)==asset['sha256'];e=members[asset['member']];pos=d['lba']*2048+e['offset'];f.seek(pos);old=exact(f,e['size']);om=parse(old);nm=parse(data)
  assert len(old)==len(data) and om['header']==nm['header'] and om['palette']==nm['palette'] and nm['bpp']==8
  mask=np.zeros((nm['height'],nm['width']),bool)
  for x,y,w,h in r['edit_rectangles_xywh']:mask[y:y+h,x:x+w]=True
  ni=np.frombuffer(unpack_indices(nm),np.uint8).reshape(mask.shape).copy();oi=np.frombuffer(unpack_indices(om),np.uint8).reshape(mask.shape);ni[~mask]=oi[~mask];nm['indices']=ni.tobytes();data=serialize(nm);assert np.array_equal(ni[~mask],oi[~mask])
  dest=B/'textures/STATUS'/asset['member'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  patches.append(dict(offset=pos,data=data,expected_sha256=sha(old)));entries.append(dict(member=asset['member'],offset=pos,size=len(data),before_sha256=sha(old),after_sha256=sha(data),outside_edit_regions_preserved=True));sources.append((name,rp,r))
print('Building v5: character-selection background and equipment labels',flush=True)
result=overlay(BASE,ISO,patches,BASE_SHA);assert iso_inventory(ISO)==inv
print('Comparing entire ISO and re-reading both texture members',flush=True)
verifier.BASE_HASH=BASE_SHA;verified=verifier.verify_stream(BASE,ISO,patches,result['output_sha256'])
with ISO.open('rb') as f:
 for e in entries:f.seek(e['offset']);assert sha(exact(f,e['size']))==e['after_sha256']
r=dict(status='applied_to_iso',date='2026-09-24',iso_path=str(ISO.relative_to(ROOT)),base_iso=str(BASE.relative_to(ROOT)),iso=result,replacements=entries,whole_iso_verification=verified,runtime_verified=False)
write_json(B/'report.json',r);write_json(ROOT/'reports/user_ui_test_v5.json',r);(B/'SHA256SUMS.txt').write_text(result['output_sha256']+'  '+ISO.name+'\n')
side=Path(str(ISO)+'.pcsx2');assert json.loads((side/'manifest.json').read_text())['iso_sha256']==result['output_sha256']
with zipfile.ZipFile(B/'PCSX2_대화표시_호환패키지.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(side.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(side))
with zipfile.ZipFile(B/'PCSX2_대화표시_호환패키지.zip') as z:assert z.testzip() is None
(B/'먼저읽기.md').write_text(f'''# 사용자 UI 중간 테스트 v5 — 2026-09-24

실행 파일: `{ISO.name}`
SHA-256: `{result['output_sha256']}`

v4에 대기 중이던 사용자 PSD 두 장을 추가했습니다.
- csl_bg1: 캐릭터 선택 안내와 선택·결정·줄거리·취소.
- sys045: 장비 세 가지 상태 표기.

기존 캐릭터 이름판·구속 두께 수정·메뉴·대사·영상·전투조건 수정 유지. 두 텍스처 밖 전체 ISO 바이트 동일 및 각 텍스처 편집 범위 밖 인덱스 보존 검사 통과. 실제 게임 표시는 아직 미검증입니다.
새 ISO로 부팅하고 메모리카드 저장을 불러오세요. 이전 상태저장은 과거 텍스처가 남을 수 있습니다. 기존 CRC7502FF83 대화 표시 호환 패치는 계속 사용하세요. 사용자 카드·상태저장·설정은 변경하지 않았습니다.

검증: ../../reports/user_ui_test_v5.json
''')
for name,rp,asset_report in sources:
 asset_report['applied_assets']=asset_report.pop('pending_assets');asset_report.update(status='applied_to_iso',iso_built=True,iso_path=r['iso_path'],integration_report='reports/user_ui_test_v5.json');write_json(rp,asset_report);write_json(ROOT/'build'/name/'report.json',asset_report)
 doc=ROOT/'outputs'/name/'먼저읽기.md';s=doc.read_text();doc.write_text(s+'\n\n## 통합 완료\n\n위 적용 대기 상태를 대체합니다. '+r['iso_path']+'에 반영 완료. 실제 게임 미검증.\n')
pf=ROOT/'localization/pipeline.json';cfg=json.loads(pf.read_text());cfg['latest_experimental_build']=dict(path=r['iso_path'],sha256=result['output_sha256'],pcsx2_sidecar=r['iso_path']+'.pcsx2',report='reports/user_ui_test_v5.json',runtime_verified=False);cfg['static_checks']['user_ui_test_v5_entire_iso_verified']=True;write_json(pf,cfg)
hp=ROOT/'HANDOVER.md';s=hp.read_text().replace('## 최신 실행 ISO: 사용자 UI 중간 테스트 v4','## 이전 기반 ISO: 사용자 UI 중간 테스트 v4',1)
s=s.replace('## 적용 대기: 사용자 csl_bg1','## 준비 당시 기록 (v5 반영 완료): 사용자 csl_bg1',1).replace('## 적용 대기: 사용자 sys045','## 준비 당시 기록 (v5 반영 완료): 사용자 sys045',1)
section=f'''## 최신 실행 ISO: 사용자 UI 중간 테스트 v5 (2026-09-24)

`{r['iso_path']}`
SHA-256: `{result['output_sha256']}`.

v4 기반에 사용자 csl_bg1/sys045 대기 작업 반영 완료. 아래 준비 당시의 적용 대기/ISO 미수정 기록은 이 상태로 대체. 기존 모든 작업 유지. 두 멤버 재읽기, 전체 ISO 계획 밖 바이트 동일 및 문구 영역 밖 인덱스 보존 검사 통과. 실제 게임 미검증. CRC7502FF83 호환 sidecar/ZIP 동봉. `reports/user_ui_test_v5.json` 참조.

''';hp.write_text(s.replace('\n\n','\n\n'+section,1))
print(json.dumps(dict(iso=r['iso_path'],sha256=result['output_sha256'],verification=verified),ensure_ascii=False),flush=True)
