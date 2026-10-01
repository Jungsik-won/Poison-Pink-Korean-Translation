# 튜토리얼 전투 완료와 게임 내 저장·로드 검증

2026-09-15. 기존 24문장 시험 ISO를 변경하지 않고 후속 실행을 검증했다.

**PCSX2 2.6.3의 Software 렌더러에서 튜토리얼 전투를 완료하고, 본편 진행 슬롯을 저장한 뒤 새 부팅의 `load game`으로 복원했다.**
Metal 렌더러에서는 스킬 연출 중 PCSX2 자체의 assertion으로 종료되어, 검증 설정을 Software로 변경했다.

## 1. 시험본과 검증 범위

- ISO: `build/tutorial_slice/Poison Pink (Japan) - tutorial slice.iso`
- SHA-256: `c930e6c1cbfcc3d7cd52efb36ca296187123a7378655b9ada4eb8eda999b1c2b`
- 기존 번역·글리프·ISO 데이터는 그대로다. 이번 변경은 시험용 에뮬레이터 설정, 입력 도구, 검증 기록이다.
- 이전 24문장·23개 화자 화면 검증은 [TUTORIAL_SLICE.md](TUTORIAL_SLICE.md)에 있다.
- 기계 판독 결과와 파일 해시: [tutorial_battle.json](../reports/tutorial_battle.json).

## 2. Metal 충돌과 Software 비교

첫 화염 스킬의 대상 지정은 성공했지만 연출 중 PID 55962가 SIGABRT로 종료됐다.
macOS 충돌 기록의 GS 스레드에는 `pxOnAssertFail` → `GSDeviceMTL::DoStretchRect` → `GSRendererHW::Draw`가 남았다.
[충돌 기록](../build/tutorial_slice/evidence/skill-crash.ips), [직전 로그](../build/tutorial_slice/evidence/skill-crash.log).

같은 ISO와 `skill-line.p2s`를 사용하고 렌더러만 Software로 바꿔 동일 공격을 재실행했다.
적 HP 75 → 5, 전투 화면 복귀를 확인했으며 이후 반복 스킬·근접 공격·포획·후속 영상을 통과했다. MTVU는 계속 켜 두었다.

![Software에서 첫 화염 공격 결과](../build/tutorial_slice/evidence/skill-software-hit.png)

원본 ISO의 동일 연출과 직접 비교하지 않았으므로 **패치와 완전히 무관한 충돌이라고 확정하지 않는다.**
현재 입증한 것은 이 시험본의 Metal 중단과 Software 설정에서의 진행 성공이다.
렌더러 번호 `Software=13`, `Metal=17`은 [PCSX2 v2.6.3 Config.h](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.6.3/pcsx2/Config.h)의 정의와 대조했다.

## 3. 전투 기능 결과

| 항목 | 실제 확인 |
| --- | --- |
| 화염 스킬 | 첫 적 HP 75 → 5, 사용 가능 횟수 5 → 4, 반복 사용 후 정상 복귀 |
| 근접 공격 | 라키 발톱 공격, 오버킬 연출과 구속 상태 |
| 포획 | 일반 적 A·B·C 세 마리 포획, 전장·턴 목록에서 제거 |
| 기타 전투 데이터 | 적의 공격·후퇴, 경험치 증가, 라키 레벨 상승 |
| 장벽 | 테이지 기본 책 타격으로 해제. 적 HP 110 → 89와 장벽 아이콘 소멸 확인 |
| 마지막 적 | 장벽 해제 후 화염 피해로 HP 13, 이어 암흑 스킬로 처치 |
| 전투 종료 | 후속 영상 → 저장 질문 → 시스템 저장 → 타이틀 도달 |

별도 `Victory` 배너는 캡처하지 않았다. 전투 종료 판단은 마지막 적 처치 후 영상과 저장 단계로 넘어간 실제 진행에 근거한다.

### 장벽 해제 조건의 원본 근거

화염·암흑 마법만으로는 장벽을 해제하지 못했다. 원본 `dmap/ev/ev147.tm2`는 이 적의 약점을 **테이지의 타격 공격**으로 명시한다.
해당 TIM2의 640×384 8비트 인덱스 이미지와 팔레트를 복원해 확인했다. 이 이미지는 번역·교체하지 않았다.

![원본 장벽 도움말](../build/tutorial_slice/ev147.png)

## 4. 시스템 저장과 진행 슬롯의 차이

프롤로그 후 저장 질문에서 미포맷 시험용 카드 슬롯 1을 포맷하고 저장 성공 메시지를 확인했다.
카드는 프로젝트의 `build/runtime/memcards/Mcd001.ps2`이며 포맷 전 사본을 보존했다.

그러나 첫 새 부팅의 `load game`에는 진행 슬롯이 `NO DATA`였다. **이 시스템 저장을 본편 진행 저장으로 판정하지 않았다.**
본편 새 게임에서 테이지 루트를 선택하고 제1계층 첫 출격 준비의 상위 메뉴 → `セーブ`에서 빈 No.01 슬롯에 저장했다.

![본편 No.01 저장 성공](../build/tutorial_slice/evidence/game-slot-save-complete.png)

저장 완료 후 PCSX2를 종료하고 `-state`·`-statefile` 없이 새로 실행했다.
타이틀 `load game`에서 No.01이 나타났고, 선택하여 같은 출격 준비 화면으로 복원됐다.

| 비교 항목 | 저장·로드 확인값 |
| --- | --- |
| 슬롯·장소 | No.01 / 第1階層 灰色の王宮・戦闘 |
| 슬롯의 플레이 시간 | 000:05 |
| 테이지 | Lv.5, HP 100/100, EXP 0/180 |
| 출격 | 테이지·라키·루티카 3명 / 3/7 |
| PP·소지금 | 200 / 4,000 |

![새 부팅 후 본편 진행 복원](../build/tutorial_slice/evidence/cold-boot-game-restored-stats.png)

튜토리얼의 레벨 상승은 본편 시작 수치와 별개다. 본편 복원 화면은 일본어이며, **이 로드 자체로 한글 글리프 재표시를 검증했다고 주장하지 않는다.**
한글 표시와 한글 대사의 에뮬레이터 상태 복원은 이전 24문장 실험의 증거를 유지한다.

### 메모리카드 보존

- 포맷 전: `build/tutorial_slice/evidence/memcards-before/`
- 시스템 저장 후: `build/tutorial_slice/evidence/memcards-after/`
- 본편 진행 슬롯 저장 후: `build/tutorial_slice/evidence/memcards-progress/`
- 본편 저장 직후 슬롯 1 SHA-256: `cabf32fa34cf65067eaf42a4d8ff7be9c667b26d44b6ddc9627cefb7d6b1a34e`
- 새 부팅·로드 후 사본: `build/tutorial_slice/evidence/memcards-loaded/`, SHA-256 `11a9c88006817548815ccaaa88a9194e8d813c4136e5fa491446b91c20a20be7`.
- 재실행·로드 전후 카드 파일은 오프셋 528~535의 8바이트가 다르다. 해당 필드의 의미는 확정하지 않았으며 두 사본을 모두 보존했다. 진행 슬롯과 출격 상태의 복원은 화면으로 확인했다.
- 슬롯 2는 원래 해시와 같고 수정되지 않았다.

## 5. 현재 실행 설정과 재현

[검증 설정 사본](../build/tutorial_slice/evidence/PCSX2.validated.ini).
프로젝트 전용 설정 `build/runtime/inis/PCSX2.ini`의 `Renderer = 13`을 유지한다.
일반 앱의 전역 PCSX2 설정이나 원본 ISO는 변경하지 않았다.

| 입력 | 키 |
| --- | --- |
| 방향 | 방향키 |
| ○ / × | F11 / F12 |
| △ / □ | F5 / F6 |
| L1 / R1 | F9 / F7 |
| START | F10 |
| 일시정지·재개 | Space |
| 캡처 | F8 |
| 에뮬레이터 상태 저장·로드 | F1 / F3 |

이 세션에서 문자키 I/J/Q/E가 반응하지 않아 기능키로 변경했다. 변경 후 △의 상태 화면 진입을 확인했다.
문자키 미동작의 원인은 확정하지 않았다. 입력 도구 `tools/runtime_keys.py`도 현재 기능키 설정에 맞췄다.

2026-09-19 추가 검사: 위 F5/F6/F9가 PCSX2 기본 `CycleInterlaceMode`,
`CycleAspectRatio`, `ToggleSoftwareRendering`과 중복되어 있었다. 프로젝트 검증
프로필에서 이 세 에뮬레이터 단축키만 해제했다. 게임 버튼 매핑은 유지했고
`runtime_keys.py`는 게임 키를 보내기 전에 설정 불일치·중복을 거부한다.
사용자 일반 PCSX2의 I/J/Q 매핑에는 중복이 없어 변경하지 않았다.

프로젝트 루트에서 새 부팅:

```sh
'build/runtime/PCSX2-v2.6.3.app/Contents/MacOS/PCSX2' \
  -portable -nogui -fastboot -nofullscreen \
  -- 'build/tutorial_slice/Poison Pink (Japan) - tutorial slice.iso'
```

타이틀의 `load game` → No.01을 선택한다. F3는 게임 내 로드 검증에 사용하지 않는다.
현재 실행은 새 부팅의 No.01 로드 이후 출격 준비 화면에서 일시정지해 두었다. Space로 재개할 수 있다.

## 6. 남은 단계

1. 본편 스킬/아이템 DB의 전체 레코드 파서와 손실 없는 왕복 검증.
2. 공통 선택 항목·도움말 이미지·전투 UI의 한글화와 P4 미완료 범위 보완.
3. 다른 루트·본편 전투·반복 경로 및 장시간 폰트 검증.
4. 향후 패치 빌드 간 게임 저장 호환성 검증.
5. 필요 시 원본 ISO 동일 공격으로 Metal 충돌 비교. 현재 검증 실행은 Software 설정을 사용한다.

이번 결과만으로 P4 전체나 전체 한글화 배포 조건을 통과시킨 것은 아니다.
