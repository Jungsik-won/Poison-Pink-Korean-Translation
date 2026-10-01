# 사용자 PSD 타이틀 적용

> 정정: 아래 흰색 검사는 저장 알파 140과 255의 차이를 없애는 미리보기만 비교했다. 3,151개의 흰색 픽셀이 낮은 저장 알파를 선택한 오류를 후속 빌드에서 수정했다. 최신 ISO와 올바른 검증은 [타이틀 알파 수정](TITLE_ALPHA_FIX.md)을 따른다. 이 문서는 당시 빌드의 이력이다.

## 결과

- 입력: `extracted/original/images/DMAP/dmap/title/tit_tx01.tm2.psd`.
- 입력 SHA-256: `7c00cf80716f14cd2f3aff93c27f3192a2f39da6a9374c359f16ea7a2eccd95d`.
- 보관 사본: `localization/artwork/title_user_psd_v1/tit_tx01.tm2.psd`.
- 실제 적용 PNG: `localization/artwork/title_user_psd_v1/tit_tx01.png`.
- 출력 ISO: `build/title_psd_v1/Poison Pink (Japan) - Korean system and title v2.iso`.
- 출력 SHA-256: `28045de9491f9cbf9f7819b539c6381d0e7525086c67335f74b128e1e562fb94`.

512×256, 8비트 RGB, sRGB PSD의 저장된 최종 합성 이미지를 사용했다. 레이어 재렌더링이나 크기 변경·글자 재디자인은 하지 않았다. 사용자가 정한 ‘설정’ 간격도 유지했다.

## PSD 투명도 해석

PSD는 4채널, 레이어 수 -42로 합성 결과에 투명도가 있음을 표시한다. 저장된 미리보기 RGB는 흰 배경에 합성된 값이어서 이를 그대로 RGBA로 쓰면 반투명 테두리에 흰 번짐이 생긴다. [psd-tools의 공식 변환 코드](https://github.com/psd-tools/psd-tools/blob/main/src/psd_tools/api/pil_io.py)와 같은 역합성 원리로 원래 RGB를 복원했다. 투명도 채널과 불투명 픽셀은 변경하지 않았고, 다시 흰 배경에 합성했을 때 저장된 RGB와 채널별 오차가 최대 1임을 확인했다. 검사용 `psd_merged_preview.png`는 이 해석 전 원시 미리보기이며 적용 입력이 아니다.

## 흰색과 적용 검증

- 불투명 순백색 입력 3,172픽셀 → 게임용 변환 뒤 같은 위치에 3,172픽셀 모두 유지.
- 시작 안내 첫 줄의 순백색: 이전 사용자 PNG 223픽셀 → 새 PSD 554픽셀.
- 원본 256색 팔레트·TIM2 헤더·이미지 크기 유지.
- 원본 팔레트 근사 변환 오차: premultiplied RGBA RMSE 1.0210, 최대 알파 오차 13. 순백색 보존과 별개로 다른 색·부분 투명도는 근사된다.
- 전체 ISO 비교에서 타이틀 텍스처 인덱스 12,557바이트만 변경됐다. 파일 위치와 크기는 동일하다.
- 시스템 문구 540곳, 기존 대사·DB·글꼴, 사용자 로고·전투 메뉴·도움말은 모두 이전 ISO와 동일하다.
- `dmap/title/tit_tx01.tm2` 기본 채용 경로를 새 PNG로 갱신했다. 이전 PNG와 PSD는 보존했다.

이번 PSD에서는 흰색 중심부가 더 많아졌고 게임용 파일에도 그대로 보존됐다. 실제 화면에서 얼마나 또렷해지는지는 확대·필터·밝기 효과의 영향을 받으므로 게임 실행 전에는 보장하지 않는다. 예전 PNG의 얼룩 현상 원인이 PSD 디코딩이었다고 주장하지 않는다. 이전 입력은 PNG였으며 이번 PSD 해석 문제와 별개다.

## 재현

`tools/title_psd_import.py`. 원본 PSD·기준 ISO 해시를 고정하고 완성 ISO 덮어쓰기를 거부한다. 자세한 수치·해시는 `reports/title_psd_v1.json`과 `build/title_psd_v1/manifest.json`에 있다.
