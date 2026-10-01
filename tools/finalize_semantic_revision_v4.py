"""Publish verified revision v4 documentation and compatibility package."""
import json,zipfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def write(p,x):(ROOT/p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
r=read('reports/semantic_revision_v4.json');pre=read('localization/semantic_revision_v4/preflight.json')
assert r['whole_iso_verification']['passed'] and r['whole_iso_verification']['all_unplanned_bytes_identical']
assert r['corrections']==pre['count']==21533
h=r['iso']['output_sha256'];iso=ROOT/r['iso_path'];side=Path(str(iso)+'.pcsx2')
m=json.loads((side/'manifest.json').read_text());assert m['iso_sha256']==h and m['patch_count']==34
patch=(side/'patches'/m['patch_filename']).read_bytes();assert hashlib.sha256(patch).hexdigest()==m['patch_source_sha256']
with zipfile.ZipFile(iso.parent/'PCSX2_대화표시_호환패키지.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(side.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(side))
(iso.parent/'SHA256SUMS.txt').write_text(h+'  '+iso.name+'\n')
(iso.parent/'먼저읽기.md').write_text('''# 대사 문맥 검수 v4

이번 ISO에는 기존 테이지 주요 이벤트 검수에 이어 다른 인물·마을·전투·개별 이벤트와 엔딩 대사 검수를 반영했습니다. v3 대비 6,158개 검수 단위, 중복 분기를 포함한 21,533개 저장 위치 수정입니다. 기존 이미지·레터링·시스템 번역과 v3의 아이템·스킬 수정도 포함합니다.

ISO를 PCSX2에서 새로 부팅하고 게임 내 메모리카드 저장을 불러오세요. 이전 상태저장에는 옛 대사 데이터가 남을 수 있습니다. 대화 표시에는 기존 SLPS-25854_7502FF83.pnach 패치가 계속 필요합니다. 다른 환경에서는 동봉한 호환 ZIP의 README를 참고하세요. 기존 검증 환경은 PCSX2 2.6.3·Software·16:9·와이드스크린 패치 켬입니다.

전체 ISO 계획 범위 밖 바이트 동일, 변경 RTB 254개 재읽기, 명령·분기·미수정 문자열 보존 확인. 인코딩·용량·줄 길이 검사 통과. 이번 대사의 실제 플레이 및 음성 대조는 아직 하지 않았습니다. 해석 불명확한 5개 단위는 임의 변경하지 않았습니다.

편집본: outputs/translation_review_20260920/applied_v4/structured_ko_reviewed_v4.tsv
검수 결과와 보류 목록도 같은 폴더에 있습니다.

SHA-256: `'''+h+'`\n')
p=read('localization/pipeline.json')
p['latest_experimental_build']=dict(path=r['iso_path'],sha256=h,pcsx2_sidecar=str(side.relative_to(ROOT)),report='reports/semantic_revision_v4.json',runtime_verified=False)
p['work_priority']='RTB 대사 읽기 검수 완료. 해석 보류 5단위, 실제 플레이·음성 대조, 전체 DB 및 이미지 간 용어 일관성 검수 남음.'
p.setdefault('static_checks',{})['semantic_revision_v4_entire_iso_verified']=True
p['semantic_revision']=dict(changes='localization/semantic_revision_v4/changes.jsonl',editable_tsv='outputs/translation_review_20260920/applied_v4/structured_ko_reviewed_v4.tsv',review_report='outputs/translation_review_20260920/applied_v4/검수결과.md',build_report='reports/semantic_revision_v4.json',corrections=21533,changed_units=6158,reviewed_units=13714,reviewed_locations=114299,pending_units=5,full_game_semantic_review=False,dialogue_readthrough_complete=True,runtime_verified=False,reviewed_scene_files=pre['reviewed_scene_files'])
write('localization/pipeline.json',p)
p=read('localization/review_remaining_20260920/progress.json');p.update(complete=True,semantic_readthrough_complete=True,pending_units=5,notes='Readthrough and confirmed corrections integrated in revision v4. Five ambiguous units retained, actual gameplay/voice verification not performed.');write('localization/review_remaining_20260920/progress.json',p)
hand=ROOT/'HANDOVER.md';s=hand.read_text();title,rest=s.split('\n',1)
section='''
## 최신 실행 ISO: 대사 검수 v4 (2026-09-20)

`'''+r['iso_path']+'`\nSHA-256: `'+h+'''`.

기존 v3 테이지 주요 이벤트 이후 나머지 RTB 대사 114,299개 저장 위치/13,714개 원문·기존번역 조합을 읽고 대조했다. 다른 인물 루트, 마을, 전투, 개별 이벤트·엔딩을 포함한다. 6,158개 단위/21,533곳/254개 RTB 수정. 인물 말투, 주체·부정·관용구 오역, 이름·쌍격 등 표기 보완. 5개 방언·운문 해석 불명확 단위는 기존 번역 유지. 대사 읽기 검수 완료와 전체 게임 번역 품질 보증은 다르며 전체 DB·이미지 용어 검수는 별도다.

- 입력: `localization/semantic_revision_v4/changes.jsonl`, `decisions.json`, `pending_context.json`, `preflight.json`.
- 도구: `tools/prepare_semantic_revision_v4.py`, `tools/build_semantic_revision_v4.py`, `tools/export_semantic_revision_v4.py`, `tools/finalize_semantic_revision_v4.py`.
- 편집본: `outputs/translation_review_20260920/applied_v4/structured_ko_reviewed_v4.tsv` (128,274행, 원문·ID·위치 보존). 수정내역, 전체대사 검수대본, 검수결과, 문맥확인보류 동봉.
- 정적 검사: 문자표 왕복·255바이트·한 줄36바이트 예산 통과. RTB 비문자 명령/분기·미수정 문자열 보존. ISO 전체 계획 밖 동일, 254멤버 재읽기 확인. RTB6+DB9+호환12 검사 통과.
- 기존 사용자 이미지·레터링·폰트·ELF 및 v3 DB 수정 유지. CRC7502FF83 호환 패치34곳 검사 및 sidecar/ZIP 동봉. 실제 플레이/음성 대조 미실시. 사용자 카드/상태저장/설정 무변경.
- 아래 v3 이하의 미검수 범위 표기는 당시 이력이다. 최신 실행·편집 기준은 v4.

'''
rest=rest.replace('## 최신 실행 ISO: 문맥 수정 v3','## 이전 실행 ISO: 문맥 수정 v3',1)
hand.write_text(title+'\n'+section+rest)
print('Finalized',r['iso_path'],h)
