# 아이템·스킬 한글 표본 시험

2026-09-15. 아이템 5개·스킬 5개, 총 16개 문자열을 번역했다.

후속 검증에서 같은 DB 최종 ISO의 암흑·화염 시전도 확인했다. 암흑은 적 HP50→27,
화염은 HP27→-42 및 구속 연출로 진행했다. [추가 회귀 기록](../reports/status_slice_regression.json).
이후 전투 메뉴·첫 도움말을 추가한 최신 시험본은 [UI 파이프라인](UI_PIPELINE.md)을 따른다.

## 빌드

- 최종 ISO: `build/status_slice_v2/Poison Pink (Japan) - status slice.iso`
- SHA-256: `3b4d9bf5a74233a3c2d60b65b5788513702cc52f3b099d4b6f1fab310536bc9f`
- 원본 ISO의 계획된 변경만 존재함을 전체 바이트 대조로 확인했다.
- 기존 튜토리얼 24문장·23개 화자, 일본어 글리프와 이전 2,168개 글리프를 보존했다.
- 한글 28자를 추가해 총 2,196개, 최대 ID 2195다. 사정거리 화살표는 원본 게임 글리프를 유지한다.
- PPITEM 12,918→12,916B, PPSKILL 23,969→23,941B. 문자열 외 모든 필드와 다른 STATUS 멤버는 보존했다.
- SYSTEM.DAT의 ISO 재배치 폭은 기존과 같은 32,768B다. STATUS 파일 시작 위치는 모두 유지했다.
- 번역 목록: `localization/status_slice.json`. 정적 검증: `reports/status_slice.json`.
- 관련 테스트 44개가 통과했다.

## 표본

| 종류 | 원문 | 번역 |
| --- | --- | --- |
| 아이템 | 短弓 | 단궁 |
| 아이템 | 初級魔導書 | 초급 마도서 |
| 아이템 | 革の鎧 | 가죽 갑옷 |
| 아이템 | ローブ | 로브 |
| 아이템 | 気付けの薬草 | 각성 약초 |
| 스킬 | パルフランマ | 파르플란마 |
| 스킬 | パルエント | 파르엔토 |
| 스킬 | パルグレド | 파르그레도 |
| 스킬 | レスアクア | 레스아쿠아 |
| 스킬 | クラアクア | 클라아쿠아 |

원문이 없는 장비 설명은 채우지 않았다. HP, 속성, 대상, 효과, 사정거리의 수치와 상하 기호를 보존했다.
전투 상단 설명창은 개행을 무시하므로, 최종본에는 ` / ` 구분자를 넣었다.
초기 비교본 `build/status_slice/`은 보존하며 최종 실행 결과는 `build/status_slice_v2/` 기준으로 판정한다.

## 실행 검증

최종 ISO에서 **16개 문자열 모두 실제 화면 표시·잘림 없음**을 확인했다. PCSX2 2.6.3 Software, MTVU 사용.
검증 근거: [실행 보고서](../reports/status_slice_runtime.json). QA031~036 통과, 추가 회귀 QA037 대기.

| 검증 | 확인한 결과 |
| --- | --- |
| 장비 4개 | 초급 마도서·로브·단궁·가죽 갑옷 표시. 테이지 ATK42/DEF24/HP100, 루티카 ATK41/DEF23/HP89가 원본과 일치 |
| 스킬 5개 | 이름·설명·속성·사정거리 기호가 표시됨. 설명 구분자도 정상 |
| 바람 마법 | 적 C HP80→50, 사용 가능 횟수3→2, 라키 EXP0→17, 다음 턴 정상 |
| 각성 약초 | 테이지 HP80→100, 약초3개→2개. 사거리 밖 대상은 거부, 인접 이동 후 사용 성공 |
| 회복 마법 | 라키 HP90→103, 루티카 EXP0→11, 전투 복귀 정상 |
| 게임 내 저장/로드 | 초기 DB 시험본에서 No.02(000:08)를 생성. 최종 DB 시험본을 상태 파일 없이 새 부팅해 No.02를 불러오고 한글 장비·능력치 확인 |
| 에뮬레이터 상태 복원 | 최종 ISO에서 일시정지 상태 저장·복원 1회. 라키 HP103과 상태 화면 유지 |

![새 부팅 로드 후 한글 장비](../build/status_slice/evidence/final-loaded-teige.png)

![최종 스킬 설명](../build/status_slice/evidence/final-skill-dark.png)

![사용 후 약초 두 개](../build/status_slice/evidence/final-herb-count-2.png)

### 남은 검증 범위

- 최초 실행에서는 화염·암흑 시전을 유도하지 않았으나 위 후속 검증에서 확인했다. 공포 부여와 수면/물리 이상 해제는 아직 미검증이다.
- 장비 이름·선택 화면·저장된 장비 능력치는 확인했지만, 다른 장비와의 교환은 미검증이다.
- 약초·회복 마법은 최대 HP에 도달했으므로, 최대치에 막히지 않은 원래 회복량을 실측한 것은 아니다.
- 회복 마법 잔여 횟수는 재확인하지 않았다. 바람 스킬 횟수와 약초 수량은 각각 확인했다.
- 본편 첫 전투를 끝까지 완료한 결과는 아니다. 이전 튜토리얼 전투 완료는 튜토리얼 빌드의 별도 증거다.
- 전체 DB·UI·도움말과 P4 전체 완료, 일반적인 빌드 간 상태 파일 호환성을 주장하지 않는다.

### 보존 자료와 현재 실행

- 원본 카드 사본: `build/status_slice/evidence/memcards-before/`.
- No.02 저장 후: `memcards-saved/`, 최종 실행 후: `memcards-final/`(모두 같은 evidence 아래).
- 이전 No.01에는 저장을 덮어쓰지 않았다. No.02 생성 후 슬롯 목록에서 기존 No.01이 남아 있음을 확인했다.
- 재현 상태: `build/status_slice/evidence/final-after-heal.p2s`. **위 최종 ISO와 PCSX2 2.6.3 조합에서만 사용한다.**
- 설정: `build/status_slice/evidence/PCSX2.final.ini`. 로그: `status-slice-v2.log`.
- 실행 PID 59642는 회복 검증 후 상태 화면에서 일시정지했다. Space로 재개한다.
- 상태 파일 경로 설정은 기존 `build/tutorial_slice/sstates/`를 가리켰다. 새 상태를 위 evidence 파일로 별도 복사했으며 이전 슬롯 백업도 PCSX2가 남겼다.
- Python 3.8 표준 ZIP 검사는 상태 파일의 압축 방식을 지원하지 않아 CRC 검사를 수행하지 못했다. 실제 PCSX2 로드 성공과 복원 화면으로 검증했다.
- 빌드 manifest와 번역 입력의 `runtime_verified`는 빌드 시점 값이다. 최신 실행 판정은 `reports/status_slice_runtime.json`을 따른다.

## 다음 작업

1. QA037의 상태 효과·장비 교환 검증을 보완한다. 이름·텍스트 변경이 해당 조건의 동작을 바꾸지 않는지 확인한다.
2. 첫 출격/전투의 공통 메뉴와 도움말 그림을 분류하고, 메뉴·도움말 한글화를 이어간다.
3. P4 미완료 항목을 모두 통과한 뒤 아이템·스킬/루트별 본번역을 확대한다.

## 재현

새 부팅은 다음과 같이 실행하고 `load game`의 No.02를 선택한다. F3 상태 복원과 구분한다.

```sh
'build/runtime/PCSX2-v2.6.3.app/Contents/MacOS/PCSX2' -portable -nogui -fastboot -nofullscreen -- 'build/status_slice_v2/Poison Pink (Japan) - status slice.iso'
```

전투 메뉴 확인: 출격 준비의 장비 메뉴 → 테이지/루티카; 전투 시작 → 도입 대화 진행 → 각 캐릭터의 스킬·도구 메뉴.
바람 공격 재현: 첫 라키 턴에 이동을 위3·왼쪽1로 확정 → 스킬 선택 → 위1·왼쪽1의 적 C(HP80)를 지정한다.
대화가 끼어들 수 있으므로 상태를 확인하며 입력한다. `tools/status_runtime_capture.py`는 대상 PCSX2 실행 파일을 검증하고 새 게임 캡처만 별도 파일로 보존한다.

빌드/정적 검증:

```sh
PYTHONPATH=tools python3 -m unittest test_status_db_codec test_status_slice
python3 tools/status_slice.py --output-dir build/status_slice_next
```

이미 존재하는 빌드 산출물은 덮어쓰지 않는다. 재현 빌드는 고정 원본과 검증된 튜토리얼 빌드 자료를 요구한다.
