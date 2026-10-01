# 스킬 분류·상태·명령 제목 한글화

2026-09-15. 앞선 제목 v2에 남아 있던 그림 제목과 개별 명령 문장을 보완한다.
사용자가 **파이썬 폰트 렌더링으로 진행**을 선택해 결정적으로 생성하는 경로로 전환했다.

## 번역 범위

| 대상 | 번역 | 조각/문자열 수 |
| --- | --- | --- |
| sys011 | 액티브 스킬, 마법 스킬, 마신 소환 | 이미지 3조각 |
| sys015 | 상태 | 이미지 1조각 |
| sys000 | 재행동, 쌍격의 보조·선택 강조·비활성 표시 | 이미지 6조각 |
| ELF 명령 제목 | 재행동, 쌍격 | 문자열 2곳 |
| ELF 명령 안내 | 대상 선택 2문장, 재행동 종료·취소 질문 | 문자열 4곳 |

입력은 [ui_remaining.json](../localization/ui_remaining.json)에 원문·좌표·UAD 번호·원본 해시·
폰트 해시·색·여백·번역문을 함께 기록한다. 일본어 모드와 기존 사용자 저장을 유지한다.

## 렌더링과 주입 계약

- 도구: `tools/ui_font_artwork.py`. 기존 Noto Sans KR Regular 파일과 SHA-256을 사용한다.
- 4배 크기로 글자를 그린 뒤 고정 크기로 축소한다. 실제 글자 경계가 안전 여백을 넘으면 거부한다.
- 스킬 제목은 실제 RGBA 투명 배경 위에 그린다. 투명·반투명·불투명 픽셀이 모두 생성된다.
- 명령 조각은 원본 테두리를 남기고 내부만 지운 뒤 선택 상태별 원본 팔레트 색으로 그린다.
- 상태 조각은 원본의 빈 제목 띠에서 같은 크기의 배경을 가져온다. 해당 사각형 안에서만 변경한다.
- `ui_slice.py`가 원본 팔레트 인덱스로 컴파일한다. sys011과 sys015에는 알파를 함께 비교한다.
  원시 GS 팔레트·TIM2 헤더·UAD 전체 및 승인 사각형 밖 픽셀은 바꾸지 않는다.
- 기존 번역 메뉴 25조각, 첫 도움말, 이전 ELF 15곳·RTB·DB는 그대로 유지한다.
- ELF는 `.sdata` 명령 이름과 `.rodata` 안내 문장을 고정 용량 안에서 바꾼다.
  원본 포인터 참조·명령어·NUL 경계·주소·길이를 확인하며 초과하면 거부한다.
- 한글 10자(릭·소·쌍·재·참·취·칠·캐·택·터)를 추가해 총 2,212글리프다.
  이전 2,202글리프와 기존 테이블 값을 보존하고 SYSTEM의 기존 패딩만 사용한다.
- 일반 도구는 홀수 개 문자를 추가할 때 마지막 짝을 빈 글리프로 채운다. 빈 글리프에 문자 코드를
  할당하지 않으며, 짝의 실제 문자와 기존 글리프가 손상되지 않는 것을 별도 테스트했다.

생성 PNG는 `build/ui_remaining/artwork/sys000.png`, `sys011.png`, `sys015.png`다.
동일 입력으로 재생성한 바이트를 비교하고 다른 내용의 기존 PNG는 덮어쓰지 않는다.
앞선 image_gen 시안은 이번 입력으로 쓰지 않는다.

## 재현

```sh
python3 tools/ui_font_artwork.py --review localization/ui_remaining.json
python3 tools/ui_titles.py --review localization/ui_remaining.json --report reports/ui_remaining.json --output-dir build/ui_remaining_next --prepare-only
python3 tools/ui_titles.py --review localization/ui_remaining.json --report reports/ui_remaining.json --output-dir build/ui_remaining_next
PYTHONPATH=tools python3 -m unittest test_ui_remaining test_ui_titles test_ui_slice
```

관련 전체 테스트 55개 통과. 투명도·렌더링 재현성·사각형 밖 보존·문자열 용량·포인터·명령어·
기존 제목 유지·홀수 글리프 패딩을 검사한다. 빌드와 실행 검증 결과는 아래에 별도로 기록한다.


## 최종 빌드와 실행 결과

- ISO: `build/ui_remaining/Poison Pink (Japan) - UI titles.iso`
- SHA-256: `4ddfba66efddfadf8f4be2b5b55e9b19644a65af4c556d9d4c4a05e214b18796`
- 바탕: 제목 v2 `aa1f65d793a00a97310e94ac03ef3b796f7379d107973e5927a8ad5b8fcfeca6`.
- 전체 ISO 독립 대조: **20,084바이트 변경**, 크기 4,245,454,848B·모든 파일 위치 유지.
- 정적 보고서: [ui_remaining.json](../reports/ui_remaining.json).
- 실행 보고서: [ui_remaining_runtime.json](../reports/ui_remaining_runtime.json).
- PCSX2 CRC **C6C842C3**, Software·MTVU 설정. 원본과 완료된 이전 빌드는 보존했다.

확인한 실행 범위:

1. 상태 파일 없이 새 부팅 → 기존 No.02 로드 → 출격 확인 → 본편 첫 전투.
2. `마법 스킬`이 투명 배경 위에 정상 표시된다. 라키·테이지의 기존 한글 마법 이름/설명도 유지된다.
3. 상태 창에 `상태`가 표시되고 닫기·대기·다음 유닛 전환이 정상이다.
4. 명령 목록의 `재행동`·`쌍격` 표시, 재행동 선택 강조를 확인했다.
5. 재행동 상단 제목, 대상 선택 안내, 취소 질문, 종료 질문의 ELF 문자열 4곳을 확인했다.
6. 취소 질문의 아니요는 대상 선택으로, 예는 명령 목록으로 돌아간다.
7. 라키를 선택하자 실제 추가 행동이 시작됐다. 라키의 대기를 마치니 후보 수가 2/2→1/2로 줄었다.
8. 이때 종료 질문의 아니요는 남은 대상 선택으로, 예는 명령을 끝내고 테이지로 돌아갔다.
9. 같은 ISO의 상태를 복원해 원래 대상 선택과 2/2 후보로 돌아왔다. 이후 다른 화면에서 같은 상태로
   다시 복원했다. 총 2회 복원 확인, 진행 카드 두 개의 SHA-256은 전후 동일하다.

현재 라키·테이지에게는 마법 분류만 나타났고 L1/오른쪽 입력도 다른 분류를 보여주지 않았다.
**액티브 스킬·마신 소환은 그림/좌표/알파 검수와 주입까지만 완료했다.** 해당 분류가 있는 유닛·
저장 지점에서 실제 표시 확인이 필요하다. 쌍격은 현재 조건에서 비활성으로, 입력해도 대상 선택으로
들어가지 않았다. 따라서 쌍격 ELF 제목·안내 2곳과 실제 발동은 미검증이다. 이미지 10개 모든 변형의
실행 조건을 각각 강제로 만들었다고 주장하지 않는다.

캡처 이름 `remaining-active.png`는 L1 전환 시도이며 실제 액티브 스킬 화면이 아니다.
`remaining-finish-question.png`는 대상을 고른 직후 라키 명령 메뉴다. 실제 종료 질문은
`remaining-finish-confirm.png`다. 실행 보고서는 파일 이름보다 직접 확인한 화면 내용을 따른다.

### 현재 재현 지점

- 이 단계 종료 시 PID **63705**를 재행동 시작 상태(2/2 후보)에서 일시정지했다. 후속 도움말 검증을 위해 해당 프로세스는 종료했으며, 아래 상태 사본은 보존했다.
- 검증된 상태 사본: `build/ui_remaining/evidence/reaction-start.p2s` (8,025,235B).
- 로그·설정: `build/ui_remaining/evidence/runtime.log`, `PCSX2.final.ini`.
- 상태 저장은 잠깐 멈춰 수행하고, 재개 후 캡처했다. 마지막 정지에서는 F8을 누르지 않았다.
- 상태 파일은 이 ISO의 해시와 함께 식별한다. 다른 빌드의 상태를 섞어 검증하지 않는다.

![마법 스킬·기존 DB 번역](../build/status_slice/evidence/remaining-magic.png)

![한글 재행동 종료 질문](../build/status_slice/evidence/remaining-finish-confirm.png)

## 당시 다음 파이프라인 (후속 결과는 HELP_PAGES.md 참조)

1. **튜토리얼 도움말 ev136~ev149**: 원문 본문 전사 → 수치·조건·용어 검수 → 폰트 렌더링 →
   기존 팔레트/승인 사각형 주입 → 실제 페이지별 캡처. 설명 그림과 조작 기호는 별도 승인 영역으로 다룬다.
2. **표시 조건이 필요한 잔여 QA**: 액티브 스킬·마신 소환 분류가 있는 유닛/저장 지점,
   쌍격 가능 전투 배치 확보 후 표시와 동작 검증. 지금 완료한 번역을 다시 제작하지 않는다.
3. **출격·거점/조작 안내**: sys015의 나머지 문구, sys040, sys009/sys027, 장비·상점 제목.
4. QA037 상태 효과·장비 교환, QA044 유효 대상 열기/포획은 유지한다. 전체 P4는 미완료다.

후속 도움말 14장 주입과 사용자 요청에 따른 그림 검수 보류는 [HELP_PAGES.md](HELP_PAGES.md)를 따른다.
