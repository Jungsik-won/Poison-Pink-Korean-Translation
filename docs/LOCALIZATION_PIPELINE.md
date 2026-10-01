# Poison Pink 한글화 작업 파이프라인

**현재 최신 통합본:** `build/tutorial_11_user_v1/Poison Pink (Japan) - expanded user help.iso`. 사용자 제공 추가 도움말·미니게임 10장을 반영했고 GAME OVER 1장은 원본 유지했다. 기존 사용자 이미지도 모두 포함한다. [적용 기록](docs/TUTORIAL_11_USER_ARTWORK.md), `reports/tutorial_11_user_artwork.json` 참조. 아래 과거 빌드 안내보다 이 항목이 우선한다.

**2026-09-16 최신 빌드:** 사용자 도움말 14장과 기존 사용자 로고·타이틀·전투 메뉴를 포함한 `build/user_help_artwork_v1/Poison Pink (Japan) - user artwork and help.iso`. [적용 기록](docs/USER_HELP_ARTWORK.md)과 `localization/pipeline.json`의 최신 경로를 따른다. 도움말의 오역 6곳을 승인 범위에 따라 수정했고 전체 ISO 비교를 통과했다. 사용자 자산 17개는 이후 빌드에도 유지한다. 게임 실행 검증은 보류한다.

설정일: 2026-09-15. 기준 문서: [HANDOVER.md](HANDOVER.md).

## 후속 구현 현황

현재 단계: **[원본 전체 추출 완료](extracted/original/README.md)**. 번역은 보류하고 원문·이미지·원본 자산을 먼저 정리했다. 10,241개 아카이브 파일, 일반·내장 텍스처 4,034개, 글리프 2,016개, RTB 280개와 DB 3종의 문자열을 확보했다. 중간 ISO 13개는 복원 가능한 압축 차이 파일을 검증한 뒤 삭제했다. 원본 및 최신 도움말 ISO만 보존한다.

최신 보존 시험본: [튜토리얼 도움말 14장 통합본](docs/HELP_PAGES.md). 추가 번역과 게임·그림 검수는 현재 작업에 포함하지 않는다.

기반: [튜토리얼 24문장 시험본](docs/TUTORIAL_SLICE.md). 본문·질문 24개와 화자 23개 모두 화면 검수 통과. 한글 152자 추가 및 ID 2167 실행 출력, SYSTEM.DAT 재배치, 동일 빌드 양쪽 선택지, 이동·대기·적 턴과 두 지점의 상태 저장·총 3회 복원까지 확인했다.

후속: [전투 완료·본편 진행 저장과 새 부팅 로드](docs/TUTORIAL_BATTLE_RUNTIME.md) 통과. Metal 스킬 연출 충돌 후 같은 ISO의 Software 렌더러로 진행했다. 현재 시험용 설정은 Software이며, 시스템 데이터 저장과 본편 No.01 진행 저장을 구분한다.

- ISO 내부 50개 파일과 추출본의 크기/해시 일치 확인, LBA 목록 생성 완료.
- 11개 HED/DAT의 동일 크기 staging 구현 및 무변경 2,710,721,508바이트 일치 확인.
- 원본 글리프 2,016개 pair decode/encode 일치 및 실험 대상 외 2,013개 불변 확인.
- `テージ → 가나다` 진단 ISO 생성 완료. 전체 ISO 대조에서 의도한 픽셀 342바이트만 변경.
- 실제 시험은 별도 PCSX2/BIOS/메모리카드 사본을 둔 `build/runtime`에서 수행한다.
- PCSX2 2.6.3의 동일 대화창에서 실제 `가나다` 출력 확인. [캡처·재현 절차](docs/RUNTIME_PROBE.md).
- 최초 진단본에서는 상태 복원 뒤 대화창 유지가 확인되지 않았다. 최신 24문장 시험본은 일시정지 절차로 두 지점·3회 복원을 통과했다. 최초 실패 원인은 미확정이며 게임 내 저장 검증은 별개다.
- 후속 실험에서 일본어를 보존한 32글리프 추가와 동일 22바이트 한 문장 번역을 구현하고 실제 화면에서 확인했다. [한 문장 실험 결과·재현 절차](docs/KOREAN_SENTENCE_PROBE.md).
- 길이 증가·감소 실험본의 실제 한글 출력, 증가본 `はい`와 축소본 `いいえ` 분기, 축소본 전투 진입 확인. [실행 결과](docs/RTB_RESIZE_RUNTIME.md).
- RTB 280개 전체 필드 왕복과 명령·분기 경계 검증 완료. `rtb_codec.py`로 문자열 길이만 변경하는 편집을 구현했다. [형식과 근거](docs/RTB_FORMAT.md).
- DB 3종의 13개 표·1,689개 레코드 전체 파싱·왕복 및 9개 오프라인 문자열 변경의 수치 불변 검증 완료. [구조와 다음 주입 순서](docs/STATUS_DB_FORMAT.md).
- 패딩 내 파일 증가와 파일 축소를 지원한다. 일반 재배치, DB 표본 밖의 번역·추가 효과 검증, 전체 명령 의미 해석과 본번역은 다음 단계다.

추가 실행 명령:

```sh
python3 tools/iso_archive_stage.py iso-audit
python3 tools/iso_archive_stage.py noop-archives
python3 tools/font_pair_probe.py --iso
python3 tools/font_pair_probe.py --verify-iso
python3 tools/test_iso_font_stage.py
python3 tools/status_db_audit.py
PYTHONPATH=tools python3 -m unittest test_status_db_codec
```

staging/build 명령은 이미 있는 HED/DAT/ISO를 덮어쓰지 않는다. 위 생성 명령의 첫 실행은 이미 완료했다.
아래 P1/P2의 원래 작업 목록에서 일부가 완료된 상태이며, 전체 통과 범위는 각 보고서로 판단한다.

## 1. 방향 결정

**일본어 모드 유지 → 기존 렌더러의 글리프 pair 저장 방식 규명 → 소량 한글 표시 → 구조 파싱/재삽입 → 범위별 번역 확대.**

- `language=0`을 기준으로 진행한다. `language=6` 직접 인덱싱 주장은 잘못되었으므로 비교 실험 이상의 전제로 쓰지 않는다.
- 처음부터 2,350자/11,172자를 전부 넣지 않는다. 소규모 실험은 약 32자, 세로 테스트는 100~300자, 본번역은 실제 사용 문자 집합을 수집해 확장한다.
- 일본어 원문과 미번역 화면이 남으므로 기존 일본어 글리프/문장부호를 우선 보존한다.
- 미사용 KanTable 슬롯 후보는 5,544개지만, 유효한 입력 코드·예약 코드·범위 검사까지 통과한 슬롯 수와 같다고 간주하지 않는다.
- 화면에 노출되는 텍스트는 RTB, STATUS DB, ELF 문자열, UI 텍스처, 영상 자막으로 별도 추적한다. RTB만 완료해도 전체 한글화로 발표하지 않는다.
- 번역 기본 방침은 의미 보존, 인물별 말투 일관성, 메뉴 용어 통일이다. 이름·세계관 용어는 문맥 검수 후 용어집에 확정한다.

## 2. 바로 실행 가능한 부분

기본 audit/template/lint는 Python 3.8 이상 표준 라이브러리만 사용한다. 한 문장 폰트 실험에는 Pillow와 기록된 로컬 글꼴이 추가로 필요하다. 프로젝트 루트에서 실행한다.

```sh
# 원본 ISO/추출 파일 전체 해시 대조, 아카이브/폰트/기존 JSON 검수, 후보 재생성
python3 tools/localization_pipeline.py audit

# 검토용 양식 생성: 최초 생성은 이미 수행했다. 기존 파일이 있으면 덮어쓰지 않고 실패한다.
python3 tools/localization_pipeline.py template

# 검토 양식의 데이터 무결성 검사
python3 tools/localization_pipeline.py lint

# 파서·원문 검수 회귀 검사
python3 tools/test_localization_pipeline.py
```

`audit`는 큰 ISO까지 읽으므로 시간이 걸린다. 원본이 변경되면 중단한다.
후보 목록과 audit 보고서는 재생성하지만 번역 파일은 변경하지 않는다.
다른 작업 폴더에서도 도구 자체는 `__file__` 기준으로 프로젝트 경로를 찾는다.

| 파일 | 현재 용도 |
| --- | --- |
| `localization/pipeline.json` | 경로, 실험 전략, 길이 한도, 미통과 기술 검증 항목 |
| `localization/source.lock.json` | ISO 포함 원본 파일 크기/SHA-256 |
| `localization/rtb_candidates.jsonl` | 37,301개 원문 바이트 후보, 원본 위치/해시 |
| `localization/translations.jsonl` | 일본어 문자가 포함된 31,520개 후보의 검토·번역 양식 |
| `localization/glossary.csv` | 미확정 고유명사와 확정 용어 관리 |
| `localization/STYLE_GUIDE.md` | 한글 문체, 표기, 제어 토큰, 검수 규칙 |
| `reports/audit.json` | 원본 구조 및 기존 산출물 검수 결과 |
| `reports/translation_lint.json` | 마지막 번역 입력 검사 결과 |
| `localization/qa_matrix.csv` | 화면/기능 검증 체크리스트, 초기 상태 pending |

현재 `gates`는 기술 검증 상태를 기록하며 범용 빌드를 자동 허용하는 스위치가 아니다. 제한된 실험 결과는 `experimental_gates`에 별도로 기록한다.
`tools/korean_sentence_probe.py`는 동일 길이 실험, `tools/rtb_resize_probe.py`는 구조 파싱 후 검수한 한 문장의 길이 변경 실험이다. 후보 전체를 자동 번역·삽입하는 범용 빌드와 자동 증거 승격은 아직 없다.

## 3. 단계별 작업과 완료 기준

### P0. 원본 고정·자료 정리 — 정적 검수 완료

**입력:** 원본 ISO, 추출 폴더, 기존 조사 문서/도구.

**완료한 작업:** ISO 포함 SHA-256 고정, 11개 HED 트리 파싱, 44B 레코드 재직렬화 동일성,
파일 범위/비중첩/정렬 검사, 기존 JSON 결함 집계, ELF 주소 보정 및 원시 명령어 증거 저장.

**추가 완료:** ISO 내부 50개 파일과 추출본의 크기·해시 대조 및 LBA 목록 저장. 증거는 `reports/iso_inventory.json`이다.

### P1. 원본 그대로 재패킹하는 도구 — 동일 크기 staging 구현 완료

**담당 역할:** 아카이브/빌드 엔지니어.

1. HED 트리와 파일 인덱스를 그대로 보존하는 추출·재삽입 인터페이스를 만든다. basename만으로 파일을 선택하지 않는다.
2. 첫 버전은 기존 DAT 위치·패딩·파일 크기를 유지하고 교체 범위만 덮어쓰는 staging 방식으로 만든다.
3. 변경이 없는 빌드는 HED/DAT 바이트 전체가 원본과 같아야 한다. 리소스 payload만 같다는 검사는 부족하다.
4. 크기 확장 버전은 현재 관측된 `0x4000` 정렬, HED 디렉터리 인덱스/크기, 파일 오프셋/크기, timestamp, 미수정 파일 해시를 보존한다.
5. ISO 재빌더는 파일 순서/LBA 의존 여부를 조사한다. 파일 시스템에 재패킹 폴더를 단순 복사해도 부팅된다고 가정하지 않는다.

**통과 기준:** 무변경 빌드의 HED/DAT 전체 해시 일치 → 원본과 재구성 이미지의 타이틀/새 게임/로드/전투 진입 비교 통과.
변경 허용 범위와 diff 보고서를 남긴다. ISO 전체 해시는 메타데이터 변경 가능성을 별도로 설명한다.

### P2. 폰트·입력 코드 소규모 실험 — 152자 추가와 ID 2167 실행 확인

**담당 역할:** 폰트/엔진 분석.

1. 실제 가상주소로 폰트 초기화, 코드 변환, 글리프 선택, 복사/캐시 업로드 루틴을 추적한다.
2. 일본어 코드의 189 기반 전체 범위별 계산을 구현하고 실제 테이블 및 일본어 샘플과 대조한다.
3. 글리프 2개를 공유하는 288B pair를 비대칭 패턴으로 바꿔 홀수/짝수, 픽셀 방향, 투명도, 계조를 확인한다.
4. 확장 전에는 원본 크기의 사본에서 제한된 일본어 슬롯을 임시 교체해 `가나다라마바사`, 겹받침, 숫자, 기호를 표시한다.
5. 폰트 파일의 증가 없이 표시가 확인되면 유효한 미사용 코드 슬롯을 선별하고 한글 글리프를 추가한다.
6. 글꼴 파일의 사용·재배포 조건, 파일 해시, 래스터라이저 버전, 크기/기준선/계조 설정을 기록한다. 라이선스가 정해지기 전 특정 외부 글꼴을 임의 배포하지 않는다.
7. 작은 집합 → 100~300자 → 본문 사용 문자 집합 순으로 메모리/캐시 스트레스 검사를 한다.

**산출물 목표:** `font_spec.md`, `glyph_mapping.json`, `encoding_tests.json`, 소규모 실험 이미지와 화면 캡처.

**통과 기준:** 모든 실험 코드가 지정 글리프를 출력, 짝수/홀수 간 간섭 0, 기존 일본어/ASCII 유지,
혼합문/개행/구두점 정상, 저장·로드와 전투 후 글리프 캐시 정상, 확장 시 메모리 오류 없음.
통과 후에만 `font_pair_layout_runtime`, `font_capacity_runtime` 증거를 기록한다.

### P3. RTB·DB 구조 확정 — RTB와 DB 전체 필드 파싱·왕복 완료, 추가 실행 검증 진행

**RTB 작업:**

1. 280개 파일의 심볼/소스/타입/명령 구간을 모두 파싱하고 미해석 바이트를 보고한다.
2. opcode별 크기, 태그, 문자열 길이 형식, 함수 인자와 호출 경계를 확정한다.
3. 현재 후보 ID를 유지하면서 `dialogue/speaker/choice/ui/nontext`로 분류한다. 화자는 호출 인자/흐름으로 판별한다.
4. 공백 문자열·반각만 있는 문자열·ASCII 메뉴·디코딩 실패 7개도 별도 검토한다. 초기 일본어 필터로 누락된 후보를 버리지 않는다.
5. 원문 parse→serialize 결과를 원본과 전체 바이트 비교한다.
6. 길이 동일/증가/감소를 각각 한 건씩 적용한다. 분기 양쪽, 루프, 선택지, 함수 반환을 실행 검증한다.
7. 점프 단위가 명령 인덱스인지 바이트인지 디스패처 근거를 남긴다. 바이트 기준이면 모든 관련 참조를 재계산한다.

**DB 현재:** 세 파일 모두 정확한 EOF와 전체 바이트 왕복을 통과했다. 13개 표의 1,689행, 문자열 필드 1,941개를 분리했으며, 9개 오프라인 길이 변경 실험에서 수치·ID를 보존했다. [보고서](reports/status_db_audit.json). 후속 5개 아이템·5개 스킬 표본에서 번역 표시와 공격·회복·소모품 사용, 빌드 간 게임 저장 로드를 확인했다. 추가 상태 효과·장비 교환은 QA037로 남겼다.

**DB 작업:**

- PPITEM/PPSKILL/PPPARAM 각 로더를 추적하고 문자열 경계/패딩/스탯/후행 데이터를 확정한다.
- 0이 나오는 동안 건너뛰는 방법을 폐기한다. 값이 0인 스탯과 문자열 종결을 구분해야 한다.
- declared count뿐 아니라 ID/레코드/파일 끝까지 검증한다. 오류 대체 디코딩을 성공으로 처리하지 않는다.
- 원본 필드 바이트를 모두 보존하고, 무변경 직렬화 동일성 및 텍스트 외 필드 불변을 검사한다.

**통과 기준:** RTB 전체 명령 경계 확인, 원문 roundtrip 일치, 수정 후 제어 흐름 정상.
DB 세 파일 모두 누락·오탐 없이 파싱하고 원문 왕복 일치. 각 실패는 해당 파일군의 번역 주입을 막는다.

### P4. 작은 구간을 끝까지 한글화 — 튜토리얼 24문장 부분 통과

**현재:** 본문·질문 24개, 화자 2종의 23개 표기를 번역해 모두 화면 검수했다. 초기 양쪽 선택지와 두 상태 저장 지점을 확인했고, Software 렌더러에서 스킬·포획·튜토리얼 완료와 본편 No.01 저장·새 부팅 로드도 통과했다. 후속 아이템 5개·스킬 5개의 16개 문자열 표시와 바람/회복/약초 사용·저장/로드도 통과했다. 추가 상태 효과·장비 교환(QA037), 도움말 그림·공통 UI 번역과 더 넓은 회귀가 남아 있어 P4 전체는 미완료다.

**범위:** `t00_0010.rtb`를 우선 조사 후보로 삼되 실제 진입 조건을 확인해 고른 1개 튜토리얼/이벤트.
화자 3~5개, 본문 20~30개, 선택지 2~3개, 아이템/스킬 이름 각 5개 정도를 포함한다.
해당 파일에 이 요소가 없으면 재현 가능한 인접 이벤트로 보완하고 사용한 파일 목록을 기록한다.

**검증:** 부팅 → 이벤트 → 선택지 양쪽 → 전투 → 스킬/아이템 → 저장 → 재로드.
최장 문장, 겹받침, 괄호/숫자, 영문 혼합, 빈 문자열, 줄바꿈을 포함한다.
255바이트 이내라도 창 폭을 넘을 수 있으므로 실제 렌더링 폭/행 높이를 측정한다.
문장 길이 조절은 의미를 유지하며 수행하고, 대사 분할은 이벤트 흐름 변경이 검증된 경우에만 한다.

**통과 기준:** 오류/깨짐/잘림/선택지 오작동 0, 동일 조건에서 원본과 기능 비교 가능, 재현용 저장과 캡처 보유.

### P5. 본번역 — P4 통과 후 확대

순서: 공통 UI/용어 → 검수된 아이템·스킬 → 튜토리얼 → 루트/이벤트별 시나리오 → 도감 → 잔여 UI/ELF/텍스처/영상.
이는 구현 의존성을 고려한 순서이며 도감 설명을 기존 오탐 JSON에서 번역하지 않는다.

- 중복 원문은 번역 메모리 후보로 연결하되 화자·장면·선택지 맥락이 다르면 따로 번역한다.
- 상태: `unreviewed → draft → reviewed`; 리소스명/디버그 등 제외 대상은 `exclude`와 사유를 기록한다.
- `reviewed`는 target, 확정 role, reviewer를 요구한다. 문맥·말투·용어집 검수와 화면 검수를 별도로 추적한다.
- 용어집은 `pending/approved`로 운영한다. 승인되지 않은 이름을 대량 자동 치환하지 않는다.
- 번역률은 구조·역할 검수를 거쳐 확정된 번역 대상만 분모로 계산한다.

### P6. 자동 빌드·번역 QA — 구현 예정

목표 명령 흐름:

```text
verify-source → parse → validate-catalog → collect-glyphs → encode
→ font-build → inject → repack → static-verify → iso-build → runtime-QA
```

빌드에서 반드시 막을 항목:

- 기준 파일/원문 해시 불일치, 중복·없는 ID, 겹치는 교체 범위.
- 미분류/미검수 문자열의 삽입, 리소스 경로·심볼·제어 토큰 변경.
- 매핑되지 않은 문자, 비정규화 한글, 유효하지 않은 게임 코드, 왕복 인코딩 실패.
- 실제 게임 인코딩 결과의 리터럴 길이 255바이트 초과. UTF-8 길이나 Python 문자 수로 판단하지 않는다.
- 글리프 ID/table 범위 초과, 폰트 용량 상한 초과, 창별 측정 폭/줄 수 제한 초과.
- 비텍스트 바이트·스탯·미수정 리소스 해시 변경, 잘못된 HED 범위/정렬, 누락 파일.

현재 lint는 ID/원문, 상태, NFC, 일부 제어문자 및 `@name`/`%...` 형태 토큰 변화와 구조상 오탐 23개 후보의 번역 작성 여부를 검사한다. 제외 목록은 catalog 해시에 묶이며, 오래된 목록은 오류로 처리한다.
**실제 인코딩 길이, 전체 제어문법, 용어집 강제, 픽셀 너비, 역할의 진위는 아직 검사하지 않는다.**
따라서 성공해도 `build_ready=false`를 유지한다.

### P7. 전체 회귀와 배포 — 구현 예정

- 모든 루트/분기, 대화/선택지, 튜토리얼, 상점/장비/스킬/도감, 컨트롤러·메모리카드 오류 화면을 점검한다.
- 새 게임/기존 세이브, 반복 저장·로드, 장시간 전투와 장면 전환, 많은 글리프 동시 출력 상태를 확인한다.
- PCSX2 버전/설정, OS, 이미지 해시, 재현 세이브, 입력 순서, 화면 캡처를 기록한다. 실기 미검증이면 범위를 표시한다.
- 영상 자막/UI 텍스처는 디코딩 성공과 다시 삽입 가능한 인코딩 성공을 따로 확인한다.
- 배포물은 원본 해시를 검사하는 차분 패치, 적용 도구/설명, 지원 버전, 번역 범위, 알려진 제한, 변경 이력으로 구성한다.
- 원본 ISO나 원본 전체 리소스를 배포물에 포함하지 않는다.
- 깨끗한 원본에서 패치를 적용해 기대 결과 해시와 실행 검증이 재현되어야 한다.

## 4. 다음 작업 묶음

1. 완료: Software 설정에서 스킬·포획·장벽 해제와 튜토리얼 완료, 본편 No.01 저장 후 새 부팅의 게임 내 로드. 다음 실행은 [검증 설정](docs/TUTORIAL_BATTLE_RUNTIME.md)을 사용하고 Metal 충돌 기록을 보존한다.
2. 완료: DB 전체 구조 파싱·왕복과 아이템 5개·스킬 5개의 한글 표본 빌드·16개 문자열 화면 검수. 바람 공격·회복 마법·약초 사용과 No.02 저장·최종 빌드 새 부팅 로드를 확인했고 화염·암흑 시전도 추가 검증했다. 다음은 QA037의 공포 부여/수면·물리 이상 해제와 장비 교환을 보완한다. [실행 결과](docs/STATUS_SLICE.md).
3. 전투 메뉴 9종과 첫 도움말의 위치·형식 분석 및 시험 주입을 완료했다. ELF 행동 제목·공통 선택지 15곳의 참조/용량 검증과 시험 주입도 완료했다. `sys011` 3종·상태 제목·개별 명령명도 폰트 렌더링으로 주입했고 표본 실행은 [후속 결과](docs/UI_REMAINING.md)를 따른다. `ev136`~`ev149` 14장 번역·주입과 5장 실행 표시는 [도움말 결과](docs/HELP_PAGES.md)를 따른다. 사용자가 나머지 그림 검수를 뒤로 미뤘으므로 다음은 RTB 본문 번역이다. 두 분류와 쌍격 잔여 QA도 보류 상태로 보존한다. 세부 계약은 [UI_PIPELINE](docs/UI_PIPELINE.md)을 따른다.
4. 151개 사용 한글 이외의 겹받침·기호·숫자 혼합과 더 큰 글자 집합을 시험한다. 장시간 전투·장면 전환으로 캐시 안정성을 검사한다.
5. 각 RTB 명령의 의미와 반복·반환 경로, 다른 루트와 향후 빌드 간 저장 호환성 검증을 확장한다. 위 기능·화면 검증을 모두 통과한 뒤 P4를 완료하고 본번역을 확대한다.

P1~P3의 기술 작업은 독립적으로 나누어 진행할 수 있지만, 본문 대량 번역·파일 크기 확대는 각 완료 기준을 통과한 후 진행한다.

## 전체 추출 및 과거 ISO 복원

```sh
python3 tools/extract_all.py --output extracted/original_next
python3 tools/verify_extraction.py --output extracted/original_next
```

기준은 원본 잠금 파일이다. 최신 번역 ISO에서 원문을 추출하지 않는다. PNG와 원본 TIM2를 함께 보관한다.
검증된 RTB/DB 문자열과 미검수 ELF/바이너리 후보를 구분하고 모든 target을 비워 둔다.
전체 목록은 `extracted/original/files.tsv`, `images.tsv`, `text/*.jsonl`과 `text/*.tsv`다.

과거 빌드에 의존하는 도구와 테스트는 필요한 ISO를 먼저 복원한다. 예:

```sh
python3 tools/iso_retention.py restore --path 'build/ui_remaining/Poison Pink (Japan) - UI titles.iso'
```

삭제 목록·원본/대상 해시·복원 검증 기록은 `reports/iso_retention.json`에 있다. 완료된 이전 번역,
소규모 바이너리 산출물, 로그, 화면 증거, 상태 파일은 삭제하지 않았다.

## 2026-09-16 사용자 제작 타이틀 적용

사용자 PNG 2장 적용본이 최신 빌드다. `localization/pipeline.json`의 `latest_experimental_build`와 [타이틀 적용 기록](docs/TITLE_ARTWORK.md)을 따른다. 기존 도움말 v7 위에 두 텍스처만 적용했으며 전체 ISO 정적 비교를 통과했다. 화면·게임 검증은 계속 보류한다.

## Latest integrated build: user title and battle menu (2026-09-16)

ISO: `build/battle_menu_artwork_v1/Poison Pink (Japan) - custom title and battle menu.iso`

SHA-256: `d116694d374ef4d1c657ccd0010f32e94dc9349d194f7e8b175781d06d8e4d97`

Includes the user logo, title menu (load/prologue), and reviewed battle-menu sheet. Three texture ranges only: 89,259 changed bytes; battle-menu alpha unchanged. The title textures match the previous user build exactly. The previous title ISO was absent, so this build applies all three images to help_pages_v7. Runtime verification remains deferred. See [details](docs/BATTLE_MENU_ARTWORK.md) and `reports/battle_menu_artwork.json`. This supersedes older latest-build paths below.
