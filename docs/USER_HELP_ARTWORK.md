# 사용자 제작 도움말 14장 채용

## 입력과 적용 범위

사용자가 제공한 `ev136-ev142_KO.zip`의 PNG 7장과 별도로 제공한 `ev143.png~ev149.png`를 기본 도움말 이미지로 채용한다. 입력은 `localization/artwork/help_user_v1/`에 해시와 함께 고정했다. 이전에 첨부된 큰 화면 캡처는 보관용이며 빌드 입력이 아니다.

기준은 `build/battle_menu_artwork_v1/Poison Pink (Japan) - custom title and battle menu.iso`다. 사용자 로고 `tit_lg00`, 타이틀 메뉴 `tit_tx01`, 전투 메뉴 `sys000` 및 기존 대사·폰트·DB 한글화를 포함한다.

출력: `build/user_help_artwork_v1/Poison Pink (Japan) - user artwork and help.iso`.

## 승인된 오역 수정

사용자가 ‘닫기→열기’ 및 ‘뿔 공격→발톱 공격’ 수정을 승인했다. 추가로 ev140에서 같은 메뉴 오역을 확인해 동일하게 수정했다.

| 페이지 | 수정 |
| --- | --- |
| ev136 | 메뉴 닫기 → 열기 |
| ev137 | 메뉴 닫기 → 열기, 뿔 공격 → 발톱 공격 |
| ev140 | 메뉴 닫기 → 열기 |
| ev148 | 메뉴 닫기 → 열기 |
| ev149 | 메뉴 닫기 → 열기 |

‘닫기’는 도움말 창을 닫는 하단 버튼이 아닌, 원문 `開ける`인 전투 메뉴 항목만 수정했다. 사용자의 기존 NanumMyeongjoExtraBold 폰트·색·획·배치와 글자를 지운 배경을 사용했다. 수정 전 문구를 같은 설정으로 재생성해 입력 이미지와 바이트가 같은지 확인한 뒤 글자만 교체했다. 여섯 사각형 밖의 모든 픽셀과 전체 알파가 동일하다. 사용자 입력 원본 파일은 수정하지 않았다.

수정 사본: `localization/artwork/help_user_corrected_v1/`.
재현 입력: `localization/help_label_corrections.json`.
수정 검증: `reports/help_label_corrections.json`.

## 빌드와 검증

1. `python3 tools/correct_user_help_labels.py`
2. `python3 tools/user_help_artwork.py`

빌드 입력은 `localization/user_help_artwork.json`의 경로와 SHA-256으로 고정한다. 완료된 ISO 덮어쓰기를 거부하므로 재빌드할 때는 새 출력 경로를 지정한다.

14장 모두 원본 640×384와 알파 마스크가 일치한다. 원본 TIM2 헤더·256색 팔레트·크기를 유지해 컴파일하고, 컴파일 후에도 알파가 같은지 확인한다. 팔레트 색 근사에 따른 오차는 `reports/user_help_artwork.json`에 기록한다.

ISO 전체 바이트 비교로 도움말 14개 텍스처 범위 밖의 모든 바이트가 기준 통합본과 같은지 검사한다. 따라서 기존 사용자 로고·타이틀·전투 메뉴와 기타 한글화가 유지된다. 원본 게임 파일은 변경하지 않는다.

이번 검수는 제공 이미지와 수정 영역 및 정적 데이터 검증이다. 게임 실행 검증은 이전 사용자 요청대로 보류한다. 사용자 도움말의 ‘협공/아이템’과 전투 메뉴의 ‘쌍격/도구’ 용어 차이 및 장식 영문은 입력대로 유지했다.

## Completed ISO

SHA-256: `bc4d5a4e4a764d1a1c69dae80c89bd6a938b918dff4b77251d3519287eb776ec`

Entire ISO comparison: 535223 changed bytes, restricted to the 14 help textures. Original alpha is exact on all 14 pages. Four codec tests and Python compilation passed.
