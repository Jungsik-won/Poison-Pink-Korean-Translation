# 사용자 제작 전투 메뉴와 타이틀 통합

2026-09-16. 사용자가 제공한 `sys000.tm2 복사.png`의 문구와 배치를 확인하고, 기존에 제공한 로고·타이틀 메뉴까지 함께 적용했다.

## 적용 범위

- 전투 메뉴: `status/sys000.tm2`
- 사용자 로고: `dmap/title/tit_lg00.tm2`
- 사용자 타이틀 메뉴(로드·프롤로그 포함): `dmap/title/tit_tx01.tm2`
- 기준 ISO: `build/help_pages_v7/Poison Pink (Japan) - tutorial help.iso`
- 출력 ISO: `build/battle_menu_artwork_v1/Poison Pink (Japan) - custom title and battle menu.iso`
- 입력 고정 사본: `localization/artwork/battle_menu_user_v1/sys000.png`, `localization/artwork/title_user_v1/`
- 입력 경로·해시: `localization/battle_menu_artwork.json`, `localization/title_artwork.json`
- 결과 보고서: `reports/battle_menu_artwork.json`

이전 타이틀 적용 ISO는 작업 시작 시 해당 경로에 없어, 남아 있는 도움말 v7에서 세 장을 함께 적용했다. 로고와 타이틀 메뉴 TIM2의 해시가 이전 타이틀 빌드의 검증 기록과 정확히 일치해야 빌드가 통과한다.

## 전투 메뉴 검수

사용자가 첨부한 이미지에서 이동·공격·스킬·명령·열기·포획·도구·귀환·상태·대기·재행동·설정·행동순·쌍격·마신·조건의 문구와 배열을 확인했다. `魔神`과 `条件`은 UAD에서 각각 별도의 64×24 조각이므로 ‘마신’과 ‘조건’을 각 칸에 넣는 현재 배치가 맞다. 앞선 답변에서 하나의 ‘마신 조건’으로 묶어 안내한 부분을 정정했다.

512×256 RGBA 규격과 원본 알파 마스크가 유지됐다. 원본 PNG와 비교했을 때 메뉴 밖에서 달라진 32,768픽셀은 모두 완전히 투명한 픽셀의 RGB 값뿐이다. 이 값은 표시 결과에 영향을 주지 않으며 컴파일 시 원래 인덱스를 유지한다. 메뉴 밖의 보이는 그림은 바뀌지 않았다.

## 변환·검증

원본 256색 팔레트와 TIM2 헤더를 유지하고, 크기 변경 없이 알파를 곱한 RGB와 알파를 함께 비교해 가장 가까운 색으로 변환한다. 변환된 전투 메뉴도 기존 알파 마스크가 유지되고 UAD가 지정한 64×24 메뉴 영역 밖의 인덱스가 일치해야 통과한다. 색 변환은 근사이며 원본 편집 PNG와 완전히 동일한 색을 보장하지 않는다.

전체 ISO 비교에서 세 텍스처 이외의 모든 바이트가 같고 ISO 메타데이터가 유지되는지 검증한다. 기존 도움말·대사·폰트·DB·다른 UI는 유지한다. 작성 PNG의 검수와 정적 검증을 수행하며, 게임 실행 검증은 이전 사용자 요청에 따라 보류한다.

## 재현

`python3 tools/battle_menu_artwork.py`

완료 ISO 덮어쓰기를 거부한다. 다시 만들 때는 설정의 `output_iso`를 새로운 `build/` 경로로 변경한다. 원본 게임 폴더와 사용자가 편집한 입력 PNG는 수정하지 않는다.

## Verification result

ISO SHA-256: `d116694d374ef4d1c657ccd0010f32e94dc9349d194f7e8b175781d06d8e4d97`. Entire ISO diff passed: 89,259 changed bytes across the three textures; battle menu 39,536 bytes. Battle-menu maximum alpha error: 0; premultiplied RGBA RMSE: 0.828. Four texture-codec tests and Python compilation passed.
