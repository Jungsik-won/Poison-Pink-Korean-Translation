# 튜토리얼 24문장 한글화 시험본

2026-09-15. `t00_0010.rtb`의 첫 안내와 설명 선택지, 설명을 건너뛰었을 때의 대사,
설명을 볼 때의 이동·공격·방향·스킬 기초 대사까지 **본문/질문 24개와 해당 화자 표기 23개**를 번역했다.

후속 실행: [전투 완료·게임 내 저장과 새 부팅 로드](TUTORIAL_BATTLE_RUNTIME.md). Metal의 스킬 연출 충돌을 기록하고 Software 설정에서 튜토리얼 완료와 본편 진행 복원을 확인했다. 아래 24문장 최초 화면 검증과 구분한다.

## 번역과 폰트

- 번역 입력: [tutorial_slice.json](../localization/tutorial_slice.json). 원문 ID·바이트·파일 해시와 번역문을 함께 보존한다.
- 한글 151자가 필요하며 짝수 pair 저장을 위해 시험 문자 1자를 더해 **152개 글리프**를 추가했다.
- 원본 2,016글리프와 기존 테이블 매핑을 보존한다. 총 2,168글리프, 최종 ID는 **2167**이다.
- 첫 대사의 10개 한글을 새 폰트 끝부분에 배정해, 첫 화면에서 기존 2047 한계를 넘는 ID 읽기를 검사한다.
- Noto Sans KR Regular 2.004, SIL OFL 1.1. 글꼴 해시는 이전 실험 기록과 대조한다. [라이선스](../build/korean_sentence/OFL.txt).
- 원문 뜻·위치·범위·조건을 유지하고 라키의 단정적인 말투와 테이지의 설명하는 말투를 구분했다.
- 최대 2줄, 한글 24px/ASCII 12px 기준 줄당 360px 이하로 사전 검사했다. 이는 실제 창별 표시 확인을 대체하지 않는다.
- 도움말 그림, `はい/いいえ` 공통 선택 항목, 전투 메뉴, 이번 범위 이후의 대사와 이름은 원문으로 남는다.

[정적 번역 미리보기](../build/tutorial_slice/translation-preview.png).

### 원문 코드와 보이는 글자가 다른 사례

`魔凸`의 두 번째 코드 `93ca`는 CP932에서 `凸`이지만, 원본 게임의 해당 글리프 ID 1463을 복원하면 **神**으로 보인다.
따라서 화면상 `魔神`인 용어를 **마신**으로 번역했다. 코드 `905f`의 神 글리프와 함께 비교했다.
원문 바이트나 원문 필드는 바꾸지 않고 용어집의 문맥·근거에 기록했다.

![원본 글리프 비교: 魔 / 코드93ca / 神 / 敵 / 戦](../build/tutorial_slice/original-term-glyphs.png)

## 파일 확장 방법

32자 실험에서 쓰던 폰트 뒤 패딩으로는 152자를 수용할 수 없다.
폰트 뒤의 SYSTEM 리소스를 0x4000 정렬 2칸, 즉 **32,768바이트** 뒤로 옮겼다.
모든 미수정 SYSTEM 파일의 payload가 원본과 일치하는지 확인하고 HED의 위치·크기를 갱신했다.

ISO에서는 SYSTEM.DAT 바로 앞의 사용하지 않는 영역 32,768바이트가 모두 0인지 검사하고,
SYSTEM.DAT의 시작만 **LBA 750000 → 749984**로 당겼다. 그 파일의 끝 위치는 같다.
ISO 디렉터리 레코드의 little/big endian 위치·크기를 모두 갱신했다.
다른 ISO 파일의 LBA, 디렉터리 위치, 전체 ISO 크기는 유지했다.
기존 위치를 하드코딩한 코드가 있는지는 실행 검증으로 확인해야 하며, 정적 검사만으로 부팅 성공을 가정하지 않는다.

- 전체 ISO 변경: **576,481바이트**. 의도한 overlay 범위와 위치·값을 독립적으로 대조했다.
- RTB: 60,834 → 60,831바이트. 47개 문자열의 길이·본문 외의 모든 필드와 명령·분기 구조 보존.
- SHA-256: `c930e6c1cbfcc3d7cd52efb36ca296187123a7378655b9ada4eb8eda999b1c2b`.

## 빌드와 검사

```sh
python3 tools/tutorial_slice.py
python3 -m unittest discover -s tools -p 'test_tutorial_slice.py'
```

빌드 결과가 이미 존재하면 덮어쓰지 않는다. 입력 검수 상태, 원본/글꼴 해시, 글자 누락, 인코딩 왕복,
255바이트, 개행/예상 폭, 아카이브 정렬/범위, ISO extent 충돌과 원래 빈 공간의 0바이트를 검사한다.
기존 도구까지 합한 회귀 검사 **33개 통과**.

## 실행 검증

**24개 본문·질문과 화자 23개 모두 실제 화면 검수 통과.** PCSX2 2.6.3, Metal, 일본어 BIOS, MTVU 켜짐 조건이다.

- 새 부팅 후 첫 한글 대사, 최고 글리프 ID 2167 표시를 확인했다.
- 같은 ISO에서 `いいえ`를 선택해 안내 두 개와 전투 진입을 확인하고, 저장 상태를 복원해 `はい` 경로도 진행했다.
- 라키와 테이지의 이동·대기, 적 유닛 행동, 방향별 피해 안내, 마지막 스킬 기초 설명까지 진행했다.
- 이번 24개 문구에서 글자 누락·깨짐·창 밖 잘림은 보이지 않았다. 질문 `0xbb71`은 입력에 개행이 있으나 실제 선택 창에서는 한 줄로 표시되었고 전체 문구가 보였다.
- 사용 한글 151자가 이 범위에 모두 포함된다. 저장 pair를 맞추기 위한 여분 글리프 1자는 실행 검증 대상에서 제외한다.
- 첫 대사와 스킬 대사 두 지점의 에뮬레이터 상태를 저장했다. 첫 지점 2회, 스킬 지점 1회 복원 후 한글 대사와 화자 표시가 재현됐다.

![마지막 스킬 대사 복원 후](../build/tutorial_slice/evidence/skill-after-load.png)

### 상태 저장·복원 재현

1. 게임 입력을 모두 놓고 `Space`로 일시정지한다.
2. `F1`로 실험 전용 슬롯 1에 저장한다. `Space`로 재개한 뒤 `F11`(○)로 다음 화면에 간다.
3. 다시 `Space`로 일시정지하고 `F3`로 불러온다. `Space`로 재개해 원래 대사가 보이는지 확인한다.

상태 폴더는 `build/tutorial_slice/sstates`이며 이전 실험의 상태와 분리했다.
증거 사본은 `evidence/first-line.p2s`, `evidence/skill-line.p2s`에 보존했다.
첫 대사·스킬 지점은 위 증거 사본으로 재현한다. 후속 작업에서 실험용 슬롯 1과 현재 화면이 바뀌었으며, 최신 실행 상태는 [후속 검증 문서](TUTORIAL_BATTLE_RUNTIME.md)에 기록한다.
PCSX2 로그에는 MTVU 상태 저장의 불안정 가능성 경고가 남는다. 이번 절차의 3회 성공만 확인한 것이며 이전 진단본 실패의 원인은 확정하지 않는다.

**이 최초 화면 검증 시점에는 게임 내 저장·로드와 전투 완료가 미검증이었다.** 후속 Software 실행에서 실제 스킬 사용·튜토리얼 전투 완료·본편 진행 저장과 새 부팅 로드를 확인했다. 전체 반복·분기와 장시간 캐시 검증은 남아 있다.
도움말 그림·공통 선택 항목·전투 UI는 이번 번역 범위에 포함되지 않는다. P4 전체 완료나 배포판으로 간주하지 않는다.

### 문장별 화면 증거

| 원본 opcode 위치 | 번역문 | 캡처 |
| --- | --- | --- |
| `0xbb34` | 전투의 기본을 알려주마. | [화면](../build/tutorial_slice/evidence/first-line.png) |
| `0xbb71` | 전투에 대한 자세한 설명을<br>보시겠습니까? | [화면](../build/tutorial_slice/evidence/choice-before-load.png) |
| `0xbe15` | 흥, 괜히 강한 척하는 건<br>아니겠지? | [화면](../build/tutorial_slice/evidence/no-laki.png) |
| `0xbe7b` | 모르는 게 있으면 네<br>리벨 아우로라를 보렴. | [화면](../build/tutorial_slice/evidence/no-teige.png) |
| `0xbf78` | 전투는 유닛을 하나씩<br>조작하며 진행하는 것이다. | [화면](../build/tutorial_slice/evidence/yes-first.png) |
| `0xc03f` | 유닛의 기본 조작은<br>이동과 공격을 반복하는 것이다. | [화면](../build/tutorial_slice/evidence/basic-actions.png) |
| `0xc11c` | 나는 근접 공격형이라<br>바로 옆 칸만 공격할 수 있다. | [화면](../build/tutorial_slice/evidence/melee-type.png) |
| `0xc195` | 우선 나를 오른쪽 앞에 있는<br>마신 쪽으로 이동시켜 보아라. | [화면](../build/tutorial_slice/evidence/move-instruction.png) |
| `0xc263` | 멀리 있는 마신에게도<br>충분히 경계해야 한다. | [화면](../build/tutorial_slice/evidence/dialogue-c263.png) |
| `0xc2d8` | 우리가 다가갈 때까지<br>기다려 주는 녀석만 있진 않다. | [화면](../build/tutorial_slice/evidence/dialogue-c2d8.png) |
| `0xc351` | 공격이 닿는 거리까지<br>다가오는 마신도 있단다. | [화면](../build/tutorial_slice/evidence/dialogue-c351.png) |
| `0xc3ca` | 적의 이동 가능 범위와<br>공격 가능 범위에 주의하렴. | [화면](../build/tutorial_slice/evidence/dialogue-c3ca.png) |
| `0xc449` | 더 신중하게 대처하려면<br>적의 능력치를 확인하렴. | [화면](../build/tutorial_slice/evidence/dialogue-c449.png) |
| `0xc51d` | 다음은 내 차례구나. | [화면](../build/tutorial_slice/evidence/dialogue-c51d.png) |
| `0xc577` | 라키 때처럼 나를 오른쪽 앞의<br>마신에게 다가가게 해 보렴. | [화면](../build/tutorial_slice/evidence/dialogue-c577.png) |
| `0xc5ee` | 일부러 적에게 다가가<br>유인하는 것도 전략이란다. | [화면](../build/tutorial_slice/evidence/dialogue-c5ee.png) |
| `0xc6b8` | 전투에서는 적을 하나씩<br>쓰러뜨리는 것이 좋다. | [화면](../build/tutorial_slice/evidence/dialogue-c6b8.png) |
| `0xc729` | 적에게 포위당하지 않도록<br>유닛 배치에 신경 쓰거라. | [화면](../build/tutorial_slice/evidence/dialogue-c729.png) |
| `0xc7a8` | 자, 적이 공격해 온다! | [화면](../build/tutorial_slice/evidence/dialogue-c7a8.png) |
| `0xc85d` | 유닛은 공격받는 방향에 따라<br>받는 피해량이 달라진다. | [화면](../build/tutorial_slice/evidence/dialogue-c85d.png) |
| `0xc936` | 적을 공격할 때는<br>적극적으로 옆과 뒤를 노려라. | [화면](../build/tutorial_slice/evidence/dialogue-c936.png) |
| `0xc9af` | 반대로 네가 당하지 않도록<br>대기할 때의 방향도 조심하렴. | [화면](../build/tutorial_slice/evidence/dialogue-c9af.png) |
| `0xca87` | 나 같은 마법사는<br>스킬 공격이 더 특기란다. | [화면](../build/tutorial_slice/evidence/dialogue-ca87.png) |
| `0xcb02` | 스킬을 쓰면<br>멀리 있는 적도 공격할 수 있어. | [화면](../build/tutorial_slice/evidence/dialogue-cb02.png) |

기계 판독 보고서: [reports/tutorial_slice.json](../reports/tutorial_slice.json). 빌드 시점의 `manifest.json`은 정적 검사 스냅샷으로 유지하며 후속 실행 검증은 reports에 기록한다.
