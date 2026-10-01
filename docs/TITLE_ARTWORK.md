# 사용자 제작 타이틀 이미지 적용

2026-09-16. 사용자가 제공한 로고·타이틀 메뉴 PNG 두 장을 기존 도움말 v7 통합본에 적용했다.

- 최신 ISO: `../build/title_artwork_v1/Poison Pink (Japan) - custom title.iso`
- SHA-256: `4ca319947d7dfb3ef9e570094f22e2e81445a8699157c5299ac61b1f64bf231d`
- 입력 고정 사본: `../localization/artwork/title_user_v1/tit_lg00.png`, `../localization/artwork/title_user_v1/tit_tx01.png`
- 입력 경로·해시: `../localization/title_artwork.json`
- 결과: `../reports/title_artwork.json`
- 변환된 TIM2와 PNG: `../build/title_artwork_v1/`

## 변환과 검증

원본 크기 512×256을 유지하고 크기 변경이나 재디자인 없이 원본 256색 팔레트에 매핑했다. 알파를 곱한 RGB와 알파를 함께 비교해 가장 가까운 색을 사용한다. 표시 색이 그대로인 픽셀은 기존 인덱스도 유지한다. TIM2 헤더·팔레트·크기와 ISO 파일 위치를 보존했다.

전체 ISO 비교 결과 두 텍스처의 인덱스 49,723바이트만 변경됐다. 기존 튜토리얼·도움말·UI·폰트·대사와 기타 파일은 바이트가 일치한다. TIM2 재파싱·재직렬화 일치, ISO 메타데이터 일치, 기존 텍스처 코덱·ISO 복원 도구 테스트 6개를 통과했다.

원본 팔레트 근사에 따른 RGBA 오차는 보고서에 기록했다. 알파를 곱한 RGBA의 채널별 RMSE는 로고 2.14, 메뉴 1.01(0~255 척도)이며 최대 알파 오차는 각각 44, 13이다. 이는 자동 수치 비교이며 화면 품질 검수 완료를 뜻하지 않는다. 이미지 열람 및 게임 실행은 사용자의 이전 요청대로 하지 않았다.

## 재현

`python3 tools/title_artwork.py --config localization/title_artwork.json`

완료 ISO 덮어쓰기를 거부하므로 재빌드할 때는 설정 사본의 `output_iso`를 새로운 `build/` 경로로 지정한다. 기준 ISO인 도움말 v7은 유지했다. 사용자 원본 편집 PNG와 원본 게임 폴더는 수정하지 않았다.
