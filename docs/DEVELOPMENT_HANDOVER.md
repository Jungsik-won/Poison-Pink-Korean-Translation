# Poison Pink 한글화 인계서 — 검수 반영판

## 최신 테스트 ISO: 상점·도감 + 전투 음성 보완 v4 (2026-10-02)

`build/korean_update_v4/Poison Pink (Japan) - Korean update v4.iso`

SHA-256 `b6601a8b7a6a5c6de956a9ccaa33804a304429e29cfa94bbe9e7d7f59a017445`, ELF CRC `04D21A3D`. 최신 실행 v3 기반으로 사용자 dic_pt04/sys007/sys019/dic_pt02 4장과 전투 음성32종 추가. 총442번역(511슬롯)·116비언어·34보류. 전체 ISO 변경 범위 밖 바이트 동일, 이전 게임 로드 세그먼트·대화 보정·heap0x655000 보존, 최신 카탈로그 MIPS 실행 시험4개/592종 매칭 및 새 텍스처 재읽기 통과. 외부 PCSX2 패치 불필요. v4 실제 게임 실행은 미검증. `reports/korean_update_v4.json` 참조.

`reports/user_shop_dictionary_v1.json` applied_assets 4개와 `localization/battle_voice_subtitles_v3.json` 통합 완료. 거절된 자동 식자와 dic_pt03 제외. 공개 자료에 원본 ISO·음성·PSD·저장 데이터·글꼴 매핑 원자료를 포함하지 말 것.

## 이전 테스트 ISO: 전투 음성 자막 v3 (2026-10-01)

`build/battle_voice_subtitles_v1/Poison Pink (Japan) - Korean battle subtitles v3.iso`

SHA-256 `8ba7111a988b095902e727f089bdf5ac12778c59cfeb127e193402ce17a888b9`, ELF CRC `0A6FFA91`. 기존 standalone v1 전체 번역·이미지·영상 유지. 음성 592종 중 410종/456뱅크 슬롯 한글 자막, 102종 비언어 기합/무음 제외, 80종 불확실하여 보류. ASR 결과의 일본어·한국어 텍스트 검토이며 사람이 모든 음성을 청취한 검수는 아님.

KV SPU 0x600 재생에 FNV/길이 연결. 0x650000 새 ELF PT_LOAD, heap 시작 0x655000, BSS clear 끝 원래 값 유지. 렌더 기존 글꼴, y330/흰색+검정 그림자, 2~4초, 다음 발화 갱신. 외부 pnach 불필요. ISO 전체 계획 밖 바이트 동일 검증. 새 부팅+정상 메모리카드 저장 사용. 오래된 상태저장은 실행코드/폰트/좌표를 되돌리므로 사용하지 말 것.

검증: 최종 v3 Software 4:3 새 부팅 및 RAM 코드/문구/좌표 대조. 이전 v1 동일 코드의 정상 카드 불러오기·전투맵·마법 대상 화면. 복사 상태에서 게임 음성 재생 함수를 호출하여 맵 가거라!/컷인 조디아여! 표시 확인. 시험용 일회 재생 헬퍼는 ISO에서 제외. 자연스러운 공격 조작으로 자막을 확인한 것은 아니며 전체 게임/Metal 전투/실기 미검증. 생성 MIPS 명령 실행 시험 4개(592종 매칭/범위/타이머/메모리) 통과.

보고서 `reports/battle_voice_subtitles_v1.json`; 검토표 `outputs/battle_voice_subtitles_v1/voice_review.tsv`; 안내 `outputs/battle_voice_subtitles_v1/README_KO.txt`. 다음 작업에서 이 ISO와 추가 ELF 세그먼트/heap 예약을 보존할 것. 재빌드 원본은 standalone v1로 고정되어 있음.

## 이전 기반 ISO: 외부 패치 없는 독립 실행 v1 (2026-10-01)

`build/iso_dialogue_fix_v1/Poison Pink (Japan) - Korean standalone v1.iso`

SHA-256: `f7276bfe1da4b9599d5242daa74ee094ac87e3044173e3c943b6320890fed072`. ELF CRC `15A5210D`.

최신 DMAP flow v1 기반에 초상화 대화 레이아웃 네 값(실제 6바이트)만 반영. 외부 PCSX2 패치 없이 대화 표시. 전체 ISO 계획 밖 바이트 동일, 기존 텍스트·이미지·영상·코드·시야각·글자 폭 보존. `.iso.pcsx2` 또는 호환 ZIP을 배포하지 않음.

PCSX2 2.6.3 패치 OFF 실제 확인: Software 4:3 새 게임 여러 인물·두 줄 대사, 전투 준비/첫 본편 전투 대사·유닛 이동; 기본 Metal 4:3 첫 초상화 대화; Software 16:9 기존 레벨 23 메모리카드 저장 불러오기 및 해당 전투 재개. 모든 분기/전체 엔딩/실기/다른 에뮬레이터 버전은 미검증.

다음 작업은 이 ISO를 기반으로 하고 `localization/runtime/iso_dialogue_layout.json`의 네 값을 보존할 것. `runtime_compat.inspect_iso`는 통합 보정을 인식해 외부 패치가 불필요함을 반환하며, ISO overlay는 해당 빌드에 sidecar를 생성하지 않음. 후속 빌더에서 sidecar 존재를 무조건 가정하지 말 것. 이전 기반판의 PCSX2 패치 필수 안내는 최신본에 적용되지 않음. 과거 강제 상태저장을 로드하지 말고 새 부팅 후 정상 게임 저장 사용.

빌더 `tools/build_iso_dialogue_fix.py`, 검증 기록 `reports/iso_dialogue_fix_v1.json`, 증거 `build/iso_dialogue_fix_v1/evidence`.

## 이전 기반 ISO: DMAP 지역명 한글화 추가 v1 (2026-10-01)

`build/dmap_flow_ko_v1/Poison Pink (Japan) - Korean DMAP flow v1.iso`

SHA-256: `b1ebb5db3d0613ea9fe1160f6636c7481fb4d71c43e6b2d9b67f366ea9ca06b2`. DMAP maps v1에 flow/bf_nm_a~j,s 11장 추가. 기존 지도 이미지 75장과 클래스·상점·컨트롤러 수정 보존. 일본어 제목만 기존 용어로 한국어화; 영어 영역의 원본 인덱스·픽셀 및 UAD 보존. 원본 제목 잉크 영역의 폭·높이·위치 유지, 한국어 자간은 시각 검수. 전체 ISO 계획 밖 바이트 동일 검증. ELF CRC 565FA10D 유지, 해당 호환 ZIP 동봉. 실제 게임 실행 미검증.

보고서: reports/dmap_flow_ko_v1.json. 원본 생성 결과·프롬프트·게임용 미리보기: outputs/dmap_flow_ko_v1. 빌더: tools/build_dmap_flow_ko_v1.py.

## 이전 기반 ISO: DMAP 지도 이미지 한글화 v1 (2026-10-01)

`build/dmap_map_ko_v1/Poison Pink (Japan) - Korean DMAP maps v1.iso`
SHA-256: `481a8ea8e042b0dd3385bb5ed56aa3b3d8e41dad222fef053c81c751854f1f3e`.

UI test v6 기반. DMAP/dmap/map 전체 1,353장 검토; 전투 시작 화면 73장과 특수 명칭 2장 추가, 기존 bstart 한글 이미지 137장 유지. 이전에 준비된 클래스·상점·컨트롤러 문구도 class_change_review_v1의 3개 파일로 통합.

내장 이미지 생성 도구 사용. 원본 TM2 크기·헤더·팔레트·파일 길이 보존, UAD 및 ISO 계획 범위 밖 전체 바이트 동일 확인. 생성형 편집으로 배경 세부 표현 차이가 있음. 실제 게임 실행은 미검증. PCSX2 CRC 565FA10D용 호환 sidecar/ZIP 동봉. 보고서 reports/dmap_map_ko_v1.json; 이미지·프롬프트·검수 자료 outputs/dmap_map_ko_v1; 빌더 tools/build_dmap_map_ko_v1.py.

## 준비 당시 기록 (DMAP v1 반영 완료): 클래스 체인지 전체 문구 검수 (2026-09-30)

다음 ISO에는 `reports/class_change_review_v1.json` pending_files 3개 사용. 상점/추가 안내문 대기 작업 포함하며 기존 두 pending 보고서를 대체함. 클래스명 전체 및 설명 22종 대조. 설명 한 줄 최대 10문자(공백 포함), 포인터·비문자 데이터 보존. ISO 미생성, 실제 게임 배치 미검증. `outputs/class_change_review_v1` 검수 CSV 참조.

## 준비 당시 기록 (DMAP v1 반영 완료): 추가 안내문 통합 (2026-09-30)

`reports/remaining_messages_v1.json` pending_files를 다음 ISO에 사용. 기존 shop_messages_v1의 10문구 포함 + 컨트롤러 연결 3줄·회차 1개 추가. shop_messages_v1을 뒤에 덮어쓰지 말 것. 원래 문자열 종료 위치와 제어문자, 실행 코드 및 기존 한글 폰트 확인. ISO 미생성, 실행 미검증. 번역 목록 128,274행에 의미 검수 v1~v4를 합쳐 검사했고 일본어 단어 잔존/빈 번역 후보 0개. 이미지·실행 경로 전체 번역 완료를 의미하지 않음.

## 준비 당시 기록 (DMAP v1 반영 완료): 상점 수량·확인 대사 (2026-09-30)

`reports/shop_messages_v1.json` pending_files의 SLPS_258.54를 다음 통합에 반영. UI test v6 ELF 기반. 구매·매각·사용 수량 및 확인 대사 10개; 기존 번역 보류 항목의 화면 사용 확인 후 반영. 기존 종단 NUL 위치, 제어 토큰, 실행 코드 및 영역 밖 바이트 보존. 현재 폰트 매핑 확인. ISO 미생성·미수정, 게임 실행 미검증.

## 이전 기반 ISO: 사용자 UI 중간 테스트 v6 (2026-09-30)

`build/user_ui_test_v6/Poison Pink (Japan) - Korean user UI test v6.iso`
SHA-256: `3086890c313ffcbf1303671e3e0f11a1dded4194c0ad742cb54a59e61b5b3771`.

v5 기반에 최신 sys045 v2 수정본 반영. 전체 ISO 계획 밖 바이트 동일 및 문구 영역 밖 인덱스 보존 확인. 게임 실행 미검증. 호환 sidecar/ZIP 동봉. reports/user_ui_test_v6.json 참조.

## 준비 당시 기록 (v6 반영 완료): sys045 수정본 v2 (2026-09-30)

사용자 최신 PSD를 `outputs/user_sys045_v2`에 보관하고 `build/user_sys045_v2/textures/STATUS/status/sys045.tm2`로 변환. 다음 ISO 통합에서 `reports/user_sys045_v2.json`의 pending_assets를 사용하여 기존 v1 sys045를 대체. 장비 3상태 반영, ITEM/문구 밖 인덱스/팔레트/헤더/길이 보존과 불투명 알파 검사 통과. ISO 미생성·미수정, 게임 실행 미검증.
## 이전 기반 ISO: 사용자 UI 중간 테스트 v5 (2026-09-24)

`build/user_ui_test_v5/Poison Pink (Japan) - Korean user UI test v5.iso`
SHA-256: `e47cb3f57e0196a3e195024c3971d45b2be1146c18ebba21694a1d2629abce90`.

v4 기반에 사용자 csl_bg1/sys045 대기 작업 반영 완료. 아래 준비 당시의 적용 대기/ISO 미수정 기록은 이 상태로 대체. 기존 모든 작업 유지. 두 멤버 재읽기, 전체 ISO 계획 밖 바이트 동일 및 문구 영역 밖 인덱스 보존 검사 통과. 실제 게임 미검증. CRC7502FF83 호환 sidecar/ZIP 동봉. `reports/user_ui_test_v5.json` 참조.

## 준비 당시 기록 (v5 반영 완료): 사용자 sys045 장비 PSD (2026-09-24)

`outputs/user_sys045_v1`에 원본 PSD·미리보기·비교본. 사용자 장비 3상태 가시 합성 반영, ITEM과 문구 밖 인덱스/팔레트/헤더/길이 보존 및 불투명 알파 확인. `build/user_sys045_v1/textures/STATUS/status/sys045.tm2` 준비. **ISO 미생성·미수정**, 실제 게임 미검증. 다음 통합은 `reports/user_sys045_v1.json`과 `reports/user_csl_bg1_v1.json`의 pending_assets를 함께 반영.

## 준비 당시 기록 (v5 반영 완료): 사용자 csl_bg1 캐릭터 선택 배경 (2026-09-24)

`outputs/user_csl_bg1_v1`에 사용자 원본 PSD·가시 합성·TIM2 미리보기·비교본. 상단 안내와 하단 선택/결정/줄거리/취소 사용자 식자 반영. 영문·아이콘·편집 범위 밖 인덱스 및 팔레트/헤더/파일길이 보존, 불투명 알파 검사 통과. `build/user_csl_bg1_v1/textures/STATUS/status/chr_cel/csl_bg1.tm2` 준비. 다음 통합은 `reports/user_csl_bg1_v1.json`의 pending_assets. **사용자 요청에 따라 ISO 생성·수정 없음**. 실제 게임 미검증.

## 이전 기반 ISO: 사용자 UI 중간 테스트 v4 (2026-09-21)

`build/user_ui_test_v4/Poison Pink (Japan) - Korean user UI test v4.iso`
SHA-256: `ace426201a5e31336ad3f4a6e26eb2b56099fc76683657abcba4fecc53738686`.

사용자 sys040 수정 PSD를 가시 합성 그대로 추가. 글자 형태/문구 유지, 텍스트 칸 밖 영문/숫자/장식/인덱스 보존. v3 sys027/sys036과 구속 두께 수정 등 이전 모든 작업 유지. 전체 ISO 비교와 sys040 재읽기 통과. 실제 게임 미검증. `reports/user_ui_test_v4.json` 참조. CRC7502FF83 호환 sidecar/ZIP 동봉.

## 이전 기반 ISO: 사용자 UI 중간 테스트 v3 (2026-09-21)

`build/user_ui_test_v3/Poison Pink (Japan) - Korean user UI test v3.iso`
SHA-256: `c8a49ec4f0e97a7c0c2f7b88d485125174000d0b7d82809dbd15e1683506cdb5`.

사용자 sys027/sys036 PSD를 가시 합성 그대로 추가. 글자 형태/문구 유지, 텍스트 칸 밖 영문/숫자/장식/인덱스 보존. v2 구속 두께 수정과 이전 모든 작업 유지. 전체 ISO 비교와 두 멤버 재읽기 통과. 실제 게임 미검증. `reports/user_ui_test_v3.json` 참조. CRC7502FF83 호환 sidecar/ZIP 동봉.

## 이전 기반 ISO: 사용자 UI 중간 테스트 v2 — 수정 구속 PSD

`build/user_ui_test_v2/Poison Pink (Japan) - Korean user UI test v2.iso`
SHA-256: `f301e337690e27c80d6b72acf5f04fcda875e1961e58423ca2cca94777291e18`.

사용자가 일본어 배경을 지운 최신 sys031 PSD를 전체 가시 합성 그대로 반영. 별도 문자 제거/리사이즈 없이 변환. sys031 글자 네 칸 밖 효과 원본 보존. v1의 sys009/sys015 및 이전 작업 유지. 전체 ISO 비교 통과, sys031 외 바이트 동일. 실제 게임 미검증. `reports/user_sys031_v2.json` 참조. CRC7502FF83 호환 sidecar/ZIP 동봉.

## 이전 기반 ISO: 사용자 UI 3장 중간 테스트 v1 (2026-09-20)

`build/user_ui_test_v1/Poison Pink (Japan) - Korean user UI test v1.iso`
SHA-256: `856e3e831ee96159bdf3af51aa570fce43c383f5039e84ff4a81cfba69bdaee1`.

캐릭터 이름판 통합판 기반에 사용자 sys009/sys015/sys031 적용 완료. 아래 준비 당시의 ‘적용 대기/ISO 미수정’ 상태는 이 기록으로 대체. 대기 항목 3개 모두 반영. 기존 대사·영상·전투조건·캐릭터 이름판 유지. 3개 텍스처의 승인된 편집 영역 밖 픽셀 및 ISO 계획 범위 밖 전체 바이트 동일 검사 통과. 실제 게임 미검증. CRC7502FF83 sidecar/ZIP 동봉. `reports/user_ui_test_v1.json` 참조. 폐기한 15장 식자는 미포함.

## 준비 당시 기록 (아래 3장 모두 현재 ISO 반영 완료): 사용자 sys031 구속 PSD (2026-09-20)

`outputs/user_sys031_v1`에 원본 PSD/일본어 겹침 제거 PSD/비교 이미지. 배경에 남아 있던 일본어 拘束을 네 UAD 글자 칸에서 제거하고 사용자 선명·흐림 구속 아트 합성. `build/user_sys031_v1/textures/STATUS/status/sys031.tm2` 준비. 네 칸 밖 인덱스·효과장식, 팔레트/헤더/크기 보존. 표시 칸 내 아트 경계 및 불투명 글자 알파 확인. 실제 게임 애니메이션 미검증. **ISO 미생성·미수정**. 다음 통합은 `reports/user_sys031_v1.json`과 앞선 sys009/sys015 사용자 보고서의 pending_assets를 함께 반영.

## 준비 당시 기록 (아래 3장 모두 현재 ISO 반영 완료): 사용자 sys015 PSD 정렬 보정 (2026-09-20)

`outputs/user_sys015_v1`에 원본 PSD/문구별 보정 PSD/미리보기. 사용자 글자 모양·문구·내부 자간을 유지한 정수 픽셀 이동으로 21개 메뉴 칸 중앙과 선택/비선택 위치 보정. 외곽선 효과 복원. `build/user_sys015_v1/textures/STATUS/status/sys015.tm2` 준비. 지정 칸 밖 인덱스, 팔레트/헤더/파일길이 보존 및 불투명 글자 알파 확인. **ISO 미생성·미수정**, 실제 게임 미검증. `reports/user_sys015_v1.json`과 앞서 등록한 `reports/user_sys009_v1.json`을 다음 통합에 함께 반영. 폐기했던 15장 자동 식자와 별개의 사용자 작업본.

## 준비 당시 기록 (아래 3장 모두 현재 ISO 반영 완료): 사용자 sys009 PSD (2026-09-20)

사용자 제공 `sys009.tm2.psd`의 결정·취소·선택을 채용. 원본 PSD는 `outputs/user_sys009_v1`에 해시 일치 복사. `build/user_sys009_v1/textures/STATUS/status/sys009.tm2` 준비. 보고서/다음 통합 목록은 `reports/user_sys009_v1.json`. 세 문구 밖 인덱스, 팔레트/헤더/파일크기 보존 및 불투명 글자 알파 확인. 실제 게임 검증 미실시. **ISO 생성·수정 없음**, 현재 캐릭터 이름판 통합 ISO에는 아직 미반영. 이전에 폐기한 15장 자동 식자는 복원하지 않음.

## 이전 기반 ISO: 캐릭터 이름판 통합 v1 (2026-09-20)

`build/character_tabs_ko_v1/Poison Pink (Japan) - Korean character names v1.iso`
SHA-256: `703b15e773dc21bb668a748a13cea79e673f402324e74ec8439ae5efdfbe4efb`.

기존 영상 자막·대사 검수·전투조건 표시 보정판에 `STATUS/status/chr_cel/csl_tb0~4.tm2` 5장/12명만 추가. EBS 주시경체 Bold, 원문 폭·높이에 맞춘 식자. 전체 ISO 비교 및 5멤버 재읽기 통과, 변경 범위 밖 모든 바이트 동일. 실제 게임 검증 미실시. CRC7502FF83 호환 패치 sidecar/ZIP 동봉. `reports/character_tabs_ko_v1.json` 참조.

후속 STATUS 15장 을지로체 작업은 사용자 요청으로 폐기했으며 포함하지 않음. 원본 추출 파일은 보존. 원본 영상 자막의 미확정 구절 등 기반판 한계는 아래 기록 유지.

## 이전 기반 ISO: 영상 자막 + 전투조건 표시 보정 v1 (2026-09-20)

`build/battle_condition_display_v1/Poison Pink (Japan) - Korean movies and battle display v1.iso`
SHA-256: `ca5069ad208cbbc7d063681daaa2fd89852bfd88f9ce5a8dbd04bd6cbc859040`.

사용자 게임 스크린샷에서 제목 축소/패배조건 하단 잘림 확인. 제목 실제 높이가 원본37.5 대비25.5/26이었던 식자 오류, 패배본문 UV 높이약40을 텍스처 전체64로 취급한 패킹 오류를 수정했다. 승리/패배 제목 원본 높이로 보정, 주인공·테이지 전투불능 두 문구를 실제UV 안으로 재배치. 네 효과×4문구=16PSD/9TIM2 수정. 원본 UPL/UV/팔레트/헤더/파일크기 변경 없음.

- 기존 `outputs/battle_lettering_work_v3` 안에 갱신, 이전16PSD/PNG/manifest/README는 `표시범위_크기보정전_보존.zip`에 검증 보존. 원문과 이전 작업 숨김 레이어 유지. 범위 밖143PSD 해시 동일.
- 원본 영상 자막v1 ISO 기반이므로 기존 대사검수v4 + MOVIE13편/149자막 유지. 주제가 잠정/생략 구절은 아래 영상 기록과 `청취_확인필요.json` 참조.
- 도구: `battle_workbench_v3.defeat_geometry()`에서 실제 UV사각형 산출; `build_battle_titles_euljiro.group_images()` 제목 원본높이 및 본문여백 보정. `tools/fix_battle_condition_display.py` 준비→`--install`→`--build`, `tools/finalize_battle_condition_display.py` 기록.
- 네 문구 저장후 기본/검정 IoU .927~.972, 검정기본피복 .961~.986. 7개 관련검사 통과. 전체ISO 계획범위밖 동일 및9멤버 재읽기 통과. MOVIE/대사/기타이미지 유지. CRC7502FF83/34곳 호환 sidecar/ZIP 동봉.
- **새 수정본 실제 게임 화면 검증 미실시.** 사용자 설정/카드/상태저장 무변경. 새로 부팅 후 게임내 저장 불러오기 권장.

## 이전 기반 ISO: 원본 영상 자막 v1 (2026-09-20)

`build/movie_subtitles_v1/Poison Pink (Japan) - Korean movie subtitles v1.iso`
SHA-256: `168d0d707f4f77c4163954912832d021a5b51e6cf93cd22cfe2f20cc40af642a`.

대사 검수 v4를 기반으로 원본 IPU 13편에 자막149개(대화8편/67개, 주제가5편/82개) 반영. 기존 MP4 재사용 없음. 원본 AG15개 바이트 보존, s01/s15 원본 영상 보존. 기존 사용자 이미지·레터링·시스템·텍스트·ELF는 MOVIE 범위 밖 전체 동일 검사로 유지 확인.

- 입력/자료: `localization/movie_subtitles_v1.json`, `extracted_movies/korean_reviewed_v1/`. 기존 SRT 보존. 자동 인식 원자료는 `asr_unreviewed/`이며 적용본 아님.
- 빌드 순서: `tools/author_movie_subtitles.py` → `tools/export_movie_subtitles.py` → `tools/export_movie_review_notes.py` → `tools/build_movie_subtitle_assets.py` → `tools/build_movie_subtitle_iso.py` → `tools/finalize_movie_subtitles.py`. author 도구에 번역을 보관하므로 JSON을 직접 수정한 뒤 author를 재실행하면 덮어쓰는 점 유의.
- IPU 출력 해상도·프레임 수·플래그 유지, 사용 프레임의 MPEG-2/IPU 왕복 픽셀 일치 검사. 원본 프레임 보존(s04 기존자막 영역, s14 크레딧 배치 제외), 모든 멤버 재읽기, 전체 ISO 계획 범위 밖 동일 통과.
- s04 원래 일본어 자막 영역을 한글로 대체. s10~s13 그림 아래 빈 공간에 가사. s14는 크레딧 보존을 위해 전체 영상을 같은 비율의576×432로 축소하여640×480 안에 배치, 하단48픽셀 가사 공간, 전체 프레임 재압축. 재압축 손실 있음.
- **가사 완전 확정본 아님:** s09 주문 수식어/주제가1절 술어 일부 생략, s14 약172~178초 잠정 번역 및 문맥 보정 구절 존재. `청취_확인필요.json` 필수 참조. 공식 가사집과 전곡 청취 확정 미실시.
- 검증: `reports/movie_subtitles_v1.json`, `build/movie_subtitles_v1/asset_report.json`. CRC7502FF83/34곳 호환 패치 sidecar/ZIP 동봉. 실제 PCSX2 영상 재생 검증 미실시. 사용자 설정·카드·상태저장 무변경.

## 이전 기반 ISO: 대사 검수 v4 (2026-09-20)

`build/semantic_revision_v4/Poison Pink (Japan) - Korean dialogue revision v4.iso`
SHA-256: `648097edc8f2b19d8efb750e916d769aa8cd128c75323b9d379d08ed6003edc4`.

기존 v3 테이지 주요 이벤트 이후 나머지 RTB 대사 114,299개 저장 위치/13,714개 원문·기존번역 조합을 읽고 대조했다. 다른 인물 루트, 마을, 전투, 개별 이벤트·엔딩을 포함한다. 6,158개 단위/21,533곳/254개 RTB 수정. 인물 말투, 주체·부정·관용구 오역, 이름·쌍격 등 표기 보완. 5개 방언·운문 해석 불명확 단위는 기존 번역 유지. 대사 읽기 검수 완료와 전체 게임 번역 품질 보증은 다르며 전체 DB·이미지 용어 검수는 별도다.

- 입력: `localization/semantic_revision_v4/changes.jsonl`, `decisions.json`, `pending_context.json`, `preflight.json`.
- 도구: `tools/prepare_semantic_revision_v4.py`, `tools/build_semantic_revision_v4.py`, `tools/export_semantic_revision_v4.py`, `tools/finalize_semantic_revision_v4.py`.
- 편집본: `outputs/translation_review_20260920/applied_v4/structured_ko_reviewed_v4.tsv` (128,274행, 원문·ID·위치 보존). 수정내역, 전체대사 검수대본, 검수결과, 문맥확인보류 동봉.
- 정적 검사: 문자표 왕복·255바이트·한 줄36바이트 예산 통과. RTB 비문자 명령/분기·미수정 문자열 보존. ISO 전체 계획 밖 동일, 254멤버 재읽기 확인. RTB6+DB9+호환12 검사 통과.
- 기존 사용자 이미지·레터링·폰트·ELF 및 v3 DB 수정 유지. CRC7502FF83 호환 패치34곳 검사 및 sidecar/ZIP 동봉. 실제 플레이/음성 대조 미실시. 사용자 카드/상태저장/설정 무변경.
- 아래 v3 이하의 미검수 범위 표기는 당시 이력이다. 최신 실행·편집 기준은 v4.


## 이전 실행 ISO: 문맥 수정 v3 (2026-09-20)

`build/semantic_revision_v3/Poison Pink (Japan) - Korean dialogue revision v3.iso`
SHA-256: `881c853e669fd3b7139add937b5af35e81bf85c32460128e6f356eb1a7ae537f`.

1126곳(대사930/DB196) 반영, 고유 원문·수정문·종류 조합903종. 테이지 주요 이벤트 ft_01~ft_16 및 ft_99의 장면 원문 대조와 말투 보완. 중복 분기를 명시적 ID로 수정. 이전340행 초안도 포함하며 장비명 용량 초과는 ‘교황의 성스런 봉’으로 해결. 다른 루트의 개별 확정 오역도 포함하나 **전체 게임 수동 문맥 검수는 미완료**. 다른 인물 루트, 마을/전투 대사, DB/이미지 용어 일관성 검수가 남는다.

- 적용 입력 `localization/semantic_revision_v3/changes.jsonl`; 준비/빌더 `tools/prepare_semantic_revision_v3.py`, `tools/build_semantic_revision_v3.py`.
- 최종 편집용 `outputs/translation_review_20260920/applied_v3/structured_ko_reviewed_v3.tsv`, 비교표 `수정내역.tsv`, 대본 `테이지_장면별_검수대본.tsv`, 설명 `검수결과.md`.
- 검증 `reports/semantic_revision_v3.json`: 전체 ISO 계획 범위 밖 동일, 36멤버 재읽기, RTB 명령/분기·DB 수치·미수정 문자열 보존. 변경379859바이트. 문자누락/용량초과 없음. RTB6+DB9+호환12검사 통과.
- 기존193개 레터링/사용자 이미지/시스템 번역/폰트/ELF 보존. CRC7502FF83, 기존 대화 표시 패치 계속 필요. sidecar/호환 ZIP 동봉. 신규 실제 플레이 검증 미실시. 카드/상태저장/사용자설정 무변경.
- v1/v2는 이번 작업의 중간 결과이며 실행 기준은 v3. 아래 ‘ISO 미변경’은 이전 초안 작성 당시 이력이다.

## 이전 이력: 번역 의미 검수 초안 (2026-09-20)

사용자가 문맥 오역을 지적해 적용 텍스트118,668행/중복묶음16,112건을 전수 자동대조. 실제 대사/DB 검수에서 방향·행위자·부정 반전, 僕/命 다의어, 관용구, 스킬 단일대상→단체, 장비명 심각한 오역 확인. `outputs/translation_review_20260920/검수결과.md`와 `summary.json`. 자동후보1,005건은 확정오역이 아님. 수동수정안340행(대사144/이름139/스킬57),255종을 보존초안으로 작성. **전체 수동 문맥 검수 미완료. ISO 미변경.** 기존 번역기술검사는 의미검수를 보증하지 않음.

`tools/review_translation_semantics.py`는 적용 plan+후속system기록을 읽고 동일 함수/원문/기존번역에만 대사수정을 연결. `localization/review_20260920/dialogue_fixes.txt`, `term_fixes.txt`가 수동근거. 초안`structured_ko_reviewed_draft.tsv` 원문/ID/위치열 보존 및 TSV왕복 확인. 기존 문자표 인코딩확인. `教皇の聖杖` 수정안만22>18byte로 적용보류 필요. 기존 plan/TSV/ISO는 그대로. 다음 작업은 남은 장면 의미검수, 프로젝트전체 이름/말투 일관화, 안전한 새빌드입력 연결. 기초권장도구의 자동후보를 전부 오역으로 주장하거나 340행을 ISO반영완료로 오인하지 말 것.

## 이전 기반 ISO: 전체 작업 통합 (2026-09-20)

`build/korean_integrated_20260920/Poison Pink (Japan) - Korean integrated 20260920.iso`

SHA-256: `2adb730382015a49d69d850445a7d8950fb9efdc313610c9610259d7acea942c`.
기존 heading alignment v1 위에 포획56 + 계층/장소112 + 조건25 = 193개 TIM2를 반영했다. 조건16개는 마지막 spacing_euljiro_v2 우선. 최신 v3 작업PSD150개 해시 전부 일치. 193텍스처 헤더/팔레트/길이 보존 및 ISO 재읽기 해시 확인, 전체 ISO 비교로 범위 밖 모든 바이트 동일 확인. 실제 변경1,287,778바이트. 대사/폰트/시스템/튜토리얼/타이틀은 검증된 기반 그대로 유지.

대화 미표시 해결은 여전히 PCSX2 호환 패치로 제공한다. ELF CRC7502FF83/패치34곳 및 주변 코드 검사 통과, `.iso.pcsx2`와 `PCSX2_대화표시_호환패키지.zip` 동봉. 사용자 프로필 읽기 전용 검사 findings=[]; 패치 일치·와이드스크린 ON·16:9·Software 확인. 사용자 설정/세이브/카드 변경 없음. 호환 회귀검사12개 통과. 이번 통합 ISO의 신규 런타임 검증은 하지 않았으며 이전 대화 표시 런타임 증거는 `reports/dialogue_missing_fix.json`.

빌더: `tools/build_korean_integrated_20260920.py`. 통합 기록: `reports/korean_integrated_20260920.json`. 실행 설명: 통합 폴더 `먼저읽기.md`. 원본과 기존 ISO/작업본 보존. **아래 기록의 ‘준비만 됨/ISO 미적용’은 당시 이력이며 위 193개는 현재 통합 완료.** 원문 템플릿 상태인 별도 OVERKILL/BIND/CAPTURE 연출은 새 번역 대상에 포함하지 않았다. 포획 이름 5종의 텍스트 DB 동기화는 여전히 미실시.

## 승리조건 본문 원문 폭·자간 보정 (2026-09-20)

사용자가 글자가 좁게 붙는다며 원문 기준 폭/자간 조정을 요청. 4개 승리 본문(모든 적/루나셰/보스/발드 왕)×4효과16PSD를 기존 v3에서 갱신. `tools/build_battle_titles_euljiro.py:emphasis_mask`를 실제 글자 픽셀 경계별 배치로 변경, 원문 기본 텍스처 각 줄 폭/시작 위치 참고, 테두리 사이 최소3nativepx 보장, 강조/보조64% 유지. 모든적 문구는 첫줄165.75→217px, 둘째157.25→190px; 강조55.5/보조35.5px 그대로. 원문시작점 대비 안전여유1/0.5px만 이동. `tools/revise_battle_spacing.py`로 준비/검증/설치. 네검정효과 복원IoU .9654~.9722, 기본/검정 원본공통알파 동일. 기존16PSD/PNG·메타데이터는 v3 루트 `을지로체_자간보정전_보존.zip` 보존, 범위외143PSD 유지. `reports/battle_spacing_euljiro_v2.json`. **다음 ISO에서는 `build/battle_spacing_euljiro_v2/textures/`의16개를 이전 titles_euljiro_v1보다 우선 적용해야 한다.** v3 총150작업PSD는 동일. ISO/런타임 미변경, 최신 실행용은 heading alignment v1.


## 계층·장소명 및 조건 전체 을지로체 식자 (2026-09-20)

사용자의 전체 식자 요청과 후속 강조 지시 반영. `localization/battle_titles_euljiro.json` 62문구(계층장소54+제목2+본문6), `tools/build_battle_titles_euljiro.py`로 기존 v3의86PSD를 식자본으로 갱신. 원문과 이전 한글 숨김 참고 레이어 유지, 전체 기존86PSD/메타데이터는 v3 루트 `을지로체_자동식자전_보존.zip`에 바이트 그대로 보존. 범위 밖73PSD 유지(전체159=작업150+원본보존9). 승리 본문은 대상 이름과 '격파'를 크게, 조사/어미는64%로 작게 하며 특히 '모든'·'격파' 강조. 같은 실루엣에서4효과 파생, 검정은 흰 테두리 전체 포함. 54계층장소→별칭112텍스처+조건25텍스처=총137개 게임용 TIM2 준비. `build/battle_titles_euljiro_v1/textures/`. 8세트 검정/기본 복원IoU .9329~.9747, 기본영역 피복 .9651~.9871. 원본 헤더/팔레트/크기/UV 밖 인덱스 유지. 장소050040/070020만 원본 팔레트최소알파1로, compile_texture에 명시적 allow_original_alpha_floor 옵션 추가(기본엄격검사는 유지). 신규5+기존alpha2+heading3=10검사 통과. 원문 기준040020브라지언덕/040030루돈전선기지, startmap 목록순서와다름 주의. ELF/TSV 미변경. `reports/battle_titles_euljiro_v1.json`. **ISO 미변경/런타임 미검증**, heading alignment v1이 최신 실행ISO. 다음 빌드에는 이전포획56+이번137텍스처를 합쳐 반영 가능. 사용자 요청 범위 밖 오버킬/구속/CAPTURE 작업은 그대로.


## 포획 알림 을지로체 식자 완료 (2026-09-20)

사용자 요청 폰트 `<LOCAL_USER_HOME>/Library/Fonts/BMEULJIROTTF.ttf`로 BATTLE/battle/catch의 마신 이름55개+捕獲!!1개를 식자했다. 기존 v3에 `14_포획알림_catch_*.psd`56개, 투명 PNG56개, 팔레트 변환 후 목록JPG5장 추가. 원문 숨김 레이어, 밝은 글자와 어두운 테두리 분리 픽셀 레이어. 한줄 공통좌표→UAD 두 조각/기준점 배치. 원본52개4bpp+4개8bpp, 헤더/팔레트/파일길이 유지, 밝은RGB232 저장알파128 검사. 원문56개 배치왕복, PSD 합성 1단계 반올림 허용 비교, 기존 v3 exporter 대표3형식 픽셀정확 일치. 기존 PSD103개 보존. v3 총150작업PSD/197원본텍스처. `localization/capture_notice_euljiro.json` 이름 대응표, `tools/build_capture_notice_euljiro.py`, `reports/capture_notice_euljiro_v1.json`. 아니마뉴크스/탄클페어/아크니스/엑 아크니스/캔서기가스5종 오역 보완은 식자만 반영; DB 동기화는 미실시. 게임용 TIM2는 `build/capture_notice_euljiro_v1/textures/`. **ISO 변경 없음, 실제 게임 미검증.** 최신 실행 ISO는 heading alignment v1 유지.


## 작업본 추가: 전투 시작 계층명·장소명 (2026-09-20)

사용자 요청으로 새 버전 폴더 없이 기존 `outputs/battle_lettering_work_v3/` 바로 아래에 `12_계층명_*.psd` 10개와 `13_장소명_*.psd` 44개를 추가했다. bt_ar/bt_nm 전체 112개를 원본 바이트 해시로 중복 제거한 54종이며, 기존 40개를 합쳐 작업 PSD 94개다. 원본 텍스처는 총 141개. 두 줄 저장 텍스처를 한 줄 작업 공간으로 펼쳤고 원문 레이어·가이드를 제공했다. bt_name_std.upl의 연속 사각형/UV 확인, 108개 조각 알파/가시 RGB 왕복, 신규 PSD 216레이어 디코드, 3개 회귀 검사 통과. 패커가 동일 원본의 별칭 전체에 반영하도록 추가했다. 기존 PSD 49개(작업40+보존9)의 현재 해시 유지. 회색의 왕궁은 `13_장소명_bt_nm_010020.psd`, 계층은 `12_계층명_bt_ar.psd`. 목록 JPG 6장과 ZIP 갱신. ISO·번역 미변경, 실제 게임 표시는 미검증. `reports/battle_stage_titles_v3.json`, 도구 `tools/add_battle_stage_titles_v3.py`.

## 최신 작업본: v2 전체 범위 공통 좌표 재구성 (2026-09-20)

`outputs/battle_lettering_work_v3/`와 ZIP을 제공했다. 원본 텍스처 29개, 공통 좌표 PSD 40개, 문구 폴더 11개. 각 PSD에 원문 해당 효과·기본 원문·가이드·빈 한글 레이어를 넣고 기존 작업도 보존했다. 수정된 v2 PSD 8개와 추가 제목 사본 1개를 바이트 그대로 별도 복사했다. 주인공 전투불능의 주황 높이와 검은 전체 실루엣은 편집용 사본에서 보정했고 보정 전도 숨김 참고로 유지했다. 조건은 UPL 역변환, 마신 포획 계열은 UAD 조각·기준점을 사용하며 후자는 타이밍/스케일 연출 미검증이다. `tools/battle_workbench_v3.py`는 PSD의 참고 레이어를 제외하고 원래 atlas PNG로 출력한다. 6개 회귀 검사, 280개 PSD 레이어 디코드 검사 및 기존 작업 포함 16개 문서→9개 atlas 내보내기 통과. Photoshop 앱 직접 검증·ISO 적용은 하지 않았다. 현재 ISO는 아래 heading alignment v1 그대로다. 사용자는 이제 v3에서 편집한다. `reports/battle_workbench_v3.json`, 작업법은 `outputs/battle_lettering_work_v3/먼저읽기.md`.

## 최신: 승리조건·패배조건 제목 빨간 효과 정렬 (2026-09-19)

최신 ISO는 `build/battle_heading_v1/Poison Pink (Japan) - Korean heading alignment v1.iso`, SHA-256 `22b4219433f1e3d3d429c1cc6bc37738ea463163782b53d6e1ec47d1c4ea8c58`이다. 기존 본문 보정에서 제외됐던 bt_tx04의 두 제목 빨간 효과를 수정했다. 기본 제목 네 글자의 실제 메시 배치에 맞추고 승리·패배 각각의 빨간 효과 정점/UV를 역산했다. 검은 효과 수정본 위에서 빨강 영역 3,279바이트만 변경했으며 다른 자산·번역은 동일하다. 총 15개 테스트와 전체 ISO 차이 검사를 통과했다. 별도 PCSX2 Software, 16:9, 1/2 속도로 첫 전투 소개를 촬영해 두 제목의 빨간 효과 정렬을 확인했다. 원본 사용자 PSD·슬롯 1 보존, 테스트 프로세스 종료·설정 복원 완료. 공통 작업본은 `outputs/battle_headings_aligned_v1/` 및 ZIP이며 기준 PSD는 참고용, 빨간 효과 PSD 두 장만 패커 입력이다. [상세](docs/BATTLE_HEADING_ALIGNMENT.md), `reports/battle_heading_alignment_v1.json`.

## 최신: 검은 글자 효과의 테두리 누락 수정 (2026-09-19)

최신 ISO는 `build/battle_shadow_v1/Poison Pink (Japan) - Korean battle shadow fix v1.iso`, SHA-256 `7cc52fc3027ed9ec51aa8ffd60ec29fc0864995f1613032bab72d6c67c8ee1b7`이다. 이전 생성기가 bt_tx08에 문자 속 획만 넣어 흰 테두리의 검은 효과를 누락했다. 원본 05/08은 전체 실루엣이 99.645% 일치한다. 이제 기본 글자의 최종 합성 알파(테두리 포함)를 검은 효과에 사용한다. bt_tx08의 4,469바이트만 바뀌고 다른 자산·번역은 동일하다. 공통 작업본은 `outputs/battle_lettering_aligned_v4/`와 ZIP으로 갱신했다. 12개 검사 통과. 복제 세이브·카드의 별도 PCSX2 Software에서 1/4 속도 촬영으로 검은 단계와 패배조건 원본을 확인했고, 이전 v3에는 밝은 테두리가 남지만 수정본은 어두워진 뒤 사라짐을 비교 확인했다. 사용자 PSD와 상태저장 보존, 테스트 앱 종료·설정 복원. [상세](docs/BATTLE_SHADOW_FIX.md), `reports/battle_shadow_fix_v1.json`.

## 최신: 본문 효과 정렬 및 공통 좌표 PSD (2026-09-19)

최신 ISO는 `build/battle_registration_v2/Poison Pink (Japan) - Korean battle lettering aligned v3.iso`, SHA-256 `3f3e8c39ed023aee41e9ddb1205c3d76ccd9c92c4dfe51cdfd5a738ff852f7f1`이다. 사용자가 원한 방식으로 본문 4장을 같은 크기·자간·위치의 PSD로 편집하고, 패킹 단계에서 원본 UPL 배치를 역산하도록 변경했다. 작업본은 `outputs/battle_lettering_aligned_v3/` 및 ZIP. 추출 원본은 TM2 재해독과 완전 일치하며 잘린 것이 아니었다. 기존 기본 글자 bt_tx05는 동일하고 bt_tx06~08의 8,442바이트만 수정했다. 11개 검사와 ISO 전체 차이 검사를 통과했고, 별도 PCSX2 Software에서 첫 전투 소개의 불꽃·본문 빨간 테두리 정렬·주황 윤곽 전환을 확인했다. 검은 실루엣은 유지·미세 정렬했으나 단독 효과를 분리 검증하지 않았다. 제목 bt_tx04와 다른 조건은 이번 변환 대상이 아니다. 원본 사용자 PSD·사용자 세이브·카드 보존. 테스트 앱 종료 및 설정 복원. [상세](docs/BATTLE_LETTERING_ALIGNED.md), `reports/battle_lettering_aligned_v3.json`.

## 추가 점검: PCSX2 보정 재발 방지·테스트 키 충돌 수정 (2026-09-19)

`iso_archive_stage.overlay`의 ISO 공개 전에 최종 ELF 식별값·보정 34곳·주변 명령을 검사하고 CRC별 `.iso.pcsx2` 보정 패키지를 자동 생성한다. 충돌 시 ISO 공개를 막는다. 현재 ISO에도 패키지를 생성했고 ISO 바이트는 동일하다. 프로젝트 테스트 키 △/□/L1의 F5/F6/F9가 영상 모드·화면 비율·렌더러 전환과 중복된 것을 발견해 에뮬레이터 단축키 세 개를 해제했으며 `runtime_keys.py`에 입력 전 검사도 추가했다. 사용자 프로필에는 키 충돌·추가 누락 패치·오래된 게임별 설정이 없고 슬롯 1 보정값도 정상이다. 복제 카드로 마을·저택·츠바키히메 관·도감을 확인했다. 전체 게임 검증은 아니다. [점검 기록](docs/RUNTIME_COMPATIBILITY_AUDIT.md), `reports/runtime_compat_review.json`.

## 최신: 첫 대화 본문 미표시 수정 (2026-09-19)

원본 CRC `F7786EE4`에만 적용되던 PCSX2 번들 와이드스크린·대화창 보정이 한글판 CRC `7502FF83`에서는 빠져 하단 영역이 본문을 가렸다. 원본 보정 ON/OFF와 한글판 새 게임으로 재현·수정을 확인했다. 번들 패치의 34개 주소를 검사하고 사용자 PCSX2 `patches`에 한글판용 파일을 설치했다. 상태저장 1번도 원본 백업 후 보정 34곳과 저장된 대화창 좌표 2곳을 반영한 복구본으로 교체했으며 실제 로드 표시를 확인했다. 사용자 기존 창에서도 대사가 보인다. 메모리카드 2개는 해시 동일, ISO는 아래 최신본 그대로다. 이후 ELF CRC 변경 시 이 호환 패치도 주소 재검증 후 갱신해야 한다. [상세 기록](docs/DIALOGUE_DISPLAY_FIX.md), `reports/dialogue_missing_fix.json`, 배포용 `outputs/pcsx2_dialogue_compat/`.

## 최신: 사용자 승리·패배 및 적 격파 PSD 적용 (2026-09-19)

최신 ISO는 `build/battle_conditions_psd_v1/Poison Pink (Japan) - Korean battle conditions v1.iso`, SHA-256 `41021fe51f65c13eb12dbf122f251beaa5a742b287f79f2c2ca05a773bb36b8f`다. 사용자 제목 사본 PSD와 적 격파 PSD 4개를 `bt_tx04~08`에 적용했다. 원본 일본어 참고 레이어를 제외하고 표시된 사용자 레이어를 이름과 무관하게 포함했다. 기본 글자와 실루엣 위치를 맞추되 붉은색·주황색 효과의 원본 별도 배치는 유지했다. 전체 ISO 비교에서 63,116바이트만 변경되고 기존 번역·타이틀·기타 자산은 동일하다. 정적 검사·변환 그림 검수 완료, 실제 애니메이션의 겹침과 표시는 미검증이다. 사용자 원본 PSD는 변경하지 않았다. 이후 빌드의 기본 채용 자산에 5개를 추가했다. [상세 기록](docs/BATTLE_CONDITIONS_USER_PSD.md), `reports/battle_conditions_psd_v1.json`. 아래 작업본 미적용 기록은 이 적용 이전 이력이며, 나머지 식자 작업본은 아직 적용되지 않았다.

## 정정: 연출 형태별 식자 작업본 v2 (2026-09-17)

사용자가 글자의 연출 전·중·후 형태 누락을 지적했다. v1은 일반 글자·테두리 분리만 제공하여 요구를 잘못 반영했다. `outputs/battle_lettering_work_v2/`와 ZIP에 원본 형태별 PSD 29개, 비교판 10개, 원본 자료를 제공했다. v2는 원문 형태를 그대로 4배 확대하고 빈 한글 식자 레이어를 넣은 작업본이다. 새 한글 식자나 ISO 적용은 하지 않았다. 조건 문구 4개 텍스처가 시간상 4단계라는 뜻은 아니며 실제 연출 순서는 미확인이다. 87개 PSD 레이어 왕복 확인. 상세 설명은 해당 폴더 `먼저읽기.md`. v1을 올바른 효과 재현 작업본으로 간주하지 않는다.

## 작업본: 승리·패배 조건과 마신 포획 식자 (2026-09-17)

사용자 요청으로 `outputs/battle_lettering_work_v1/` 및 동명 ZIP에 한글 초안 PSD 11종을 만들었다. 조건 8종, 오버킬·구속·포획 3종. PSD는 6개 픽셀 레이어이며 문구 편집 SVG·4배 투명 PNG·원배율 참고본도 있다. 원본 29개 텍스처와 UAD·전투 시작 연출 자료를 보관했다. 문구 전체를 편집하는 논리 캔버스이므로 원본 atlas/UV 재배치와 효과 생성은 미완료다. 66개 PSD 레이어 왕복 검사·PNG 알파 검사·미리보기 검수 완료. Photoshop 실행 검증은 미완료. 이번 초안은 사용자 최종 수정본으로 채용하거나 ISO에 반영한 것이 아니다. 최신 ISO는 아래 타이틀 알파 수정본 그대로다.

## 최신: 타이틀 흰색 저장 알파 선택 수정 (2026-09-17)

최신 ISO는 `build/title_alpha_v1/Poison Pink (Japan) - Korean title alpha fix.iso`, SHA-256 `6abf192f3a386b4e1bbc781bba7d02d2e1bdfa04894640b2cda4b6be0aeb4a56`이다. 사용자 보고를 조사한 결과, 클리핑된 PNG 미리보기에서 서로 같아 보이는 흰색 팔레트 중 저장 알파 140을 잘못 선택한 변환기 오류를 찾았다. 이전 PSD 적용본의 순백색 3,172픽셀 중 3,151픽셀이 해당했다. 불투명 입력은 같은 미리보기 색 중 저장 알파가 가장 높은 항목을 선택하도록 고쳤고 이제 순백색 모두 원본과 같은 저장 RGBA (255,255,255,255)다. 전체 ISO에서 타이틀 인덱스 4,753바이트만 변경됐고 나머지는 동일하다. 관련 검사 6개 통과. 실제 게임 표시 검증은 미완료다. 아래 PSD v1의 ‘정확한 흰색 보존’ 설명은 클리핑된 미리보기만 검사한 것으로 저장 알파 보존을 뜻하지 않으며 이 기록으로 정정한다. [자세한 수정 기록](docs/TITLE_ALPHA_FIX.md), `reports/title_alpha_v1.json`.

## 최신: 사용자 PSD 타이틀 적용 (2026-09-17)

사용자가 수정한 `tit_tx01.tm2.psd`를 540곳 시스템 문구 통합본 위에 적용했다. 최신 ISO는 `build/title_psd_v1/Poison Pink (Japan) - Korean system and title v2.iso`, SHA-256 `28045de9491f9cbf9f7819b539c6381d0e7525086c67335f74b128e1e562fb94`다. 저장된 PSD 합성 이미지를 올바른 투명도로 읽어 크기·디자인을 유지했다. 불투명 순백색 3,172픽셀 모두 게임용 텍스처에도 정확히 보존됐다. 시작 안내의 순백색은 이전 223픽셀에서 554픽셀로 늘었다. 전체 ISO에서 타이틀 텍스처 인덱스 12,557바이트만 변경되어 기존 시스템 문구·대사·다른 이미지가 유지됐다. 이 PSD를 타이틀 메뉴 기본 채용본으로 갱신했다. 실제 게임에서의 확대·밝기·필터 효과는 검증하지 않았다. [적용 기록](docs/TITLE_PSD_V1.md), `reports/title_psd_v1.json`.

## 최신: 시스템·공통 UI 번역 통합 (2026-09-17)

사용자가 저장·로드·메모리카드·게임 설정과 그 밖의 필요한 문구 번역을 요청했다. `SLPS_258.54`의 확인된 플레이용 문자열 **540곳**을 추가 반영했다. 최신 ISO는 `build/system_messages_v1/Poison Pink (Japan) - Korean system v1.iso`, SHA-256 `d78c7ae9fc1bf691f76e46e117802c83a131652b743ffd72b1d66603eab4ecbd`다. 기존 대사·DB·사용자 이미지 28개를 바이트 단위로 보존했다. 폰트는 3,148글리프이며 기존 3,136개는 그대로다. 전체 ISO 차이 18,622바이트와 관련 검사 18개를 통과했다. 메모리카드 연속 문구의 NUL 위치를 유지했으며 나데시코 이름 1개의 확인된 테이블 포인터만 옮겼다. 게임 내 화면 검증은 아직 하지 않았다. 자세한 범위와 한계는 [시스템 문구 적용 기록](docs/SYSTEM_MESSAGES_KO.md), `reports/system_messages_v1.json`을 따른다.

### PCSX2 실행 시 주의할 확인된 문제

2026-09-17 사용자가 첫 전투 로딩 직후 종료를 보고했다. 당일 두 macOS 충돌 기록은 PCSX2 2.6.3의 GS 스레드 `pxOnAssertFail → GSDeviceMTL::DoStretchRect`에서 SIGABRT다. 앞선 튜토리얼 시험도 같은 오류가 있었고 Software 렌더러로 바꿔 진행에 성공했다. 새 ISO는 Software로 실행하도록 안내한다. 최신 번역본의 같은 장면을 직접 비교하지 않았으므로 패치 영향까지 배제한 결론은 아니다. [이전 Software 검증](docs/TUTORIAL_BATTLE_RUNTIME.md).

## 최신: 사용자 TSV 보완 후 적용 (2026-09-17)

사용자가 오류 보완과 적용을 승인하여 대사·화자 RTB 116,616행, DB 1,388행, 검증된 ELF 문구 124행을 반영했다. 최신 ISO는 `build/user_translations_v1/Poison Pink (Japan) - Korean text v1.iso`, SHA-256 `7a9f425a5bfc883d94349888445b87684c66315b854782b7c69fa4468c63b3e8`이다. 사용자 이미지 28개와 기존 글리프 2,212개를 보존하고 총 3,136개 글리프로 확장했다. 설정 파일 2행과 미확인·내부용·길이 초과 ELF 등은 제외했다. 전체 ISO 범위 검사와 관련 테스트 27개가 통과했고 실행 검증은 보류한다. 수정 TSV·보류 목록·자세한 적용 범위는 [사용자 번역 적용 기록](docs/USER_TRANSLATIONS_20260917.md)과 `reports/user_translations_applied_20260917.json`을 따른다. 아래의 검수 보류 기록은 해결 전 이력이다.

## 최신 검수: 사용자 TSV 2종 적용 보류 (2026-09-17)

사용자가 전달한 `elf_strings_ko_final_v4.tsv`와 `structured_ko_working_translated.tsv`를 원본과 대조했다. 행·ID·원문·위치 열은 모두 보존됐으며 변경 번역은 각각 2,179행과 118,006행이다. 입력 사본은 `localization/imports/20260917/`에 보관했다. 게임 전용 글자 `魔凸`의 추출 표시 문제에 따른 ‘마볼록’ 등 532행, DB 이름 저장 한도 초과 7행, ELF 기존 문자열 길이 초과 757행 및 내부 식별자 후보 등이 발견돼 **이번 TSV는 적용하지 않았다**. 상세 수정 목록과 한계는 [검수 보고서](reports/user_translations_20260917/README.md), 전체 행별 진단은 같은 폴더의 `issues.jsonl`을 따른다. 일부 표시는 검토 후보이지 확정 오류가 아니다. 원문 열은 그대로 두고 번역 열만 수정해야 한다. `tools/audit_user_translations.py`는 읽기 전용 검수 도구다. 최신 ISO와 채용한 사용자 이미지는 아래 2026-09-16 통합본 그대로 유지한다.

## 최신: 추가 도움말·미니게임 10장 통합 (2026-09-16)

최신 ISO는 `build/tutorial_11_user_v1/Poison Pink (Japan) - expanded user help.iso`다. 전달받은 `tutorial_11_KO`의 11개 중 ev150·151·155~162의 번역 이미지 10장을 추가했다. ev154 GAME OVER는 원본과 완전히 같아 유지했다. 기존 사용자 로고·타이틀·전투 메뉴·도움말 14장과 오역 수정 6곳도 보존했다. 원본 크기·알파·팔레트·TIM2 왕복 및 ISO 전체 변경 범위 검증을 통과했다. 자세한 내용은 [추가 이미지 적용 기록](docs/TUTORIAL_11_USER_ARTWORK.md), `reports/tutorial_11_user_artwork.json`, 최신 경로·해시는 `localization/pipeline.json`을 따른다. 사용자 채용 자산은 변경 이미지 27개와 원본 유지 GAME OVER 1개로 총 28개다. 게임 실행 검증은 계속 보류한다. 아래의 과거 최신 경로보다 이 항목이 우선한다.

## 최신: 사용자 도움말 14장까지 통합 (2026-09-16)

최신 ISO는 `build/user_help_artwork_v1/Poison Pink (Japan) - user artwork and help.iso`다. 사용자 로고·타이틀 메뉴·전투 메뉴에 사용자 도움말 `ev136~ev149` 14장을 추가했다. 사용자가 승인한 메뉴 ‘닫기→열기’ 및 ‘뿔 공격→발톱 공격’ 오역은 같은 오류가 추가 확인된 ev140을 포함해 6곳 수정했다. 기존 제작 폰트·배경을 사용했고 수정 사각형 밖의 픽셀은 유지했다. 14장 모두 원본 알파와 동일하고 ISO 전체 비교에서 도움말 범위 535,223바이트만 변경됨을 확인했다. 자세한 결과와 해시는 [사용자 도움말 적용 기록](docs/USER_HELP_ARTWORK.md), `reports/user_help_artwork.json` 및 `localization/pipeline.json`을 따른다. 아래의 이전 최신 ISO 안내보다 이 항목이 우선한다. 이후 빌드에서도 채용한 사용자 자산 17개를 유지한다. 게임 실행 검증은 계속 보류한다.

## 사용자 이미지 기본 채용 방침 (2026-09-16)

사용자가 별도로 지시하지 않으면 직접 제작·편집한 이미지를 기본 자산으로 채용한다. 이후 빌드에도 채용한 사용자 이미지를 계속 포함하고, 해당 자산을 이전 자동 제작본이나 일본어 원본으로 되돌리지 않는다. 현재 기본 자산은 사용자 로고 `tit_lg00`, 타이틀 메뉴 `tit_tx01`, 전투 메뉴 `sys000`이다. 입력 사본 경로는 `localization/pipeline.json`의 `user_artwork_policy.adopted_assets`에 기록했다. 새 사용자 이미지도 규격·투명도·메뉴 조각 위치·문구를 확인해 문제가 없으면 재확인 없이 적용한다. 실제 문제가 발견되면 알리고 사용자 디자인을 임의로 바꾸지 않는다. 게임 실행 검증 보류 방침은 유지한다.

## Latest integrated build: user title and battle menu (2026-09-16)

ISO: `build/battle_menu_artwork_v1/Poison Pink (Japan) - custom title and battle menu.iso`

SHA-256: `d116694d374ef4d1c657ccd0010f32e94dc9349d194f7e8b175781d06d8e4d97`

Includes the user logo, title menu (load/prologue), and reviewed battle-menu sheet. Three texture ranges only: 89,259 changed bytes; battle-menu alpha unchanged. The title textures match the previous user build exactly. The previous title ISO was absent, so this build applies all three images to help_pages_v7. Runtime verification remains deferred. See [details](docs/BATTLE_MENU_ARTWORK.md) and `reports/battle_menu_artwork.json`. This supersedes older latest-build paths below.

문서 버전: 3.4 / 검수일: 2026-09-16 / 대상: 현재 폴더의 `SLPS_258.54`

## 1. 결론과 현재 상태

**최신 빌드는 사용자 제작 타이틀 PNG 2장 적용본이다(2026-09-16).** `tit_lg00 복사.png`, `tit_tx01.tm2 복사.png`를 도움말 v7 통합본에 적용했다. ISO: `build/title_artwork_v1/Poison Pink (Japan) - custom title.iso`, SHA-256 `4ca319947d7dfb3ef9e570094f22e2e81445a8699157c5299ac61b1f64bf231d`. 원본 512×256·256색 팔레트·TIM2 헤더를 유지했고 ISO 전체 비교에서 두 텍스처의 인덱스 49,723바이트만 변경됨을 검증했다. 기존 한글화는 보존됐다. 원본 팔레트에 근사 변환하므로 PNG와 픽셀 단위로 동일하지는 않다. 화면 확인·게임 실행은 사용자 요청대로 보류했다. 입력과 재현 방법은 [타이틀 적용 기록](docs/TITLE_ARTWORK.md), 결과는 `reports/title_artwork.json`이다. 도움말 v7 ISO는 재빌드 기준 및 이전 실행 확인본으로 유지한다.

**현재 우선순위는 번역보다 전체 추출이다.** 사용자 요청에 따라 [원본 전체 추출](extracted/original/README.md)을 완료했다. 11개 아카이브 원본 10,241개와 별도 디스크 파일 39개, 일반·내장 텍스처 4,034개 PNG, 폰트 글리프 2,016개를 확보했다. RTB 280개의 문자열 126,329개와 DB 3종의 필드 1,941개 등을 원문·바이트·위치·빈 번역 칸으로 저장했다. ELF 23,047개와 기타 바이너리 120,046개는 미검수 후보로 분리했다. 이번에는 번역·게임 실행·이미지 열람 검수를 하지 않았다.

중간 ISO **13개를 삭제**했다(파일 크기 합계 55,190,913,024바이트). 당시 원본과 도움말 v7 통합본만 유지했고, 현재는 위 타이틀 적용본을 추가했다. 과거 ISO의 압축 차이 파일 4,787,273바이트와 모든 기존 검증·번역 자료는 보존했다. 각 차이 파일로 복원한 전체 ISO의 SHA-256이 삭제 전 ISO와 같은지 검증했다. 목록과 복원 방법은 [추출 안내](extracted/original/README.md), `reports/iso_retention.json`, `tools/iso_retention.py`를 따른다. **과거 문서의 ISO 경로는 삭제된 시험본을 가리킬 수 있으며, 해당 도구·테스트를 다시 실행할 때 필요한 ISO만 복원한다.**


**타이틀 적용의 기준 표본은 [튜토리얼 도움말 14장 통합본](docs/HELP_PAGES.md)이다.** 제목·본문·페이지 이동 100영역을 번역했고, 기존 UI 통합본 위에 그림만 주입했다. 전체 ISO 509,340바이트 변경·58개 테스트·원본 잠금 검사를 통과했다. ELF·2,212글리프·이전 RTB/DB/UI·UAD·팔레트·파일 위치는 보존했다.

타이틀 적용 전 기준 ISO: `build/help_pages_v7/Poison Pink (Japan) - tutorial help.iso`, SHA-256 `a3f2c6c3fe10fe0ce3d15e78838a235a69730f332550f297e1b32d62f5481630`. 새 부팅에서 ev136~ev140의 5장, 다음·뒤로·닫기, 같은 ISO 상태 복원 1회와 화염 스킬의 전투 복귀를 확인했다. 기존 진행 카드 해시는 유지됐다. 보고서는 `reports/help_pages.json`, `reports/help_pages_runtime.json`이다.

**사용자가 그림 확인을 나중으로 미뤘다. 추가 이미지 확인을 자동으로 재개하지 않는다.** ev141~ev149의 실제 표시와 편집 영역 안의 배경 미술 보완은 QA060 보류다. 그림 속 일본어 메뉴·이름·수치와 장식 영문은 남아 있다. 다음은 추출 카탈로그에서 실제 번역 대상을 선별하는 일이며, 번역 착수는 후속 요청에 따른다.

이전 [스킬 분류·상태·명령 제목 통합](docs/UI_REMAINING.md)의 이미지 10조각·ELF 6곳과 재행동 실행 검증은 유지한다. 액티브/소환 분류·쌍격 발동, QA037 상태 효과·장비 교환, QA044 유효 대상 열기/포획과 전체 P4는 미완료다. 도움말 그림 주입이 이 항목들의 통과를 뜻하지 않는다.

앞선 [상단 제목·공통 선택지 v2](docs/UI_TITLES.md)의 ELF 15곳과 공백 포함 예/아니요 보완은 유지한다. 그 단계에서 실패한 image_gen 시안은 이번 입력으로 사용하지 않았다.

이전 [공통 메뉴·첫 도움말 시험본](docs/UI_PIPELINE.md)은 전투 명령 9종·25개 이미지 조각과 첫 도움말을 교체했다. `開ける` 오역은 ‘열기’로 정정했고 해당 자산은 최신 빌드에도 유지된다. 암흑 마법 HP50→27, 화염 마법 HP27→-42 및 구속 연출의 이전 검증도 보존했다.

**한글화는 일본어 모드(`language=0`)를 유지한 슬롯 리매핑을 우선 실험한다.**
폰트 패킹과 RTB 제어 흐름을 먼저 검증하고, 소규모 실행 화면 검증을 통과한 뒤 본번역을 확대한다.
`language=6`을 켜고 4bpp 폰트를 넣으면 동작한다는 기존 경로 A는 근거가 잘못되어 보류한다.
일본어 모드에서 한글 전용 슬롯, RTB 길이 변경, 튜토리얼 24개 본문·질문과 화자 23개 표시까지 실행 검증했다. DB 3종의 구조 파싱·왕복과 아이템 5개·스킬 5개의 한글 표본 실행을 완료했다. 추가 상태 효과·공통 UI·대규모 용량·전체 회귀 검증은 남아 있다.

원본 고정과 추출 검수에 이어 ISO/추출 폴더 50개 파일 대조, 11개 아카이브의 무변경 전체 바이트 일치,
2,016개 글리프 왕복 검사, 동일 크기 아카이브/ISO 재삽입 도구와 최소 한글 글리프 실험 ISO까지 만들었다.
앞선 한 문장 실험은 기존 일본어를 보존하면서 미사용 코드 슬롯에 한글 32자를 추가하고,
첫 라키 대사 `戦い方の基本を教えるぞ`를 동일 22바이트의 `전투의 기본을 알려주마`로 바꾼 것이다.
PCSX2 2.6.3 새 부팅에서 한글 문장, 이후 일본어 선택지와 `テージ`·장음부호 보존을 확인했다.
폰트는 뒤의 0 패딩 4,608바이트만 소비해 2,048글리프로 확대했고, ID 2038~2047을 실제 출력했다.
후속 작업에서 RTB 280개 전체의 필드 파서·손실 없는 직렬화·문자열 길이 변경 도구를 구현했다.
길이 증가(22→23바이트)·감소(22→20바이트) 실험본의 한글 출력과 각각 다른 선택지 분기 진입을 확인했고, 축소본은 전투 화면까지 진행했다.
명령 의미 전체 해석, DB 표본 밖의 번역·추가 효과 검증, 대규모 폰트 확장 및 전체 회귀는 남아 있다.
튜토리얼 시험본은 본문·질문 24개와 화자 23개를 번역하고 한글 152자를 추가했다.
SYSTEM.DAT을 ISO 안에서 32,768바이트 앞당겨 확장 공간을 확보했고, 실제 부팅과 ID 2167 출력이 확인됐다.
24개 본문·질문과 해당 화자 23개를 모두 실제 화면에서 확인했다. 같은 시험본의 양쪽 선택지, 이동·대기·적 턴,
두 지점의 일시정지 상태 저장과 총 3회 복원도 통과했다.
후속 검증에서 Metal 스킬 연출 중 PCSX2 assertion이 발생했다. 같은 ISO를 Software 렌더러로 실행해
튜토리얼 전투 완료, 본편 첫 출격 준비의 No.01 진행 저장, 상태 파일 없는 새 부팅의 게임 내 로드까지 통과했다.
프롤로그 완료 저장은 시스템 데이터이며 본편 진행 슬롯과 구분했다. 현재 시험용 설정은 Software이며,
원본 ISO의 동일 연출 비교 없이 Metal 충돌이 패치와 무관하다고 단정하지 않는다.
이전 `テージ → 가나다` 실험은 pair 규격 확인용 전역 치환으로 별도 보관한다.
후속 DB 검수에서 3개 파일의 13개 표·1,689개 레코드를 전체 바이트 왕복했고, 빈 문자열 포함 1,941개 문자열 필드를 분리했다. 9개 오프라인 길이 변경 실험에서 수치·ID 불변을 확인했다.
최신 DB 시험본은 아이템 5개·스킬 5개, 16개 문자열을 번역하고 한글 28자를 더해 총 2,196개 글리프를 사용한다.
기존 튜토리얼 번역과 이전 2,168개 글리프는 유지했다. 16개 문자열을 실제 화면에서 확인하고,
바람 마법(적 HP80→50, 3→2회), 약초(HP80→100, 3→2개), 회복 마법(HP90→103),
No.02 저장 후 최종 빌드 새 부팅 로드, 같은 ISO의 상태 파일 복원까지 통과했다.
DB 단계 최종 ISO: `build/status_slice_v2/Poison Pink (Japan) - status slice.iso`, SHA-256 `3b4d9bf5a74233a3c2d60b65b5788513702cc52f3b099d4b6f1fab310536bc9f`.
설명창이 개행을 무시해 구분자를 보완했으며 이전 DB 시험본은 비교 자료로 보존했다.
이 DB 표본의 후속 화염/암흑 시전은 위 추가 검증에서 통과했다. 공포·수면/물리 이상 해제와 장비 교환은 추가 검증 대상이다.
이번 작업에서는 원본 게임 파일과 ISO를 수정하지 않았다.

- 최신 DB 한글 표본과 실행 결과: [docs/STATUS_SLICE.md](docs/STATUS_SLICE.md), [reports/status_slice_runtime.json](reports/status_slice_runtime.json)
- DB 구조·로더 근거·주입 순서: [docs/STATUS_DB_FORMAT.md](docs/STATUS_DB_FORMAT.md), [reports/status_db_audit.json](reports/status_db_audit.json)
- 실행 방법과 상세 작업 순서: [LOCALIZATION_PIPELINE.md](LOCALIZATION_PIPELINE.md)
- 오류별 근거와 정정: [docs/HANDOVER_AUDIT.md](docs/HANDOVER_AUDIT.md)
- 기계 판독 검수 결과: [reports/audit.json](reports/audit.json)
- 폰트 규격: [docs/FONT_SPEC.md](docs/FONT_SPEC.md)
- 실제 한글 출력과 재현 절차: [docs/RUNTIME_PROBE.md](docs/RUNTIME_PROBE.md)
- ISO/추출 파일 대조: [reports/iso_inventory.json](reports/iso_inventory.json)
- 무변경 아카이브 검증: [reports/noop_archives.json](reports/noop_archives.json)
- 최초 폰트 진단 검증: [reports/font_probe.json](reports/font_probe.json)
- 한글 한 문장·32글리프 확장: [docs/KOREAN_SENTENCE_PROBE.md](docs/KOREAN_SENTENCE_PROBE.md), [reports/korean_sentence_probe.json](reports/korean_sentence_probe.json)
- 최신 24문장 시험본: [docs/TUTORIAL_SLICE.md](docs/TUTORIAL_SLICE.md), [reports/tutorial_slice.json](reports/tutorial_slice.json)
- 후속 전투 완료·게임 내 저장과 새 부팅 로드: [docs/TUTORIAL_BATTLE_RUNTIME.md](docs/TUTORIAL_BATTLE_RUNTIME.md), [reports/tutorial_battle.json](reports/tutorial_battle.json)
- 길이 변경 실행 결과: [docs/RTB_RESIZE_RUNTIME.md](docs/RTB_RESIZE_RUNTIME.md)
- RTB 구조와 길이 변경 도구: [docs/RTB_FORMAT.md](docs/RTB_FORMAT.md), [reports/rtb_structure_audit.json](reports/rtb_structure_audit.json)
- 과거 문서 원문: [docs/history/HANDOVER.v1.md](docs/history/HANDOVER.v1.md), [docs/history/RESEARCH.2026-09-15.md](docs/history/RESEARCH.2026-09-15.md)

## 2. 원본 식별과 재현

- `SYSTEM.CNF`: `BOOT2 = cdrom0:\SLPS_258.54;1`, `VER = 1.03`, `VMODE = NTSC`.
- `VER=1.03`은 부팅 설정 값으로 확인했다. 별도 배포판/리비전 판별은 ISO 해시로 한다.
- 실행 파일은 ELF32 little endian. LOAD 세그먼트는 파일 오프셋 `0x1000`, 가상주소 `0x100000`에서 시작한다.
- 해당 세그먼트의 주소 변환은 `VA = file_offset - 0x1000 + 0x100000`이다.
- 원본 ISO, ELF, HED/DAT, 기타 추출 파일의 크기/SHA-256은 [localization/source.lock.json](localization/source.lock.json)에 고정했다.
- `python3 tools/localization_pipeline.py audit`는 원본이 달라지면 실패하며 기준 해시를 자동 교체하지 않는다.
- ISO 내부 50개 파일과 추출 폴더를 SHA-256으로 대조해 모두 일치함을 확인했고, ISO의 LBA/파일 목록을 기록했다.

## 3. 검수 후 신뢰할 수 있는 범위

### 아카이브

HED는 44바이트 레코드이며 파일 엔트리의 offset/size로 DAT에서 직접 읽을 수 있다.
하지만 **디렉터리 offset은 DAT 오프셋이 아니라 HED 레코드 인덱스**다. `offset=2`만으로 디렉터리를 판별하면 안 된다.
현재 자료의 디렉터리 엔트리는 timestamp=0이고, offset이 가리키는 범위는 `..`로 시작하여 `--DirEnd--`로 끝난다.
size에는 이 두 엔트리도 포함된다. 이 규칙을 모든 11개 HED에 적용해 전체 레코드를 순회했다.

| 아카이브 | 실제 파일 엔트리 수 | 디렉터리 수 |
| --- | ---: | ---: |
| DMAP | 3,843 | 90 |
| STATUS | 210 | 2 |
| SYSTEM | 15 | 2 |
| ROOT | 1 | 1 |
| BATTLE | 5,386 | 328 |
| CLIP | 199 | 15 |
| LFACE | 127 | 1 |
| SFACE | 131 | 1 |
| SOUND | 287 | 11 |
| MOVIE | 30 | 16 |
| MODULES | 12 | 2 |

모든 실제 파일 시작 위치는 현재 원본에서 `0x4000` 정렬이다. 모든 파일 범위는 DAT 내부에 있고 서로 겹치지 않는다.
HED 디코드→재직렬화와 11개 HED/DAT 무변경 staging의 전체 바이트 일치를 통과했다.
크기 확장을 수반하는 재배치와 전체 기능 회귀 검증은 별도다.
`SUBDIR.HED`는 이 레코드 포맷이 아니므로 별도로 보존한다.
컨테이너가 직접 접근 가능하다는 사실이 내부의 모든 리소스 형식까지 비압축임을 보장하지는 않는다.

### 동영상 컷씬 및 오디오 (MOVIE / SOUND)

- **동영상 규격 (`*.ipu`)**:
  - 총 15개 컷씬 (`s01.ipu` ~ `s15.ipu`, 총 1.01 GB).
  - 포맷: Sony IPU (MPEG-2 Video 기반), 640x448 @ 29.97 fps (NTSC).
- **오디오 스트리밍 규격 (`*.ag`)**:
  - 총 15개 오디오 스트림 (`s01.ag` ~ `s15.ag`, 총 70.3 MB).
  - 코덱: Sony SPU2 VAG ADPCM (16바이트 블록당 28샘플, low-nibble first).
  - 채널 구성: **2채널 스테레오 (Stereo)**, 샘플레이트 **44,100 Hz**.
  - **인터리브 블록 크기**: **16,384 바이트 (`0x4000`, 16KB = 8개 DVD 섹터)**.
    - `[16KB L 채널] [16KB R 채널] [16KB L 채널] [16KB R 채널] ...`
    - 보폭(Stride): 32,768 바이트 (`0x8000`). 모든 `.ag` 파일 크기는 `0x8000`의 정수배로 나누어떨어짐.
  - 주의: 16바이트 단위 교차 인터리브로 디코딩할 경우 1575Hz 고주파 버징 및 채널 파쇄 잡음이 발생하므로 반드시 16KB 블록 단위로 디인터리브해야 함.
- **도구 및 변환 결과**:
  - 추출 및 변환 스크립트: `tools/remux_all_movies_with_sound.py`
  - 산출물 경로: `extracted_movies/s01.mp4` ~ `s15.mp4` (H.264 + AAC Stereo 44.1kHz).

### RTB와 번역 후보

- 실제 RTB 파일 수: **280개**.
- 기존 `all_dmap_dialogues.json`: **17,992행의 휴리스틱 묶음**. 검증된 대사 수가 아니다.
- 신규 목록: **37,301개 패턴 후보**, 이 중 일본어 범위 문자가 포함된 후보 31,520개, 기타 5,774개, 엄격한 CP932 디코딩 실패 7개.
- 새로운 후보 수에도 이름, 리소스 문자열, 반복문자열, 오탐이 포함될 수 있다. 전체 대사 수나 번역률의 분모로 사용하지 않는다.
- 기존 후보는 심볼 테이블 뒤에서 `33 01` 패턴을 검색한 목록이다. 후속 `rtb_codec.py`는 로더 기반으로 280개 파일 전체를 구조 파싱한다.
- 구조 파싱 결과 함수 23,487개, 명령 1,440,116개, 문자열 리터럴 126,329개, 분기 122,923개. 리터럴 수를 번역문 수로 간주하지 않는다.
- `opcode_offset`과 실제 텍스트 시작 `payload_offset=opcode_offset+6`을 구분한다.
- 파일 전체 경로, HED 인덱스, 원본 파일 해시, 원문 바이트/해시로 위치를 고정한다.
- `33` 문자열 로더의 길이는 uint8로 확인했다. 최대 **255바이트**이며, 메타데이터용 가변 count 형식과 다르다.
- 점프는 현재 명령 인덱스 기준 signed 상대 이동이다. 모든 파일의 명령 수·분기 경계와 필드 왕복을 확인했다.
- 공통 헤더의 packed 4바이트 전체 의미, 각 명령의 연산 의미, 화자/대사/선택지 역할은 추가 검증 대상이다.

### DB

`status_db_codec.py`가 세 파일의 **13개 표 / 1,689개 레코드 / 85,016바이트**를 순차 파싱하고 무변경 왕복한다.

- PPITEM: 표별 150/46/59/21/119행, 합계 395행. 앞 네 표의 이름·설명과 후행 수치 표를 포함한다.
- PPSKILL: 194행. 이름 종결 NUL 직후부터 66바이트 수치 영역을 읽고 설명을 읽는다.
- PPPARAM: 표별 271/251/265/25/42/102/144행, 합계 1,100행. 첫 표의 ID는 1~444 사이의 불연속 값이다.
- 텍스트 필드 1,941개(비어 있지 않은 필드 1,388개)의 엄격한 CP932 디코딩이 성공했다. 번역 대상 개수로 간주하지 않는다.
- 별도 설명 표는 PPPARAM 표 5, ID 26~127의 102행이다. 과거의 “128~271번이 도감 설명” 구획은 폐기한다. 도감 화면과의 연결은 별도 확인한다.
- 기존 `parse_items.py`는 첫 레코드 뒤에서 중단하고, 스킬/캐릭터 추출기는 0 건너뛰기·ID 검색을 사용하므로 기존 JSON은 참고 자료로만 보존한다.
- 이름 상한은 아이템 18B, 스킬 16B, PPPARAM 표 0/4는 18B, 표 1은 20B다. 설명은 아이템/스킬 127B, PPPARAM 표 5는 255B다. NUL 제외, 메모리 경계 기준이며 화면 폭 기준은 아니다.
- 로더가 버리는 상위 바이트와 읽지 않는 수치 영역도 원본 그대로 보존한다. 문자열 편집은 파일 해시·표·행·필드·원문 바이트로 고정하고 수치·ID 불변을 검사한다.
- 빈 문자열·동일 길이·버퍼 상한 길이의 9개 오프라인 실험이 통과했다. **후속 아이템 5개·스킬 5개 시험에서 16개 문자열 표시와 공격·회복·아이템 사용·저장/로드 표본 검증을 통과했다.** 전체 상태 효과와 장비 교환은 미검증이다.

근거와 재현 명령은 [STATUS_DB_FORMAT](docs/STATUS_DB_FORMAT.md)에 있다. 표본 번역·주입 결과는 [STATUS_SLICE](docs/STATUS_SLICE.md)에 있다. 후속 메뉴·도움말 표본과 다음 세부 순서는 [UI_PIPELINE](docs/UI_PIPELINE.md)을 따른다.

### 폰트와 언어 모드

- `kanji.dat=290,304B`, `kantable.dat=15,120B=7,560×int16`.
- 테이블에 등록된 슬롯 2,016개, ID 범위 0~2,015. `kantable.h`의 **중괄호 안 initializer**와 바이너리 테이블이 일치한다.
- 기존 정규식은 `Sint16`의 `16`까지 읽었다. 이로 인한 `+1` 인덱스 공식은 폐기한다.
- 실제 `0x001d61ec`에서는 189 상수를 사용한다. 기존 188열 압축 공식은 엔진과 일치하지 않는다.
- 실제 `0x001d5b08` 언어 설정 분기에서는 `language=0`과 `6` 모두 `gp-20276`에 **0**을 기록한다. 나머지 값은 1이다.
- 실제 `0x001d61e0`부터의 루틴은 일본어 코드 계산 후 테이블을 읽고, `ID & 1`을 별도 출력하며 `(ID >> 1) * 288`로 폰트 주소를 계산한다.
- 후속 복사 루틴의 `0x3333/0xCCCC` 마스크와 원본 글리프 복원으로 pair 패킹을 확인했다. 행당 12바이트, 낮은 니블부터 x 순서, 짝수 글리프 하위 2비트/홀수 글리프 상위 2비트다. [FONT_SPEC](docs/FONT_SPEC.md) 참고.
- 따라서 단순한 `glyph_id*144` 연속 레이아웃과 `glyph_id*288` 한국어 레이아웃 둘 다 확정 규격으로 사용하지 않는다.
- 튜토리얼 시험본은 152자를 추가해 총 2,168글리프이며, 사용 한글 151자와 마지막 ID 2167을 실제 표시했다. 후속 DB/UI 시험본은 28자를 더한 총 2,196글리프다. 더 큰 확장의 힙·캐시·업로드 상한과 장시간 안정성은 미검증이다.

## 4. 작업자에게 넘길 핵심 규칙

1. 원본을 변경하지 말고 출력은 별도 staging/build 경로에 만든다.
2. 기존 JSON의 화자 추정과 역할 분류를 확정 정보로 사용하지 않는다.
3. 원문은 보존하고 번역은 별도 `target` 필드에 쓴다.
4. VM/DB 파서가 원문을 손실 없이 왕복하고 명령·레코드 경계를 입증하기 전에는 길이를 바꾸지 않는다.
5. 한글은 NFC, 게임 인코딩은 명시적 매핑표를 사용한다. CP949/UTF-8로 일괄 저장하지 않는다.
6. 글리프 누락, 제어 토큰 손상, 255바이트 초과, 잘못된 원본 해시는 빌드 오류로 처리한다.
7. 정적 검수 통과, 원문 재삽입 부팅 통과, 실제 한글 화면 통과를 구분해 기록한다.
8. 전체 실행 계획과 각 통과 기준은 [LOCALIZATION_PIPELINE.md](LOCALIZATION_PIPELINE.md)를 따른다.
