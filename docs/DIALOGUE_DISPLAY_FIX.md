# 첫 대화의 본문 미표시 수정 — 2026-09-19

## 결과

PCSX2 2.6.3의 16:9 / Software 환경에서 새 게임 첫 대화와 사용자 상태저장 1번의 한글 본문 표시를 확인했다. 사용자가 열어 둔 기존 창에도 화면 배치 보정을 적용해 표시를 확인했다. ISO와 번역 데이터는 변경하지 않았다.

## 원인과 비교

- 원본 ELF CRC는 `F7786EE4`, 현재 한글판은 `7502FF83`이다.
- PCSX2 번들 `patches.zip`의 `SLPS-25854_F7786EE4.pnach`에는 Arapapa의 `Widescreen 16:9` 보정이 있다. 여기에는 대화창 위치 보정도 포함된다.
- 한글판에서는 CRC가 달라 이 패치가 자동 적용되지 않았다.
- 원본 ISO도 같은 환경에서 이 보정을 끄면 대사가 사라졌고, 켜면 표시됐다. 한글판에 동일 보정을 연결한 새 게임에서도 한글 대사가 표시됐다.
- 하단 영역의 저장된 Y 좌표가 `312`인 상태에서는 본문이 가려졌다. 보정된 좌표는 `384`다. 이름의 어두운 색은 원본에서도 같았으며 글리프 손상 증거가 아니었다.
- 번역 본문, 글꼴과 문자표, CPU 쪽 글리프 캐시의 실제 픽셀은 정상임을 확인했다. ASCII 시험 문구도 동일하게 가려졌다.

이 결과는 위 PCSX2 환경의 첫 초상화 대화에 대한 검증이다. 원본 실기나 4:3 전체 동작을 판정하는 자료는 아니다.

## 적용 파일

`outputs/pcsx2_dialogue_compat/SLPS-25854_7502FF83.pnach`는 원본 번들 패치의 작성자·내용을 유지하고 대상 CRC 파일명을 바꾼 것이다. 34개 수정 주소의 기존 값이 한글판에서도 원본 ELF와 같음을 확인했다.

설치 위치:

`<LOCAL_USER_HOME>/Library/Application Support/PCSX2/patches/SLPS-25854_7502FF83.pnach`

사용자 설정의 `EnablePatches`와 `EnableWideScreenPatches`는 이미 켜져 있었다. 앞으로도 이 설정이 필요하다. 실행 파일을 다시 수정해 CRC가 바뀌면 새 CRC에 맞춰 패치 파일을 재생성하고, 34개 주소와 코드 삽입 공간을 다시 검사해야 한다. CRC 파일명만 무조건 복사해서는 안 된다.

## 상태저장 복구

이전 상태저장은 잘못된 화면 좌표도 담고 있어서 정적 보정값만 등록해도 바로 회복되지 않았다.

원본 상태저장을 백업한 뒤 복구 사본의 EE RAM에 번들 보정 34곳과 이미 만들어진 대화창 좌표 2곳을 반영했다. 총 36개 워드 범위에서 실제 110바이트만 바뀌었다. 다른 15개 상태 멤버는 동일하다. 복구 사본을 새 테스트 프로세스로 불러와 첫 대사 표시를 확인한 후 사용자 슬롯 1에 설치했다.

- 원본 백업: `~/Library/Application Support/PCSX2/sstates/SLPS-25854 (7502FF83).01.p2s.before-dialogue-fix.bak`
- 프로젝트 원본: `build/dialogue_missing_v1/user-slot1-original.p2s`
- 복구 사본: `build/dialogue_missing_v1/user-slot1-dialogue-recovered.p2s`
- 복구된 캐시: `0x0062dcb4`, float `312 → 384`; 진행 표시 위치 `0x0062dbe4`, float `418 → 400`.

상태저장의 내장 미리보기 이미지는 원본 그대로다. 실제 로드 후 화면은 별도 검증했다. 다른 오래된 상태저장은 자동 복구한 것이 아니다.

사용자의 두 메모리카드는 작업 전후 SHA-256이 동일하다. 테스트에 사용한 복제 카드는 프로젝트에 보관했다. 테스트 인스턴스는 종료하고 프로젝트 PCSX2 설정을 원복했으며, 사용자의 기존 창은 대사가 보이는 상태로 유지했다.

## 증거

`reports/dialogue_missing_fix.json`에 주소별 변경·파일 해시·카드 보존 검사가 있다. `build/dialogue_missing_v1/evidence/`에 원본 보정 ON/OFF, 한글판 새 게임, 복구 상태저장, 사용자 기존 창 화면을 보관했다.

최신 ISO는 계속 `build/battle_conditions_psd_v1/Poison Pink (Japan) - Korean battle conditions v1.iso`다. 이번 수정은 PCSX2 호환 보정이며 ISO에 코드를 영구 삽입한 것이 아니다.
