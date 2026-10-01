# 일본어 보존 + 한글 한 문장 실행 검증

2026-09-15. PCSX2 2.6.3에서 실험 ISO를 새로 부팅해 **`전투의 기본을 알려주마`**가 실제 대화창에 출력되는 것을 확인했다.

![실제 한글 대사](../build/korean_sentence/evidence/korean-first-line.png)

## 확인 범위

| 항목 | 결과 |
| --- | --- |
| 번역 대상 | `DMAP:2786:0000bb34`, `dmap/script/t00_0010.rtb` 첫 라키 안내 |
| 원문 → 번역 | `戦い方の基本を教えるぞ` → `전투의 기본을 알려주마` |
| 문자열 길이 | 원문·번역 모두 게임 인코딩 22바이트; 길이 필드와 이후 바이트 불변 |
| 폰트 확장 | 2,016 → 2,048개, 290,304 → 294,912바이트 |
| 실제 출력한 추가 글리프 | 문장에 쓰인 10자, ID 2038~2047; 나머지 22자는 정적 래스터 검증만 수행 |
| 일본어 보존 | 원본 폰트 290,304바이트와 기존 매핑 불변; 실제 `ラキ`, `テージ`, `アウローラ` 확인 |
| 선택지 진행 | 일본어 질문·선택지 표시, `いいえ` 선택 후 두 대사 진행 확인 |
| ISO 검증 | 전체 비교 2,033바이트 변경, ISO 크기·모든 파일 LBA 보존 |
| 미검증 | `はい` 분기, 길이 증가·감소, 전체 VM, DB, 저장/로드, 전투 후 캐시, 2,048개 초과 확장 |

![일본어 선택지](../build/korean_sentence/evidence/japanese-choice.png)
![일본어 이름과 장음부호 보존](../build/korean_sentence/evidence/japanese-name-long-vowel.png)

기존 세 글자를 전역 치환한 `font_probe`와 별개인 후속 실험이다. 새 ISO는 원본에서 직접 만들었다.
32자 폰트 파일을 읽고 끝부분의 문자를 출력한 결과이며, 모든 32자의 화면 품질이나 대규모 폰트 용량 상한을 입증한 것은 아니다.

## 구현과 보호 검사

1. 원본 테이블 값이 `-1`이고 CP932 입력으로 유효한 서로 다른 코드 슬롯을 고른다. 280개 RTB 원시 바이트, ELF, STATUS의 DB 3개, ROOT/config에서 나타난 바이트 쌍은 제외한다. 이미지·음성 및 미확정 텍스트 경로까지 모두 조사한 결과는 아니다.
2. 원본 글리프를 그대로 두고 32개를 뒤에 추가한다. `kanji.dat` 뒤의 **0으로 채워진 4,608바이트 패딩**만 사용한다. 다음 파일의 위치 884,736을 넘기면 실패한다.
3. SYSTEM.HED에서 해당 파일 크기 필드만 갱신한다. DAT 크기, 기존 파일 오프셋, ISO LBA는 그대로다. 일반적인 리소스 재배치 기능은 아직 없다.
4. RTB 전체 해시, 리터럴 헤더/태그, 원문 해시, 위치, 인접 명령 바이트를 검사하고 22바이트만 교체한다. 전체 명령 파서 없이 범용 문자열 삽입으로 확장하지 않는다.
5. 매핑 문자와 ASCII만 명시적으로 인코딩한다. NFC, 누락 문자, 인코딩 왕복과 동일 바이트 길이를 검사한다.
6. 원본·출력 ISO 전체를 읽어 변경 위치와 값을 staged 파일의 차이와 독립적으로 대조한다.

변경 바이트: SYSTEM.HED 1 + SYSTEM.DAT 2,010 + DMAP.DAT 22 = **2,033**.
새 ISO SHA-256: `5ed8beed8d5781c17868f20aea2687a6ab078fb3d2bfd79386b9d3d0056b058c`.

## 글꼴과 재현 환경

- Noto Sans KR Regular 2.004, 로컬 PCSX2 리소스에 있던 글꼴 사용. 정확한 경로·SHA-256은 보고서에 기록했다.
- SIL Open Font License 1.1, Copyright 2014–2021 Adobe. [라이선스 사본](../build/korean_sentence/OFL.txt), [공식 출처](https://raw.githubusercontent.com/google/fonts/main/ofl/notosanskr/OFL.txt).
- Pillow 10.4.0 / FreeType 2.13.2. 22px 글꼴을 3배로 래스터화해 24×24 셀로 축소, 4계조 양자화 후 pair 형식으로 저장.
- PCSX2 2.6.3 / Metal / 사용자 제공 Japan v02.00 BIOS. 프로젝트의 독립 `build/runtime` 환경을 사용했다.
- [32자 정적 아틀라스](../build/korean_sentence/glyph_atlas.png). 겹받침의 게임 화면 검증은 별도다.

## 실행 명령

프로젝트 루트에서 실행한다. 빌드 결과는 이미 존재하며, 생성 명령은 기존 결과를 덮어쓰지 않는다.
빌드에는 위 글꼴과 `build/korean_sentence/OFL.txt`, Pillow가 필요하다.

```sh
# 최초 빌드용; 기존 산출물이 있으면 실패
python3 tools/korean_sentence_probe.py --iso

# 기존 실험 ISO 전체 검증
python3 tools/korean_sentence_probe.py --verify

# 회귀 검사: 각각 7개, 10개, 6개
python3 tools/test_korean_sentence_probe.py
python3 tools/test_iso_font_stage.py
python3 tools/test_localization_pipeline.py
```

이미 실행 중인 시험용 PCSX2를 종료한 뒤 새로 부팅한다.

```sh
'build/runtime/PCSX2-v2.6.3.app/Contents/MacOS/PCSX2' \
  -portable -nogui -fastboot -nofullscreen \
  -logfile "$PWD/build/runtime/manual-korean-sentence.log" \
  -- "$PWD/build/korean_sentence/Poison Pink (Japan) - Korean sentence.iso"
```

1. 타이틀에서 F10(Start), `prologue`에서 F11(Circle).
2. 영상 시작 후 F10으로 건너뛰고 첫 라키 대사까지 기다린다.
3. `전투의 기본을 알려주마` 확인 후 F8로 캡처한다.
4. F11 → 오른쪽 → F11로 `いいえ` 선택, 일본어 라키 대사를 확인한다.
5. F11로 다음 대사에 진입해 `テージ`와 `リベル・アウローラ`가 원래대로인지 확인한다.

현재 시험용 앱은 마지막 일본어 대화창에서 일시정지했다. Space로 재개할 수 있다.
이전 실험의 상태 복원 문제는 이번 작업에서 해결했다고 표시하지 않았다. 재현 근거는 새 부팅이다.

## 당시 다음 구현 순서

후속 작업: [RTB 전체 구조 파서와 길이 변경](RTB_FORMAT.md). 아래 1번의 필드 경계와 왕복 구현은 완료했다.

1. `t00_0010.rtb`의 전체 명령 경계·분기 참조와 무변경 직렬화부터 확정한다.
2. 동일 길이 실험을 기준으로 길이 증가/감소 각 한 문장을 만들고 양쪽 선택지·반환을 비교한다.
3. 32자에 포함된 겹받침과 혼합문을 화면 검증한다. 100~300자 확대는 DAT 재배치 및 ID/캐시 상한 확인 후 진행한다.
4. 해당 구간 20~30문장으로 확대해 전투·저장·재로드까지 검증한다.

기계 판독 증거: [korean_sentence_probe.json](../reports/korean_sentence_probe.json).
검수된 번역 기록: [korean_sentence_review.json](../localization/korean_sentence_review.json).
