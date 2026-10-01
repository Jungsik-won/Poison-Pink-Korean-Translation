"""Build intermediate ISO with three user PSD imports, preserving prior changes."""
import sys,json,zipfile
from pathlib import Path
from localization_pipeline import ROOT,sha,hed_tree,write_json
from iso_archive_stage import iso_inventory,exact,overlay
from ui_texture_codec import parse,serialize,unpack_indices
import build_user_translation_import as verifier
sys.path.insert(0,str(ROOT/'build/python_psd'))
import numpy as np
BASE=ROOT/'build/character_tabs_ko_v1/Poison Pink (Japan) - Korean character names v1.iso'
BASE_SHA='703b15e773dc21bb668a748a13cea79e673f402324e74ec8439ae5efdfbe4efb'
B=ROOT/'build/user_ui_test_v1';ISO=B/'Poison Pink (Japan) - Korean user UI test v1.iso'

def main():
 assert not B.exists();B.mkdir();inv=iso_inventory(BASE);files={e['path']:e for e in inv['files']};patches=[];entries=[];reports=[]
 with BASE.open('rb') as f:
  he=files['DATA/STATUS.HED'];de=files['DATA/STATUS.DAT'];f.seek(he['lba']*2048);members={e['path']:e for e in hed_tree(exact(f,he['size']))[0]}
  for n in ['009','015','031']:
   rp=ROOT/f'reports/user_sys{n}_v1.json';r=json.loads(rp.read_text());assert r['status']=='prepared_not_applied_to_iso';asset=r['pending_assets'][0];assert asset['member']==f'status/sys{n}.tm2'
   data=(ROOT/asset['replacement']).read_bytes();assert sha(data)==asset['sha256'];e=members[asset['member']];pos=de['lba']*2048+e['offset'];f.seek(pos);old=exact(f,e['size']);om=parse(old);nm=parse(data)
   assert len(data)==len(old) and om['header']==nm['header'] and om['palette']==nm['palette'] and nm['bpp']==8
   mask=np.zeros((nm['height'],nm['width']),bool)
   rects=[row['rect'] for row in r['rows']] if n=='015' else r['edit_rectangles_xywh']
   for x,y,w,h in rects:mask[y:y+h,x:x+w]=True
   ni=np.frombuffer(unpack_indices(nm),np.uint8).reshape(mask.shape).copy();oi=np.frombuffer(unpack_indices(om),np.uint8).reshape(mask.shape)
   restored=int(np.count_nonzero(ni[~mask]!=oi[~mask]));ni[~mask]=oi[~mask];nm['indices']=ni.tobytes();data=serialize(nm);assert np.array_equal(ni[~mask],oi[~mask])
   dest=B/'textures/STATUS'/asset['member'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
   patches.append(dict(offset=pos,data=data,expected_sha256=sha(old)));entries.append(dict(member=asset['member'],offset=pos,size=len(data),before_sha256=sha(old),after_sha256=sha(data),preserved_prior_pixels_outside_edit_regions=restored,source_report=str(rp.relative_to(ROOT))));reports.append((rp,r))
 print('Building three-PSD intermediate test ISO',flush=True)
 result=overlay(BASE,ISO,patches,BASE_SHA);assert iso_inventory(ISO)==inv
 print('Checking every ISO byte and re-reading three texture members',flush=True)
 verifier.BASE_HASH=BASE_SHA;verified=verifier.verify_stream(BASE,ISO,patches,result['output_sha256'])
 with ISO.open('rb') as f:
  for e in entries:f.seek(e['offset']);assert sha(exact(f,e['size']))==e['after_sha256']
 r=dict(status='built',iso_path=str(ISO.relative_to(ROOT)),base_iso=str(BASE.relative_to(ROOT)),iso=result,replacements=entries,whole_iso_verification=verified,runtime_verified=False,discarded_15_image_work_included=False)
 write_json(B/'report.json',r);write_json(ROOT/'reports/user_ui_test_v1.json',r);(B/'SHA256SUMS.txt').write_text(result['output_sha256']+'  '+ISO.name+'\n')
 side=Path(str(ISO)+'.pcsx2');sm=json.loads((side/'manifest.json').read_text());assert sm['iso_sha256']==result['output_sha256']
 with zipfile.ZipFile(B/'PCSX2_대화표시_호환패키지.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(side.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(side))
 with zipfile.ZipFile(B/'PCSX2_대화표시_호환패키지.zip') as z:assert z.testzip() is None
 (B/'먼저읽기.md').write_text(f'''# 사용자 PSD 3장 중간 테스트 ISO

실행 파일: `{ISO.name}`
SHA-256: `{result['output_sha256']}`

기존 캐릭터 이름판 통합판에 사용자 작업 3장만 추가했습니다.
- sys009: 결정·취소·선택.
- sys015: 21개 메뉴 문구와 줄 위치/여백 보정.
- sys031: 구속의 선명/흐림 효과, 아래 남아 있던 일본어 제거.

기존 대사 검수·영상 자막·전투조건 보정·캐릭터 이름판 유지. 폐기한 15장 자동 식자는 포함하지 않았습니다. 전체 ISO 비교에서 3개 계획 범위 외 모든 바이트가 기반판과 동일합니다. 실제 게임 검증은 아직 하지 않았습니다.

## 테스트

새 ISO로 다시 부팅한 뒤 게임 내 메모리카드 저장을 불러오세요. 이전 상태저장은 과거 텍스처가 남을 수 있어 이번 이미지 확인에는 권장하지 않습니다.
기존 CRC7502FF83 대화 표시 호환 패치를 그대로 사용하세요. 다른 PC에서는 동봉 호환패키지 안내에 따라 설치하세요. 카드·상태저장·에뮬레이터 설정은 변경하지 않았습니다.

1. 메뉴 하단 결정·취소·선택의 테두리와 투명도.
2. 출격 준비 메뉴의 선택/비선택 글자 위치, 잘림.
3. 전투 중 구속 표시의 흐림/선명 효과 위치와 원문 잔상 여부.

기반 영상 자막 미확정 구절 등의 한계는 이전 `../battle_condition_display_v1/먼저읽기.md`에 있습니다.
검증 보고서: `../../reports/user_ui_test_v1.json`.
''')
 for rp,asset_report in reports:
  asset_report['applied_assets']=asset_report.pop('pending_assets');asset_report.update(status='applied_to_iso',iso_built=True,iso_path=r['iso_path'],integration_report='reports/user_ui_test_v1.json');write_json(rp,asset_report)
  n=rp.stem.removeprefix('user_sys').removesuffix('_v1');write_json(ROOT/f'build/user_sys{n}_v1/report.json',asset_report)
  doc=ROOT/f'outputs/user_sys{n}_v1/먼저읽기.md';s=doc.read_text();s+='\n\n## 통합 완료\n\n위 적용 대기 안내는 완료되었습니다. `'+r['iso_path']+'`에 반영했습니다. 실제 게임 검증은 아직 하지 않았습니다.\n';doc.write_text(s)
 pf=ROOT/'localization/pipeline.json';p=json.loads(pf.read_text());p['latest_experimental_build']=dict(path=r['iso_path'],sha256=result['output_sha256'],pcsx2_sidecar=r['iso_path']+'.pcsx2',report='reports/user_ui_test_v1.json',runtime_verified=False);p['static_checks']['user_ui_test_v1_entire_iso_verified']=True;write_json(pf,p)
 hp=ROOT/'HANDOVER.md';s=hp.read_text();s=s.replace('## 최신 실행 ISO: 캐릭터 이름판 통합','## 이전 기반 ISO: 캐릭터 이름판 통합',1)
 for title in ['사용자 sys009 PSD','사용자 sys015 PSD 정렬 보정','사용자 sys031 구속 PSD']:s=s.replace('## 적용 대기: '+title,'## 준비 당시 기록 (아래 3장 모두 현재 ISO 반영 완료): '+title,1)
 section=f'''## 최신 실행 ISO: 사용자 UI 3장 중간 테스트 v1 (2026-09-20)

`{r['iso_path']}`
SHA-256: `{result['output_sha256']}`.

캐릭터 이름판 통합판 기반에 사용자 sys009/sys015/sys031 적용 완료. 아래 준비 당시의 ‘적용 대기/ISO 미수정’ 상태는 이 기록으로 대체. 대기 항목 3개 모두 반영. 기존 대사·영상·전투조건·캐릭터 이름판 유지. 3개 텍스처의 승인된 편집 영역 밖 픽셀 및 ISO 계획 범위 밖 전체 바이트 동일 검사 통과. 실제 게임 미검증. CRC7502FF83 sidecar/ZIP 동봉. `reports/user_ui_test_v1.json` 참조. 폐기한 15장 식자는 미포함.

''';hp.write_text(s.replace('\n\n','\n\n'+section,1))
 print(json.dumps(dict(iso=r['iso_path'],sha256=result['output_sha256'],verification=verified),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
