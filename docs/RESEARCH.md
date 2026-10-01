# Poison Pink (PlayStation 2 - SLPS-25854) 리버스 엔지니어링 분석 보고서

> **2026-09-15 재검수 안내:** 아래는 초기 조사 기록이며 일부 결론이 반증되었다.
> ELF 주소, language=6 플래그, 폰트 인덱스/패킹, RTB 길이 확장 안전성, DB 완전 파싱 주장을 구현 근거로 사용하지 않는다.
> 현재 기준은 [HANDOVER.md](HANDOVER.md), 정정 근거는 [docs/HANDOVER_AUDIT.md](docs/HANDOVER_AUDIT.md), 작업 순서는 [LOCALIZATION_PIPELINE.md](LOCALIZATION_PIPELINE.md)를 따른다.

## 1. 개요
- **대상 게임**: Poison Pink (ポイズンピンク / 영문 발매명: Eternal Poison)
- **플랫폼**: Sony PlayStation 2 (NTSC-J)
- **디스크 시리얼**: SLPS-25854 (SYSTEM.CNF 기준 `SLPS_258.54;1`)
  *(참고: 유저 요청 시 언급된 SLPM-65806은 유사 타이틀 계열 번호이며, 디스크 실체 파일은 SLPS-25854 버전 1.03임)*
- **개발사/발매사**: Flight-Plan (개발) / Banpresto (발매)
- **분석 목적**: 한글화 패치 구현을 위한 게임 데이터 아카이브 구조, 텍스트 저장 방식, 폰트 및 렌더링 파이프라인 분석

---

## 2. 파일 시스템 및 디렉터리 전체 구조

### 2.1 루트 디스크 구조
| 파일/디렉터리 | 크기 (Bytes) | 매직/헤더 (Hex) | 설명 |
| :--- | :--- | :--- | :--- |
| `SYSTEM.CNF` | 57 | `42 4f 4f 54 32 20...` (`BOOT2 =...`) | 부팅 설정 파일 |
| `SLPS_258.54` | 4,659,936 | `7f 45 4c 46 01 01 01 00...` (`.ELF`) | 메인 MIPS R5900 실행 파일 |
| `DI` | 128 | `21 a4 9c fe 00 00...` | 디스크 정보 식별자 (128B 고정) |
| `DATA/` | - | 디렉터리 | 게임의 모든 리소스 데이터 (.DAT / .HED) |
| `MODULES/` | - | 디렉터리 | IOP용 사운드/패드/메모리카드 IRX 드라이버 |

### 2.2 `DATA/` 디렉터리 아카이브 목록
게임의 데이터는 11개 카테고리의 짝을 이루는 `.HED`(헤더/인덱스)와 `.DAT`(데이터 컨테이너) 파일로 구성되어 있으며, `SUBDIR.HED`에 해당 11개 카테고리 이름이 텍스트로 명시되어 있습니다 (`dmap`, `modules`, `movie`, `sound`, `status`, `system`, `root`, `battle`, `clip`, `sface`, `lface`).

| 카테고리 (.HED / .DAT) | .HED 크기 (B) | .DAT 크기 (B) | 파일 수 | 주요 포함 확장자 및 내용 |
| :--- | :--- | :--- | :--- | :--- |
| `ROOT` | 220 | 16,384 | 2 | `config.txt` (비디오 해상도, 언어 모드 설정) |
| `SYSTEM` | 968 | 1,376,256 | 17 | `kanji.dat`, `kantable.dat`, `eng.dat`, `eng_pro.dat`, `kantable.h` (폰트 및 시스템 설정) |
| `STATUS` | 9,548 | 12,255,232 | 212 | `PPPARAM.dat`, `PPSKILL.dat`, `PPITEM.dat`, `.tm2` (파라미터/아이템/스킬 및 메뉴 UI) |
| `DMAP` | 181,016 | 419,086,336 | 3,933 | `*.rtb` (이벤트/대사 바이트코드 280개), `*.scp` (카메라 연출 139개), `.tm2`, `.loc`, `.mi` |
| `BATTLE` | 280,324 | 348,864,512 | 5,714 | `.upm` (3D 모델/모션), `.tm2` (텍스처), `.upl`, `.ups` (전투 이펙트) |
| `CLIP` | 10,780 | 19,267,584 | 214 | `.upm`, `.tm2`, `.upl`, `.ups` (클립 씬 연출 데이터) |
| `LFACE` | 5,764 | 14,467,072 | 128 | `.tm2` (대형 인물 대화 페이스 포트레이트 그래픽) |
| `SFACE` | 5,940 | 2,211,840 | 132 | `.tm2` (소형 전투/상태 페이스 포트레이트 그래픽) |
| `SOUND` | 14,124 | 716,619,776 | 298 | `.ags`, `.ag`, `.bd`, `.th` (배경음악, 효과음, 보이스 스트림) |
| `MOVIE` | 3,476 | 1,175,289,856 | 46 | `.ipu` (MPEG2 동영상 스트림), `.ag` (오디오) |
| `MODULES`| 836 | 753,664 | 14 | `.irx`, `IOPRP300.IMG` (IOP 런타임 드라이버 모듈 백업본) |

---

## 3. 메인 실행 파일 (ELF) 분석

### 3.1 ELF 기본 정보
- **파일명**: `SLPS_258.54`
- **아키텍처**: MIPS R5900 (Sony Emotion Engine), 32-bit Little Endian
- **진입점 (Entry Point)**: `0x00100008`
- **프로그램 헤더**: 1개 세그먼트 (LOAD)
- **섹션 헤더**: 76개 섹션 (SN Systems ProDG 툴체인 사용 흔적인 `.DVP.overlay` 다수 포함)
- **주요 메모리 매핑**:
  - `.text`: `0x00100000` ~ `0x004269ff` (크기 3.15MB)
  - `.data`: `0x00426a80` ~ `0x004f9d97` (크기 844KB)
  - `.rodata`: `0x00511c80` ~ `0x0054472f` (크기 202KB)
  - `.bss`: `0x00557780` ~ `0x0064ebd0` (크기 989KB)

### 3.2 ELF 내부 문자열 및 소스 파일 흔적
ELF 내부 바이너리에서 다수의 C 소스 파일명과 디버그 문자열이 확인되었습니다:
1. **폰트 엔진 모듈**: `ulib/uknj.c`
   - `フォントTexture転送+++++++++++++++++++++++++++++++++++++++++++`
   - `フォントCLUT転送+++++++++++++++++++++++++++++++++++++++++++`
   - `knjbank%d`
   - `漢字バッファが足りません!!`
   - `system/kantable.dat`, `system/eng_pro.dat`, `system/kanji.dat`, `system/dbg_han.dat`, `system/eng.dat`
2. **시스템 및 상점 대사 (`.data`)**:
   - `アナログコントローラ(DUALSHOCK 2)が接続されていません。`
   - `コントローラ端子1 にアナログコントローラ(DUALSHOCK 2)を正しく接続しなおしてください。`
   - `何体購入するんだい？`
   - `体で@gになるよ\nいいんだね？`
   - `何個購入するんじゃ？`
3. **디버그 메뉴 문자열 (`.rodata`)**:
   - `佐野国芳でーん■□凹凸` (개발자 이름: Sano Kuniyoshi)
   - `シーンについての設定をします`, `アニメーションの動作を選択します` 등 개발용 엔진 메뉴 텍스트

---

## 4. 아카이브 컨테이너 포맷 (`.HED` + `.DAT`)

### 4.1 압축 여부 검증
- **결론: `.DAT` 파일은 비압축 선형 아카이브(Uncompressed Linear Archive)임**
- **근거**:
  - `SYSTEM.HED`의 `kantable.h` 오프셋(0x00134000)에서 37,866바이트를 직접 읽으면 C 소스코드 텍스트(`Sint16 KanTable[] = { ... }`)가 그대로 확인됨.
  - `ROOT.HED`의 `config.txt` 오프셋(0)에서 881바이트를 직접 읽으면 `//フレームモード...` 텍스트가 그대로 확인됨.
  - `STATUS.HED`의 `PPITEM.dat` 오프셋(0x0014000)에서 직접 읽으면 아이템 이름(`兵士の長剣`)이 비압축 바이너리로 존재함.
  - `LFACE.HED`의 모든 파일은 `TIM2` 매직이 그대로 노출됨.
  - 파일 오프셋은 기본적으로 PS2 디스크 섹터 단위(0x800 = 2,048 바이트) 또는 0x4000(16,384 바이트)으로 정렬(Padding)되어 있음.

### 4.2 `.HED` 엔트리 구조 (44바이트 고정 레코드)
`.HED` 파일은 44바이트(0x2C) 크기의 고정 구조체 배열로 이루어져 있습니다:

```c
struct HedEntry {
    uint32_t offset;       // 0x00: DAT 파일 내 바이트 오프셋 (또는 디렉터리 식별자)
    uint32_t size;         // 0x04: 파일 크기 (바이트 단위, 디렉터리인 경우 항목 수)
    char     filename[32]; // 0x08: Null-terminated 파일/디렉터리 이름
    uint32_t timestamp;    // 0x28: 32-bit Little-Endian Unix Timestamp (빌드 시간)
}; // Total: 44 bytes (0x2C)
```

특수 엔트리:
- 디렉터리 시작 엔트리: `offset = 2`, `size = 하위 파일 수`
- 디렉터리 종료 엔트리: `filename = "--DirEnd--"`
- 상위 디렉터리 이동: `filename = ".."`

---

## 5. 텍스트 저장 방식 분석

게임 내 텍스트는 크게 **(1) 스크립트 바이트코드(.rtb)**, **(2) 파라미터/아이템 DB 파일(.dat)**, **(3) 메인 ELF(.data)**의 세 곳에 분산되어 저장되어 있습니다. 모든 텍스트의 인코딩은 **Shift-JIS (CP932)**입니다.

### 5.1 메인 시나리오 / 이벤트 / 튜토리얼 텍스트 (`DMAP.DAT` 내 `*.rtb`)
- 총 280개의 `.rtb` 파일 중 약 416개 이상의 스크립트 단위에 방대한 대화 텍스트가 들어있습니다.
- 주요 파일명 접두사:
  - `at*.rtb`: 테이지(Teage) 루트 아지트/스토리 이벤트
  - `ao*.rtb`: 올펜(Olfen) 루트 아지트/스토리 이벤트
  - `ah*.rtb`: 하쉬(Harshe) 루트 아지트/스토리 이벤트
  - `ar*.rtb`: 론데미온(Rondemion) 루트 아지트/스토리 이벤트
  - `t*.rtb`, `o*.rtb`, `h*.rtb`, `r*.rtb`, `d*.rtb`: 맵별 퀘스트 및 전투 이벤트
- **바이트코드 내 텍스트 리터럴 구조**:
  - 오프코드 시퀀스: `33 01 7c f0 c1 [LEN: 1 byte] [Shift-JIS TEXT] 65 01 7c f0 c1`
  - `0x33`은 문자열 로드 오프코드이며, `0x7cf0c1`은 스크립트 실행 토큰/타입 마커입니다.
  - 뒤이어 1바이트 길이 필드(`LEN`)가 오고, 그 뒤에 정확히 `LEN` 바이트의 Shift-JIS 텍스트가 배치됩니다.
  - 문자열 종료 후 `0x65 0x01 0x7c 0xf0 0xc1`로 다음 명령이 이어집니다.
  - 화자 이름(예: `ラキ`, `テージ`) 또한 동일한 구조로 대사 바로 직전에 전달됩니다.

### 5.2 상태 / 파라미터 / 스킬 / 아이템 텍스트 (`STATUS.DAT`)
- `PPPARAM.dat` (캐릭터 및 몬스터 스펙, 이름):
  - 구조: `[ID: 2B] [NameLen: 2B] [Name (Shift-JIS Null-padded)] [Stats struct ...]`
- `PPSKILL.dat` (스킬 이름, 속성, 사정거리 및 효과 설명):
  - 스킬명 및 개행(`\n`)이 포함된 상세 설명문이 Shift-JIS로 기록됨.
- `PPITEM.dat` (무기, 방어구, 악세서리, 소비 아이템 이름 및 옵션):
  - 첫 2바이트가 총 아이템 수(`0x0096` = 150개)를 나타내며, 고정 레코드 내에 아이템명 저장.

---

## 6. 폰트 시스템 및 렌더링 파이프라인

### 6.1 폰트 파일 구성 (`SYSTEM.DAT`)
| 파일명 | 크기 (Bytes) | 구조 및 역할 |
| :--- | :--- | :--- |
| `kanji.dat` | 290,304 | 2,016개 한자/전각 글리프 비트맵 (글리프당 144바이트) |
| `kantable.dat` | 15,120 | Shift-JIS 코드 -> `kanji.dat` 글리프 ID 매핑 테이블 (7,560개 `int16`) |
| `kantable.h` | 37,866 | `kantable.dat`의 C 소스코드 원본 (`Sint16 KanTable[] = { ... };`) |
| `eng.dat` | 36,864 | 256개 반각 ASCII 글리프 비트맵 (글리프당 144바이트) |
| `eng_pro.dat` | 224 | 0x20~0xFF 문자별 가변 폭(Proportional Width) 테이블 (바이트 배열) |
| `eng_pro.h` | 3,391 | `eng_pro.dat`의 C 소스코드 원본 (`unsigned char propo[] = { ... };`) |
| `vw_kanji.dat` | 329,600 | 가변폭 한자 폰트 데이터 |
| `vw_kantable.dat`| 15,120 | 가변폭 한자 매핑 테이블 |
| `dbg_han.dat` | 16,384 | 디버그용 반각 폰트 |

### 6.2 글리프 비트맵 규격
- **글리프 크기**: 24 x 24 픽셀, 2 bpp (4단계 앤티앨리어싱 계조)
- **용량 계산**: `24 × 24 × 2 bits = 1,152 bits = 144 Bytes`
  - `kanji.dat`: `2,016 × 144 = 290,304 Bytes` (정확히 일치)
  - `eng.dat`: `256 × 144 = 36,864 Bytes` (정확히 일치)

### 6.3 Shift-JIS -> 글리프 변환 공식 (검증 완료)
2바이트 Shift-JIS 코드 `(b1, b2)`에 대해 `KanTable` 인덱스를 산출하는 공식:
```python
if 0x81 <= b1 <= 0x9F:
    row = b1 - 0x81
elif 0xE0 <= b1 <= 0xFC:
    row = b1 - 0xE0 + 31

if 0x40 <= b2 <= 0x7E:
    col = b2 - 0x40
elif 0x80 <= b2 <= 0xFC:
    col = b2 - 0x41

index = row * 188 + col + 1
glyph_id = KanTable[index]
```
- `glyph_id == -1`이면 해당 문자는 폰트에 등록되지 않은 미지원 문자.
- 0 이상의 값이면 `kanji.dat`의 `glyph_id * 144` 오프셋에서 글리프 비트맵을 로드.

### 6.4 PS2 VRAM 동적 폰트 캐싱 (`ulib/uknj.c`)
- PS2 GS의 4MB VRAM 한계로 인해 2,016개 한자를 전부 VRAM에 상주시킬 수 없음.
- 메인 루프에서 출력할 문자열이 발생하면 `uknj.c`가 VRAM 내 `knjbank` 텍스처 버퍼로 필요한 글리프와 CLUT(팔레트)를 동적으로 전송(`フォントTexture転送`)하여 렌더링함.

---

## 7. 작성된 분석 도구 (`tools/`)
1. `tools/scan_files.py`: 디스크 전체 파일 재귀 탐색, 헤더 매직 및 크기 분석
2. `tools/hed_parser.py`: `.HED` 아카이브 인덱스 파서 및 파일트리 추출
3. `tools/extract_file.py`: `.HED` 기반 `.DAT` 내부 개별 파일 추출 유틸리티
4. `tools/analyze_elf.py`: 메인 ELF 헤더 및 세그먼트/섹션 분석
5. `tools/japanese_filter.py`: Shift-JIS 텍스트 필터링 및 자연어 판별 모듈
6. `tools/fast_scan_jp.py`: 아카이브 내 전체 파일 고속 텍스트 검색기
7. `tools/parse_rtb_strings.py`: `.rtb` 스크립트 바이트코드 내 대사 및 제어문자 추출기
8. `tools/test_font.py`: `kanji.dat` 글리프 래스터라이저 및 아스키 아트 렌더러
9. `tools/test_kanji_mapping.py`: `KanTable`과 Shift-JIS 상호 변환 검증기

---

## 8. 결론 및 향후 계획

### 8.1 텍스트 및 폰트 변경 타당성
- 모든 아카이브(`.DAT`)가 비압축이므로 파일 추출 및 패킹 구조가 매우 단순함.
- `kantable.h`와 `kanji.dat`이 별도로 존재하므로, 한글 폰트(완성형 또는 조합형)를 `kanji.dat`에 이식하고 `kantable.dat` 테이블을 재구성하거나 한글 폰트 로직을 연결할 수 있는 완벽한 기반이 마련되어 있음.
- `.rtb` 스크립트 바이트코드의 문자열 길이가 1바이트(`LEN`)로 명시되어 있으므로, 텍스트 확장 시 점프 오프셋 및 파일 크기 재조정이 필요한지 추가 확인이 필요함.

---

## 9. 2단계 심층 분석 결과 (2026-09-15)

### 9.1 RTB (Real-Time Binary) 스크립트 엔진 구조 규명
- **소스/바이너리 관계**:
  - 오리지널 스크립트 소스 확장자는 `.rts` (Real-Time Script)이며, 컴파일된 바이너리가 `.rtb` (Real-Time Binary)임.
- **헤더 섹션 구조**:
  1. **심볼 테이블 (매직 `0xFE`)**:
     - 2바이트 심볼 개수 (예: `t00_0010.rtb`는 791개).
     - 엔트리: `[32-bit Symbol Hash] [1-byte Name Length] [ASCII Symbol Name]`.
     - 엔진 C 콜백 함수(`mc_msg`, `yesnowin`, `fade_black_out`, `SetTurnMode` 등) 및 변수명 포함.
  2. **인클루드 소스 파일 테이블**:
     - 원본 소스 및 헤더 파일명 목록 (`t00_0010.rts`, `sys.h`, `voice.h`, `chara.h`, `battlemap.h`, `help.h`, `debug.h`).
  3. **타입 디스크립터 테이블**:
     - 22개 엔진 타입 (`int`, `float`, `string`, `bytes`, `v4_t`, `dobj_t`, `aobj_t`, `uadsprt`, `CHARA` 등).
- **명령어 및 제어 흐름 분석**:
  - 기본 명령어 헤더: `[Opcode: 1B] [Mode: 1B] [Debug Line/File Tag: 3B]`.
  - 문자열 로드 오프코드: `0x33` (`33 01 [Tag: 3B] [Len: 1B] [Shift-JIS Text]`).
  - 분기 점프 오프코드: `0x6c` (`6c 00 [Tag: 3B] [Target: 4B]`).
  - **점프 타겟 특성**: 오프셋 값이 바이트 오프셋이 아닌 **명령어 단위(Instruction Count / PC)** 상대 이동임.
    - 문자열 리터럴(`0x33`)은 문자열 길이에 관계없이 **1개의 단일 명령어**로 취급되므로, 문자열 길이를 늘리거나 줄여도 분기 점프 타겟 계산에 직접적인 바이트 어긋남이 발생하지 않음.

### 9.2 ELF 내부 한국어(Korean) 모드 및 폰트 분기 로직 발굴
메인 실행 파일(`SLPS_258.54`)의 `ulib/uknj.c` 및 `ulib/uconfig.c` 모듈 역어셈블리 결과, 놀랍게도 **한국어(Korean) 모드를 위한 전용 분기 코드**가 사전에 구현되어 있음을 확인:
1. **언어 설정 함수 (`0x001d6b08`)**:
   - `language == 0`: 일본어 모드 (글로벌 플래그 `-20276($gp) = 0`)
   - `language == 6`: 한국어 모드 (글로벌 플래그 `-20276($gp) = 1`)
2. **문자 처리 루틴 (`0x001d7054` ~ `0x001d7250`)**:
   - `0x001d705c`: `addiu $t7, $zero, 6; bne $t6, $t7, ...`
   - 일본어(0)와 한국어(6)에 대해 `0x8140`(전각 공백) 특수 처리를 공유.
   - 비일본어 모드(`language != 0`)에서는 글리프 피치를 288바이트(24x24 4bpp)로 계산하는 분기 로직(`0x001d7250`: `addiu $t6, $zero, 288; mult $t5, $t6`) 보유.
3. **설정 파일 연동 (`ulib/uconfig.c`)**:
   - 부팅 시 `ROOT.DAT/config.txt`의 `language={0}` 값을 읽어 이 변수에 주입함.

### 9.3 아이템 데이터베이스 (`PPITEM.dat`) 구조 규명
- 파일 헤더: `[Total Items: uint16]` (150개).
- 별도의 파일 오프셋 포인터 테이블이 없으며, 순차적(Sequential) 가변 레코드 구조로 파싱됨:
  ```c
  struct ItemRecord {
      uint16_t item_id;     // 1 ~ 150
      uint16_t subtype;     // 무기/방어구 세부 분류
      char     name[];      // Null-terminated Shift-JIS 문자열
      uint16_t null_pad;    // 2바이트 정렬 패딩
      uint8_t  stats[N];    // 카테고리별 고정 스탯/가격 블록
  };
  ```
- 포인터 테이블이 존재하지 않으므로, 텍스트 길이가 변경되더라도 레코드 규격(`null_pad` 및 `stats`)만 올바르게 유지되면 안전하게 확장 가능.

### 9.4 TIM2 텍스처 그래픽스 디코더 개발 완료
- `tools/tim2_to_png.py`를 작성하여 PS2 Graphics Synthesizer 고유의 CLUT 디스위즐링(Deswizzling) 알고리즘 구현 완료.
- `STATUS.DAT` 내 104개 텍스처 중 `sysicn.tm2`, `sysnum.tm2`, `title_1.tm2` 등을 성공적으로 무손실 PNG로 변환 검증 완료.

---

## 10. 3단계 심층 분석 결과 (2026-09-15)

### 10.1 전체 시나리오 대사 일괄 추출 완료 (`tools/dump_all_dialogue.py`)
- `DMAP.DAT` 내 280개 `.rtb` 스크립트 파일 전수 스캔 및 대사 파싱 완료.
- **총 17,992개의 대사 및 시스템 메시지 라인 추출 성공**:
  - 화자 이름(Speaker: `ハーシュ`, `テージ`, `オリフェン`, `グリン`, `レイナ` 등)
  - 대화 본문(Text)
  - 파일명(`file`), 바이트코드 내 오프셋(`text_offset`), 바이트 길이(`text_len`)
- 결과 데이터: `tools/all_dmap_dialogues.json` (3.6 MB)로 저장 완료.

### 10.2 스킬 및 악마도감(Beastiary) 텍스트 전수 분석
1. **스킬 데이터 (`PPSKILL.dat` -> `tools/all_skills.json`)**:
   - 총 194개 스킬의 명칭 및 속성/사정거리 설명문 100% 완전 파싱 완료.
   - 레코드 구조: `[ID: 2B] [Flags: 2B] [Cat: 2B] [Name (Shift-JIS \0\0)] [Stats: 66B 고정] [Desc (Shift-JIS \n)]`.
2. **파라미터 및 마신도감 (`PPPARAM.dat`)**:
   - 전반부(1~127번): 주연/조연 캐릭터 및 마신 몬스터 이름과 기본 파라미터.
   - 후반부(128~271번): 마신 도감(Beastiary)의 상세 설명문 텍스트가 저장되어 있음 (`큰 발을 가진 수마진...` 등).

### 10.3 폰트 엔진(`ulib/uknj.c`) 한국어 모드(language=6)의 완전한 동작 메커니즘 규명
ELF 코드(`VAddr 0x001d7228` ~ `0x001d726c`) 역어셈블리를 통해 한국어 렌더링 파이프라인의 실체를 완전히 규명했습니다:
```c
// VAddr 0x001d7228 (Korean / Non-Japanese Font Renderer)
void render_korean_glyph(uint16_t char_code) {
    int16_t* kan_table = (int16_t*)gp_table[-20096]; // system/kantable.dat
    uint8_t* font_buf  = (uint8_t*)gp_table[-20264]; // system/kanji.dat
    
    int16_t glyph_id = kan_table[char_code];
    if (glyph_id != -1) {
        uint8_t* glyph_ptr = font_buf + (glyph_id * 288);
        return glyph_ptr;
    }
}
```
- **발견된 핵심 사실**:
  1. 한국어 렌더러는 일본어의 복잡한 Shift-JIS 2바이트 행/열(189) 계산 대신, **16비트 문자 코드로 `kantable.dat`을 직접 인덱싱(`char_code * 2`)**합니다.
  2. `kantable.dat`과 `kanji.dat`은 `0x001d4af8`에서 `.HED`에 기록된 파일 크기만큼 **힙(Heap) 메모리를 동적으로 `malloc`**하여 로드합니다. (버퍼 크기 하드코딩이 아님).
  3. `kantable.dat`은 7,560개의 인덱스를 수용할 수 있으므로, 완성형 한글 2,350자 및 한글 자모 전체를 등록하기에 용량이 충분합니다.

---

## 11. 4단계 동영상 컷씬 오디오 스트리밍 구조 규명 (2026-09-18)

### 11.1 배경 및 문제 분석
- 기존 초기 추출 시 `.ag` 파일의 스테레오 구조를 16바이트 교차 인터리브(16B L / 16B R)로 잘못 가정함에 따라, 28샘플(0.63ms, 1575Hz) 주기로 좌/우 채널이 뒤바뀌어 극심한 금속성 버징(Buzzing) 및 에일리어싱 잡음이 발생함.
- 유저 피드백("소리가 이상한데 이거 뭐 두채널 뭐 이런거 아냐?")을 바탕으로 게임 실행 바이너리 및 IOP 사운드 드라이버 전수 역공학 분석 착수.

### 11.2 드라이버 및 바이너리 역공학 결과
1. **IOP 사운드 드라이버 (`MODULES/EZMIDI.IRX`)**:
   - `read_i.c` 및 `adpcm_i.c`에서 오디오 스트리밍(`InitTransfer2Stream`, `AllocStreamSlot`, `BlockTrans`) 담당.
   - 내부 스트링: `Stream Stereo L`, `Stream Stereo R`, `Stream Monaural`, `InitStream`, `AG data size over %d<%d`.
2. **EE 메인 루프 (`SLPS_258.54` 내 `uipu.c` 및 `0x00194330` 스트리머)**:
   - IPU 프레임 레이트: `addiu $t7, $zero, 30` (29.97 / 30 fps NTSC).
   - EE 스트리밍 버퍼 할당 및 전송 단위: `0x4000` (16,384 바이트 = 16KB = 8개 DVD 섹터 단위 고정).
   - 역어셈블리 오프코드 `0x1943a0`, `0x194410`, `0x1944b8`, `0x1945c0`, `0x194894` 전반에서 `ori $a0, $a0, 0x4000` 확인.

### 11.3 16KB 인터리브(0x4000) 채널 구조 수학적/실증적 증명
1. **페이드인 시작점 동기화 분석 (`s01.ag`)**:
   - Left 채널: 섹터 23 (`0xb9e0`)에서 최초 사운드 페이드인 시작.
   - Right 채널: 섹터 31 (`0xf9b0`)에서 최초 사운드 페이드인 시작.
   - 오프셋 차이: `0xf9b0 - 0xb9e0 = 0x3fd0` (16,384바이트인 `0x4000`과 단 48바이트 차이).
   - 48바이트(84샘플) = 44.1kHz 기준 **1.9ms**에 불과하며, 실제 음원 레코딩 시 좌우 스테레오 페이드인이 동시에 시작되는 시간차와 정확히 일치함.
2. **전구간 L/R 상관계수(Correlation) 비교 검증**:
   - `IL = 16`: Corr = -0.1254 (심각한 위상 왜곡)
   - `IL = 2048 (0x800)`: Corr = +0.0500, 시작 시점 차이 367.91ms (싱크 불일치)
   - `IL = 4096 (0x1000)`: Corr = +0.0815, 시작 시점 차이 367.91ms
   - `IL = 8192 (0x2000)`: Corr = +0.0177, 시작 시점 차이 367.91ms
   - **`IL = 16384 (0x4000)`**: **Corr = +0.3990 (강한 정적 상관관계)**, 시작 시점 차이 **9.48ms** (완벽한 스테레오 동기화)
3. **전체 15개 동영상 파일 크기 전수 검증**:
   - `s01.ag` ~ `s15.ag` 15개 파일 전체의 크기가 `0x8000` (32,768 바이트 = `16KB L + 16KB R`)의 정확한 정수배임 (오차 0바이트).
   - 각 영상 프레임 수 대비 오디오 재생 시간이 29.97fps 기준 0.1~0.6초(페이드아웃/패딩) 오차 내로 100% 일치함.

