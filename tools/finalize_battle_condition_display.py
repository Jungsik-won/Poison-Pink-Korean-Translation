"""Record the combined movie/lettering ISO as the current run target."""
import json
import shutil
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'build/battle_condition_display_v1'
r=json.loads((ROOT/'reports/battle_condition_display_v1.json').read_text())
assert r['installed'] and r['whole_iso_verification']['passed']
assert r['whole_iso_verification']['all_unplanned_bytes_identical']
assert r['movie_subtitles_preserved'] and len(r['replacements'])==9
iso=r['iso_path'];digest=r['iso']['output_sha256']
side=Path(str(ROOT/iso)+'.pcsx2')
manifest=json.loads((side/'manifest.json').read_text());assert manifest['iso_sha256']==digest
with zipfile.ZipFile(B/'PCSX2_대화표시_호환패키지.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(side.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(side))
shutil.copy2(ROOT/'build/movie_subtitles_v1/검수자막_편집자료.zip',B/'검수자막_편집자료.zip')

readme=f'''# 영상 자막 + 전투조건 표시 보정 통합판

실행 파일: `{Path(iso).name}`
SHA-256: `{digest}`

## 반영 내용

- 기존 대사 검수 v4와 사용자 이미지/레터링/시스템 번역 유지.
- 원본 MOVIE 13편: 대화·내레이션67개 + 엔딩/스태프롤 주제가82개 =149개 자막. 원본 음성 그대로. 기존 추출 MP4 재사용 없음.
- 승리조건/패배조건 제목 높이를 원본37.5픽셀과 같게 수정. 기존25.5/26픽셀에서 약44~47% 확대. 제목 폭은 각 글자의 개별 표시 칸 안에 유지.
- ‘주인공의 전투불능’과 ‘테이지의 전투불능’: 전체64픽셀 대신 게임이 실제로 읽는 위쪽 약40픽셀에 맞춰 배치. 하단 잘림 보정.
- 네 효과(기본·빨강·주황·검정)를 함께 수정. V3 작업PSD16개도 기존 폴더 안에서 갱신. 이전 작업은 V3의 `표시범위_크기보정전_보존.zip`에 보존.

## 실행과 검증 범위

새 ISO로 다시 부팅한 뒤 게임 내 메모리카드에서 불러오세요. 기존 상태저장에는 이전 이미지나 코드가 남을 수 있습니다. 대화 표시용 CRC7502FF83 패치가 계속 필요합니다. 기존에 설치한 같은 패치는 그대로 사용합니다. 다른 PC에서는 동봉 호환패키지 README에 따라 설치하세요. 사용자 카드·상태저장·설정은 변경하지 않았습니다.

영상 변환 및 ISO 전체 비교, 변경9개 텍스처 재읽기, UV/그림자/제목 관련7개 검사를 통과했습니다. 새 수정본의 실제 게임 화면 검증은 아직 하지 않았습니다.

## 자막에서 남은 확인

s09 주문 수식어와 주제가1절의 불분명한 술어 일부는 생략했습니다. 스태프롤 약172~178초는 잠정 번역입니다. 공식 가사집과 대조한 확정본은 아닙니다. 동봉 자막 자료의 `청취_확인필요.json`과 README 참고.

스태프롤은 이름을 가리지 않도록 원본 영상을 비율 유지한576×432로 축소해640×480 프레임 안에 넣고, 아래48픽셀을 가사 공간으로 썼습니다. 출력 해상도·프레임 수는 원본과 같고 재인코딩 구간에는 압축 손실이 있습니다.

검증 기록: `../../reports/battle_condition_display_v1.json`, `../../reports/movie_subtitles_v1.json`.
수정 PSD: `../../outputs/battle_lettering_work_v3/`.
'''
(B/'먼저읽기.md').write_text(readme)

v3=ROOT/'outputs/battle_lettering_work_v3/먼저읽기.md'
note='''

## 2026-09-20 실제 표시 범위·제목 크기 보정

승리조건·패배조건 제목은 원본과 동일한 높이로 보정했다. 주인공/테이지 전투불능 본문은 게임의 실제 UV가 위쪽 약40픽셀만 읽는 점을 반영했다. PSD 캔버스는 그대로지만 아래쪽 여백은 게임에 표시되지 않는다. 본문은 현재 원문/식자가 있는 위쪽 안전 영역(공통4배 작업 좌표 기준 대략 y=0~151)에 맞춰 편집할 것. 네 효과는 같은 공통 좌표에서 만들고, 패킹 시 각 효과의 실제 UV로 변환한다. 이전16PSD·PNG·manifest는 `표시범위_크기보정전_보존.zip`에 보관. 이번 대응의 실제 게임 화면 확인은 아직 하지 않았다.
'''
assert '## 2026-09-20 실제 표시 범위·제목 크기 보정' not in v3.read_text()
v3.write_text(v3.read_text()+note)

pfile=ROOT/'localization/pipeline.json';p=json.loads(pfile.read_text())
p['latest_experimental_build']=dict(path=iso,sha256=digest,pcsx2_sidecar=iso+'.pcsx2',report='reports/battle_condition_display_v1.json',runtime_verified=False)
p['static_checks']['battle_condition_display_v1_entire_iso_verified']=True
p['battle_condition_display_fix']=dict(report='reports/battle_condition_display_v1.json',textures=9,psds=16,source_movie_build='reports/movie_subtitles_v1.json',runtime_verified=False)
pfile.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')

hfile=ROOT/'HANDOVER.md';s=hfile.read_text();heading='## 최신 실행 ISO: 영상 자막 + 전투조건 표시 보정 v1 (2026-09-20)'
assert heading not in s
s=s.replace('## 최신 실행 ISO: 원본 영상 자막 v1','## 이전 기반 ISO: 원본 영상 자막 v1',1)
section=f'''{heading}

`{iso}`
SHA-256: `{digest}`.

사용자 게임 스크린샷에서 제목 축소/패배조건 하단 잘림 확인. 제목 실제 높이가 원본37.5 대비25.5/26이었던 식자 오류, 패배본문 UV 높이약40을 텍스처 전체64로 취급한 패킹 오류를 수정했다. 승리/패배 제목 원본 높이로 보정, 주인공·테이지 전투불능 두 문구를 실제UV 안으로 재배치. 네 효과×4문구=16PSD/9TIM2 수정. 원본 UPL/UV/팔레트/헤더/파일크기 변경 없음.

- 기존 `outputs/battle_lettering_work_v3` 안에 갱신, 이전16PSD/PNG/manifest/README는 `표시범위_크기보정전_보존.zip`에 검증 보존. 원문과 이전 작업 숨김 레이어 유지. 범위 밖{r['untouched_psds']}PSD 해시 동일.
- 원본 영상 자막v1 ISO 기반이므로 기존 대사검수v4 + MOVIE13편/149자막 유지. 주제가 잠정/생략 구절은 아래 영상 기록과 `청취_확인필요.json` 참조.
- 도구: `battle_workbench_v3.defeat_geometry()`에서 실제 UV사각형 산출; `build_battle_titles_euljiro.group_images()` 제목 원본높이 및 본문여백 보정. `tools/fix_battle_condition_display.py` 준비→`--install`→`--build`, `tools/finalize_battle_condition_display.py` 기록.
- 네 문구 저장후 기본/검정 IoU .927~.972, 검정기본피복 .961~.986. 7개 관련검사 통과. 전체ISO 계획범위밖 동일 및9멤버 재읽기 통과. MOVIE/대사/기타이미지 유지. CRC7502FF83/34곳 호환 sidecar/ZIP 동봉.
- **새 수정본 실제 게임 화면 검증 미실시.** 사용자 설정/카드/상태저장 무변경. 새로 부팅 후 게임내 저장 불러오기 권장.

'''
s=s.replace('\n\n','\n\n'+section,1);hfile.write_text(s)
print('Published combined movie and lettering build:',iso,digest)
