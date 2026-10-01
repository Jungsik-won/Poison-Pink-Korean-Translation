# RTB 문장 길이 변경 실행 검증

2026-09-15. 원본에서 직접 만든 길이 증가·감소 실험 ISO를 PCSX2 2.6.3에서 각각 새로 부팅했다.
이전 동일 길이 실험의 한글 32자 폰트를 그대로 사용한다.

## 실험 조건

| 항목 | 증가본 | 축소본 |
| --- | --- | --- |
| 원문 | `戦い方の基本を教えるぞ` | 동일 |
| 번역 | `전투의 기본을 알려주마.` | `전투 기본을 알려주마` |
| 게임 인코딩 길이 | 22 → 23바이트 | 22 → 20바이트 |
| RTB 크기 | 60,834 → 60,835바이트 | 60,834 → 60,832바이트 |
| 아카이브 처리 | 다음 파일 앞 0 패딩 1바이트 사용 | 남는 2바이트를 0 패딩으로 전환 |
| 명령·분기 | 모든 명령 수·순서·분기 값 보존 | 동일 |
| ISO 배치 | 원본 파일 LBA·ISO 크기 유지 | 동일 |

수정 위치는 `DMAP:2786:0000bb34`, `_PE0103T`의 17번 명령이다.
각 ISO는 기존 한글 폰트/테이블과 SYSTEM.HED, DMAP의 수정 RTB와 HED 크기 정보만 반영한다.
전체 ISO 차이를 staged 파일의 변경 위치·값과 독립적으로 비교했다.

## 실행 결과

### 증가본

- 실제 23바이트 문장과 끝의 마침표 출력 확인, 창 밖 잘림 없음.
- 이후 일본어 질문과 선택지 정상.
- `はい`를 선택해 `戦闘では、ユニットを１体ずつ…` 설명 및 유닛 턴 도움말 화면 진입 확인.
- 이 실행에서는 이후의 전체 조작 튜토리얼·전투·루프 완료까지 검증하지 않았다.

![길어진 대사](../build/rtb_resize/longer/evidence/translated-line.png)
![설명 보기 분기](../build/rtb_resize/longer/evidence/yes-branch.png)

### 축소본

- 실제 20바이트 문장 출력과 창 내 맞춤 확인.
- `いいえ` 선택 후 라키·테이지의 일본어 대사, 이름과 장음부호 보존 확인.
- 대화 종료 후 전투의 유닛 턴 화면 진입 및 Circle 입력으로 명령 메뉴 열림 확인. 전투 완료나 저장/로드는 미검증.

![짧아진 대사](../build/rtb_resize/shorter/evidence/translated-line.png)
![전투 진입](../build/rtb_resize/shorter/evidence/battle-entry.png)

## 재현

독립 시험용 앱, 설정, BIOS, 메모리카드는 `build/runtime`에 있다.
첫 한글 실험과 동일한 PCSX2 2.6.3 / Metal / Japan v02.00 BIOS를 사용했다.
이미 실행 중인 시험용 세션을 종료하고 아래에서 `longer` 또는 `shorter`를 선택한다.

```sh
'build/runtime/PCSX2-v2.6.3.app/Contents/MacOS/PCSX2' \
  -portable -nogui -fastboot -nofullscreen \
  -- "$PWD/build/rtb_resize/longer/Poison Pink (Japan) - longer.iso"
```

1. F10(Start) → 프롤로그 F11(Circle) → 영상 시작 후 F10으로 건너뛰기.
2. 첫 라키 한글 대사까지 기다리고 F8로 캡처.
3. F11로 질문 열기. 증가본은 왼쪽 `はい`에서 F11, 축소본은 오른쪽 `いいえ`에서 F11.
4. 분기 뒤 대사와 다음 화면을 확인한다. 방향키는 실제 화살표 키다.

검증 근거는 새 부팅이다. 이전 상태 파일 복원 문제를 이번 결과로 해결 처리하지 않는다.
두 가지 길이 변경과 선택지의 서로 다른 경로를 나누어 확인하며, **각 빌드의 모든 분기를 전부 검증한 결과는 아니다.**
대량 문장·255바이트 경계·개행·겹받침의 실제 화면, 게임 내 저장/로드와 장시간 전투/루프는 추가 검증 대상이다.

보고서: [증가본](../reports/rtb_resize_longer.json), [축소본](../reports/rtb_resize_shorter.json).
원문 파서 및 구조 근거: [RTB_FORMAT.md](RTB_FORMAT.md).

## 빌드 식별

- 증가본 SHA-256: `755adc4af8f501ca2217da4e105cce857caa8aaae833e071a4cee287dcf51d91`.
- 축소본 SHA-256: `f3ee6ad48926bae7e7f43a3ef560adeaf2439a78cf9b06f8bee901da88bbc017`.

시험용 PCSX2는 축소본의 전투 명령 메뉴에서 일시정지했다. Space로 재개한다.
