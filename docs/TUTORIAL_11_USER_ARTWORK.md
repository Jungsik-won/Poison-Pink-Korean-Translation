# 추가 도움말·미니게임 사용자 이미지 11개

2026-09-16. `tutorial_11_KO` 폴더를 전달받아, 사용자 이미지 기본 채용 방침에 따라 적용했다.

## 입력

| 파일 | 내용 | 크기 | 처리 |
| --- | --- | --- | --- |
| ev150, ev151 | 대형 마신 포획 | 640×384 | 사용자 번역 적용 |
| ev154 | GAME OVER | 512×512 | 원본과 동일하여 TIM2 유지 |
| ev155, ev156, ev157 | 저택 및 포획한 마신 활용 | 640×384 | 사용자 번역 적용 |
| ev158, ev159, ev160, ev161 | 스텝 스톤 규칙·조작 | 640×448 | 사용자 번역 적용 |
| ev162 | 내성 | 640×384 | 사용자 번역 적용 |

입력 사본: `localization/artwork/tutorial_11_user_v1/`.
빌드 설정과 원본 입력 경로·해시: `localization/tutorial_11_user_artwork.json`.
결과: `reports/tutorial_11_user_artwork.json`.

## 보존·검증

입력 11개 모두 원본 크기와 전체 알파 마스크가 일치했다. ev154 PNG는 추출 원본과 파일 바이트까지 동일했다. 나머지 10장의 번역 문구와 조작 안내를 검수했으며 별도 수정 없이 입력 그대로 사용했다.

원본 TIM2 헤더·팔레트·파일 크기를 보존하고 색상은 기존 팔레트로 근사 변환한다. 변환 후 알파 마스크와 TIM2 왕복 일치를 검사한다. 미니게임 640×448 이미지도 원본 크기를 유지한다. 빌더가 원본 텍스처 크기를 읽도록 확장했으며, 원본 픽셀과 동일한 이미지는 인덱스를 다시 변환하지 않는다.

기준은 도움말 14장과 사용자 로고·타이틀·전투 메뉴가 적용된 `build/user_help_artwork_v1/Poison Pink (Japan) - user artwork and help.iso`다. 전체 ISO 비교에서 10개 텍스처 범위 밖의 모든 바이트가 같아야 완료한다. 기존 사용자 이미지, 이전 오역 수정 6곳, 대사·폰트·DB 한글화를 유지한다.

새 ISO: `build/tutorial_11_user_v1/Poison Pink (Japan) - expanded user help.iso`.

재현: `python3 tools/user_help_artwork.py --config localization/tutorial_11_user_artwork.json`. 이미 생성된 ISO는 덮어쓰지 않으므로 재빌드할 때는 설정의 출력 경로를 새 `build/` 경로로 지정한다.

이번에도 게임 실행 검증은 보류했다. 사용자 입력 원본 및 원본 게임 폴더는 변경하지 않았다.

## Completed ISO

SHA-256: `93b016e26da49cee1173dcc0f727f9cd5c78879f0adefde6ed449909f37dbceb`. Full ISO comparison passed: 402961 changed bytes across 10 textures only. All 11 alpha masks exact; GAME OVER TIM2 unchanged. Four codec tests and Python compilation passed.
