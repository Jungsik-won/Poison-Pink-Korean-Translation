"""Apply only the five approved character tabs to the last complete ISO."""
import json,shutil,zipfile
from pathlib import Path
from localization_pipeline import ROOT,sha,hed_tree,write_json
from iso_archive_stage import iso_inventory,exact,overlay
from ui_texture_codec import parse
import build_user_translation_import as verifier
BASE=ROOT/'build/battle_condition_display_v1/Poison Pink (Japan) - Korean movies and battle display v1.iso'
BASE_SHA='ca5069ad208cbbc7d063681daaa2fd89852bfd88f9ce5a8dbd04bd6cbc859040'
B=ROOT/'build/character_tabs_ko_v1'
ISO=B/'Poison Pink (Japan) - Korean character names v1.iso'

def main():
 r=json.loads((ROOT/'reports/character_tabs_ko_v1.json').read_text());assert r['status']=='prepared_not_applied'
 inv=iso_inventory(BASE);files={e['path']:e for e in inv['files']};patches=[];entries=[]
 with BASE.open('rb') as f:
  he=files['DATA/STATUS.HED'];de=files['DATA/STATUS.DAT'];f.seek(he['lba']*2048);members={e['path']:e for e in hed_tree(exact(f,he['size']))[0]}
  assert len(r['textures'])==5
  for n,row in enumerate(r['textures']):
   source=row['source'];assert source==f'STATUS/status/chr_cel/csl_tb{n}.tm2'
   data=(B/'textures'/source).read_bytes();assert sha(data)==row['compiled_sha256']
   e=members[source.split('/',1)[1]];assert len(data)==e['size'];pos=de['lba']*2048+e['offset'];f.seek(pos);old=exact(f,e['size'])
   assert sha(old)==row['source_sha256'],'Base tab differs from approved original'
   assert parse(old)['header']==parse(data)['header'] and parse(old)['palette']==parse(data)['palette']
   patches.append(dict(offset=pos,data=data,expected_sha256=sha(old)))
   entries.append(dict(source=source,offset=pos,size=len(data),before_sha256=sha(old),after_sha256=sha(data)))
 print('Building ISO: five character tabs only',flush=True)
 result=overlay(BASE,ISO,patches,BASE_SHA);assert iso_inventory(ISO)==inv
 print('Verifying entire ISO against base and five replacements',flush=True)
 verifier.BASE_HASH=BASE_SHA;verified=verifier.verify_stream(BASE,ISO,patches,result['output_sha256'])
 with ISO.open('rb') as f:
  for row in entries:f.seek(row['offset']);assert sha(exact(f,row['size']))==row['after_sha256']
 r.update(status='applied_to_iso',iso_built=True,iso_path=str(ISO.relative_to(ROOT)),base_iso=str(BASE.relative_to(ROOT)),base_iso_sha256=BASE_SHA,iso=result,whole_iso_verification=verified,replacements=entries,discarded_status_lettering_included=False)
 r.pop('pending_assets',None)
 write_json(B/'report.json',r);write_json(ROOT/'reports/character_tabs_ko_v1.json',r)
 (B/'SHA256SUMS.txt').write_text(result['output_sha256']+'  '+ISO.name+'\n')
 side=Path(str(ISO)+'.pcsx2');m=json.loads((side/'manifest.json').read_text());assert m['iso_sha256']==result['output_sha256']
 with zipfile.ZipFile(B/'PCSX2_대화표시_호환패키지.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(side.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(side))
 with zipfile.ZipFile(B/'PCSX2_대화표시_호환패키지.zip') as z:assert z.testzip() is None
 (B/'먼저읽기.md').write_text(f'''# 캐릭터 이름판 통합 ISO

실행 파일: `{ISO.name}`
SHA-256: `{result['output_sha256']}`

기존 영상 자막·대사 검수·전투조건 표시 보정판에 EBS 주시경체 Bold 캐릭터 이름판 5장(12명)만 추가했습니다. 이후 요청했던 STATUS 15장 을지로체 식자는 폐기했고 반영하지 않았습니다.

ISO 전체 비교에서 위 5개 텍스처 외 바이트가 기반 ISO와 동일함을 검증했습니다. 아카이브/ISO 크기·배치·원본 팔레트·텍스처 헤더를 유지했습니다. 실제 게임 화면 검증은 아직 하지 않았습니다.

새 ISO로 부팅하고 게임 내 메모리카드 저장을 불러오세요. 상태저장은 이전 이미지가 남아 있을 수 있습니다. 기존 대화 표시용 CRC7502FF83 호환 패치를 계속 사용하세요. 다른 PC에서는 동봉 호환패키지 설명을 따르세요. 사용자 메모리카드·상태저장·에뮬레이터 설정은 변경하지 않았습니다.

기반판 영상 자막의 청취 미확정 구절 등 한계는 `../battle_condition_display_v1/먼저읽기.md`에 기록되어 있습니다.
식자 PNG/PSD: `../../outputs/character_tabs_ko_v1`.
검증 기록: `../../reports/character_tabs_ko_v1.json`.
''')
 pf=ROOT/'localization/pipeline.json';p=json.loads(pf.read_text());p['latest_experimental_build']=dict(path=r['iso_path'],sha256=result['output_sha256'],pcsx2_sidecar=r['iso_path']+'.pcsx2',report='reports/character_tabs_ko_v1.json',runtime_verified=False);p['static_checks']['character_tabs_ko_v1_entire_iso_verified']=True;write_json(pf,p)
 h=ROOT/'HANDOVER.md';s=h.read_text();start=s.index('## 적용 대기: 캐릭터 선택 이름판 5장');end=s.index('## 최신 실행 ISO:',start)
 s=s[:start]+s[end:];s=s.replace('## 최신 실행 ISO: 영상 자막 + 전투조건 표시 보정','## 이전 기반 ISO: 영상 자막 + 전투조건 표시 보정',1)
 section=f'''## 최신 실행 ISO: 캐릭터 이름판 통합 v1 (2026-09-20)

`{r['iso_path']}`
SHA-256: `{result['output_sha256']}`.

기존 영상 자막·대사 검수·전투조건 표시 보정판에 `STATUS/status/chr_cel/csl_tb0~4.tm2` 5장/12명만 추가. EBS 주시경체 Bold, 원문 폭·높이에 맞춘 식자. 전체 ISO 비교 및 5멤버 재읽기 통과, 변경 범위 밖 모든 바이트 동일. 실제 게임 검증 미실시. CRC7502FF83 호환 패치 sidecar/ZIP 동봉. `reports/character_tabs_ko_v1.json` 참조.

후속 STATUS 15장 을지로체 작업은 사용자 요청으로 폐기했으며 포함하지 않음. 원본 추출 파일은 보존. 원본 영상 자막의 미확정 구절 등 기반판 한계는 아래 기록 유지.

'''
 s=s.replace('\n\n','\n\n'+section,1);h.write_text(s)
 readme=ROOT/'outputs/character_tabs_ko_v1/README.md';t=readme.read_text().replace('ISO 반영 대기','ISO 반영 완료');t+='\n\n## 통합 완료\n\n앞선 적용 대기 안내를 대체합니다. 캐릭터 이름판 5장은 `'+r['iso_path']+'`에 반영했습니다. 후속 STATUS 15장 식자는 폐기했습니다. 실제 게임 검증은 미실시입니다.\n';readme.write_text(t)
 print(json.dumps(dict(iso=r['iso_path'],sha256=result['output_sha256'],verification=verified),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
