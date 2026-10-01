# Poison Pink (PS2 / SLPS-25854) 한글화 패치 기술 인계서
**문서 버전**: 1.0.0  
**작성일**: 2026-09-15  
**대상 독자**: 후속 번역가, 프로그래머, 롬해커, 패치 엔지니어링 협업팀

---

## 1. 프로젝트 개요 및 환경 정보

- **게임명**: Poison Pink (ポイズンピンク / 북미 발매명: Eternal Poison)
- **개발사 / 퍼블리셔**: Flight-Plan (개발) / Banpresto (발매)
- **플랫폼 / 시리얼**: Sony PlayStation 2 (NTSC-J) / `SLPS-25854` (버전 1.03)
  - `SYSTEM.CNF` 내용: `BOOT2 = cdrom0:\SLPS_258.54;1`, `VER = 1.03`, `VMODE = NTSC`
- **CPU 아키텍처**: MIPS R5900 (Emotion Engine) 32-bit Little Endian
- **컴파일러 툴체인**: SN Systems ProDG for PlayStation 2

---

## 2. 디렉터리 및 아카이브 시스템 (`.HED` + `.DAT`)

게임 내 모든 데이터는 `DATA/` 폴더 아래 11개 카테고리의 짝을 이루는 인덱스 파일(`.HED`)과 데이터 컨테이너(`.DAT`)로 구성되어 있습니다.

### 2.1 11대 아카이브 카테고리
1. `DMAP` (419MB): **가장 중요**. 메인 시나리오, 퀘스트, 아지트 이벤트 스크립트 바이트코드(`*.rtb`), 맵 텍스처
2. `STATUS` (12MB): **핵심 DB**. 아이템(`PPITEM.dat`), 스킬(`PPSKILL.dat`), 파라미터/도감(`PPPARAM.dat`), 메뉴 UI 텍스처
3. `SYSTEM` (1.3MB): **폰트 시스템**. `kanji.dat`, `kantable.dat`, `eng.dat`, `eng_pro.dat`, `kantable.h`
4. `ROOT` (16KB): 부팅 설정 파일 `config.txt` (언어 모드 설정 포함)
5. `LFACE` (14MB): 대화창용 전신/얼굴 고해상도 포트레이트 (`.tm2`)
6. `SFACE` (2.2MB): 미니맵/상태창용 소형 포트레이트 (`.tm2`)
7. `BATTLE` (348MB): 전투 3D 모델(`upm`), 모션, 전투 텍스처(`tm2`), 이펙트(`upl`, `ups`)
8. `CLIP` (19MB): 컷씬 클립 연출 데이터
9. `SOUND` (716MB): BGM(`ag`), 음성 및 효과음(`ags`, `bd`, `th`)
10. `MOVIE` (1.1GB): 동영상 스트림 (`.ipu`)
11. `MODULES` (753KB): IOP 런타임 드라이버 (`.irx`, `IOPRP300.IMG`)

### 2.2 아카이브 구조 및 패킹 규격
- **비압축 선형 아카이브**:
  - `*.DAT` 내부의 파일들은 **전혀 압축되지 않은 상태(Uncompressed)**로 순차 배치되어 있습니다.
  - 각 파일의 시작 오프셋은 PS2 CD/DVD 섹터 크기인 `0x800` (2,048 바이트) 또는 `0x4000` (16,384 바이트)으로 정렬(Padding)되어 있습니다.
- **`.HED` 엔트리 구조 (44바이트 고정 레코드)**:
  ```c
  #pragma pack(push, 1)
  struct HedEntry {
      uint32_t offset;       // DAT 파일 내 절대 오프셋 (바이트 단위, 디렉터리 식별자일 경우 2)
      uint32_t size;         // 파일 크기 (바이트 단위, 디렉터리일 경우 하위 항목 수)
      char     filename[32]; // Null-terminated 파일/디렉터리 이름
      uint32_t timestamp;    // 32-bit Little-Endian Unix Timestamp
  }; // Total: 44 bytes (0x2C)
  #pragma pack(pop)
  ```
  - 디렉터리 종료 마커: `filename = "--DirEnd--"`
  - 상위 디렉터리 마커: `filename = ".."`

---

## 3. 스크립트 바이트코드(`*.rtb`) 구조 및 대사 패치 명세

게임의 모든 대사는 `DMAP.DAT` 내 280개 `.rtb` (Real-Time Binary) 파일에 수록되어 있습니다.

### 3.1 RTB 파일 헤더 구조
1. **심볼 테이블 (시작 매직: `0xFE`)**:
   - `0x00`: `0xFE`
   - `0x01`: 2바이트 심볼 총 개수 (Little-Endian uint16)
   - 각 엔트리: `[32-bit Symbol Hash] [1-byte Name Length] [ASCII Name]`
   - 예: `mc_msg` (메시지창 오픈), `yesnowin` (선택지창), `fade_black_out`, `PlayMovie` 등
2. **인클루드 소스 파일 테이블**:
   - 컴파일 전 원본 소스(`.rts`) 및 헤더 파일 목록 (예: `t00_0010.rts`, `sys.h`, `chara.h` 등)
3. **타입 디스크립터 테이블**:
   - 22개 엔진 타입 (`int`, `string`, `bytes`, `v4_t`, `dobj_t`, `CHARA` 등)

### 3.2 텍스트 리터럴 명령어 (`0x33`)
대사 및 화자 이름은 바이트코드 내에서 opcode `0x33`으로 로드됩니다:
$$\mathbf{33\ 01\ [Tag:\ 3B]\ [Len:\ 1B]\ [Shift\text{-}JIS\ Text]\ 65\ 01\ [Tag:\ 3B]}$$
- `33 01`: 문자열 로드 오프코드 및 플래그
- `Tag (3B)`: 원본 소스 라인 및 파일 추적용 디버그 태그 (실행 흐름에 영향 없음)
- `Len (1B)`: 문자열의 **바이트 길이** (1바이트 uint8)
- `Text`: Shift-JIS 인코딩 문자열 (개행은 `\n` = `0x0A`)
- `65 01`: 다음 명령 또는 피연산자 처리

### 3.3 대화 블록 호출 흐름 예시
```
1. Opcode 0x33 -> 화자 이름 로드 (예: Len=4, Text="ラキ")
2. Opcode 0x33 -> 대사 본문 로드 (예: Len=22, Text="戦い方の基本を教えるぞ")
3. Opcode 0x68 -> mc_msg (해시: 0xdf9f29f3) 호출하여 대화창 출력
4. (선택지 필요시) Opcode 0x68 -> yesnowin (해시: 0x88c985e2) 호출
```

### 3.4 분기 점프 오프코드 (`0x6c`) 특성 (핵심)
- **오프코드 구조**: `6c 00 [Tag: 3B] [Target: 4B int32]`
- **점프 계산 방식**: **절대 바이트 주소가 아닌 명령어 단위(Instruction Count / PC) 상대 이동**
- **패치 영향**: 문자열 리터럴(`0x33`)은 텍스트의 바이트 길이가 몇 바이트로 늘어나거나 줄어들어도 **'단 1개의 명령어'**로 계산됩니다. 따라서 **대사 길이를 자유롭게 확장해도 뒤따르는 조건 분기 점프가 깨지지 않습니다.**

---

## 4. 데이터베이스 파일 구조 (`STATUS.DAT`)

### 4.1 `PPITEM.dat` (아이템 DB, 150종)
- **헤더**: `[Total Items: uint16]` (`0x0096` = 150)
- **레코드 구조** (포인터 테이블 없는 순차 가변 레코드):
  ```c
  struct ItemRecord {
      uint16_t item_id;     // 1 ~ 150
      uint16_t subtype;     // 무기/방어구 세부 분류
      char     name[];      // Null-terminated Shift-JIS 문자열
      uint16_t null_pad;    // \0\0 패딩
      uint8_t  stats[N];    // 카테고리별 고정 스탯/가격 블록 (약 19~23바이트)
  };
  ```
- 포인터 테이블이 없으므로 아이템 이름을 한글로 길게 늘려도 `stats` 위치만 맞추면 정상 로드됩니다.

### 4.2 `PPSKILL.dat` (스킬 DB, 194종)
- **헤더**: `[Total Skills: uint16]` (`0x00C2` = 194)
- **레코드 구조**:
  ```c
  struct SkillRecord {
      uint16_t skill_id;    // 1 ~ 194
      uint16_t flags;
      uint16_t category;
      char     name[];      // Null-terminated Shift-JIS 문자열 (\0\0 패딩)
      uint8_t  stats[66];   // 정확히 66바이트 고정 스탯/효과 블록
      char     desc[];      // 개행(\n) 포함 Null-terminated 설명문
  };
  ```
- 스킬 설명문은 `\n` 개행을 포함하며, 66바이트 스탯 블록 뒤에 가변 길이로 배치됩니다.

### 4.3 `PPPARAM.dat` (유닛 파라미터 및 마신도감, 271종)
- **헤더**: `[Total Entries: uint16]` (`0x010F` = 271)
- **구성**:
  - `1 ~ 127번`: 플레이어 캐릭터, 동료, 주요 보스 및 마신 유닛 이름/스탯
  - `128 ~ 271번`: **마신 도감(Beastiary) 상세 해설문** 텍스트 수록

---

## 5. 폰트 엔진 및 한국어 모드 (`ulib/uknj.c`)

### 5.1 파일 구성 (`SYSTEM.DAT`)
- `kanji.dat` (290,304 B): 2,016개 한자/전각 글리프 비트맵 (글리프당 144바이트)
- `kantable.dat` (15,120 B): Shift-JIS 코드 $\rightarrow$ 글리프 ID 매핑 테이블 (7,560개 `int16` 배열)
- `kantable.h` (37,866 B): 매핑 테이블 C 소스 원본 (`Sint16 KanTable[] = { ... };`)
- `eng.dat` (36,864 B): 256개 반각 ASCII 글리프 비트맵 ($256 \times 144$ B)
- `eng_pro.dat` (224 B): 0x20~0xFF 프로포셔널 폰트 문자 너비 테이블 (`unsigned char propo[]`)

### 5.2 글리프 비트맵 규격
- **해상도**: **$24 \times 24$ 픽셀**
- **색심도**: **2 bpp** (4단계 안티앨리어싱 계조: `00=투명`, `01=연함`, `10=중간`, `11=진함`)
- **용량**: $24 \times 24 \times 2 \div 8 = \mathbf{144\text{ Bytes}}$

### 5.3 내장 한국어(Korean) 모드 메커니즘
`SLPS_258.54` 바이너리 역어셈블리 결과, 개발사 Flight-Plan이 사전에 구현해 둔 **한국어 모드 분기**가 존재합니다:

1. **활성화 방법**:
   - `ROOT.DAT` 내 `config.txt`에서 `language={0}`을 **`language={6}`**으로 변경.
2. **글로벌 플래그 세팅 (`VAddr 0x001d6b08`)**:
   - `language == 6`일 때 `-20276($gp) = 1` (한국어 모드 활성화 플래그) 세팅.
3. **한국어 렌더러 분기 (`VAddr 0x001d83ac` $\rightarrow$ `0x001d7228`)**:
   ```c
   // VAddr 0x001d7228: Korean Direct Indexing Renderer
   void* get_korean_glyph(uint16_t char_code) {
       int16_t* kan_table = (int16_t*)gp[-20096]; // system/kantable.dat
       uint8_t* font_buf  = (uint8_t*)gp[-20264]; // system/kanji.dat
       
       int16_t glyph_id = kan_table[char_code];    // 직접 인덱싱!
       if (glyph_id == -1) return NULL;
       
       return font_buf + (glyph_id * 288);        // 피치: 288 Bytes (24x24 4bpp)
   }
   ```
4. **메모리 할당 동적성 (`VAddr 0x001d4af8`)**:
   - 폰트 파일 로더가 고정 크기 버퍼가 아닌, **`.HED`에 명시된 파일 크기만큼 힙 메모리를 동적으로 `malloc`**합니다. 글리프 수가 늘어나 파일이 커져도 엔진이 정상 수용합니다.

---

## 6. 추천 패치 구현 경로 (2가지 선택지)

### 경로 A. 엔진 내장 한국어 모드 활용 (정석 경로)
- **방법**:
  1. `ROOT.DAT/config.txt`의 `language={0}`을 `language={6}`으로 변경.
  2. 한글 폰트를 $24 \times 24$ 4bpp (글리프당 288바이트) 비트맵으로 렌더링하여 `kanji.dat` 생성.
  3. `kantable.dat`에 16비트 완성형 코드 $\rightarrow$ 글리프 번호 매핑 테이블 기록.
  4. 대사 텍스트를 해당 16비트 코드로 저장.
- **장점**: Shift-JIS의 복잡한 189진법 행/열 인덱싱을 거치지 않고 직관적인 16비트 인덱싱 사용 가능.

### 경로 B. 일본어 Shift-JIS 슬롯 리매핑 (안전 경로)
- **방법**:
  1. `language={0}` (일본어 모드 유지).
  2. 한글 완성형 2,350자 글리프를 $24 \times 24$ 2bpp (글리프당 144바이트)로 `kanji.dat`에 생성.
  3. `kantable.dat`의 일본어 한자 영역에 한글 완성형 2,350자를 1:1로 매핑.
  4. 번역 대사는 해당 매핑 테이블의 가상 Shift-JIS 코드로 인코딩하여 `.rtb`에 삽입.
- **장점**: 기존 일본어 폰트 렌더러 파이프라인(144B 피치)을 100% 그대로 활용하므로 부작용 위험 없음.

---

## 7. 구축된 도구 및 추출 자산 목록 (`tools/`)

협업팀이 즉시 활용할 수 있도록 모든 데이터 추출 스크립트와 파싱 결과물이 준비되어 있습니다:

| 파일/도구 | 형식 | 설명 |
| :--- | :--- | :--- |
| `tools/all_dmap_dialogues.json` | JSON (3.5MB) | **280개 RTB 파일에서 추출된 17,992개 대사 라인** (화자, 텍스트, 오프셋 포함) |
| `tools/all_skills.json` | JSON (27KB) | **194개 전체 스킬 명칭 및 설명문 DB** |
| `tools/all_characters_and_monsters.json` | JSON (13KB) | **주요 캐릭터 및 마신 몬스터/도감 명칭 DB** |
| `tools/dump_all_dialogue.py` | Python | RTB 파일 전체 대사 추출기 |
| `tools/hed_parser.py` | Python | `.HED` 아카이브 인덱스 파서 |
| `tools/extract_file.py` | Python | `.HED`/`.DAT`에서 개별 파일 추출 도구 |
| `tools/parse_skills.py` | Python | `PPSKILL.dat` 파서 |
| `tools/parse_items.py` | Python | `PPITEM.dat` 파서 |
| `tools/parse_all_params.py` | Python | `PPPARAM.dat` 파서 |
| `tools/tim2_to_png.py` | Python | PS2 GS 팔레트 스위즐링을 복원하는 무손실 TIM2 $\rightarrow$ PNG 디코더 |
| `tools/test_font.py` | Python | `kanji.dat` 144바이트 글리프 래스터라이저 및 아스키아트 렌더러 |
| `tools/trace_language_mode.py` | Python | 메인 ELF 언어 플래그 추적 및 역어셈블러 |

---

## 8. 후속 협업팀을 위한 작업 체크리스트

1. [ ] **번역 작업**: `tools/all_dmap_dialogues.json` 및 `tools/all_skills.json` 번역 진행.
2. [ ] **폰트 제작**: 폰트 래스터라이저를 이용해 $24 \times 24$ 한글 글리프 생성 (`kanji.dat`).
3. [ ] **매핑 테이블 빌드**: `kantable.dat` 생성 (선택한 경로 A 또는 B에 맞춤).
4. [ ] **리인젝터 제작**: 번역된 문자열을 `.rtb`에 주입하고 `text_len` 및 파일 크기 갱신.
5. [ ] **아카이브 리패킹**: 수정된 파일들을 `.DAT`에 순차 배치(0x800 섹터 정렬)하고 `.HED` 오프셋/크기 갱신.
6. [ ] **ISO 빌드 및 검증**: PCSX2 에뮬레이터에서 텍스트 출력, 창 넘침, 선택지 동작 검증.

---
*본 문서는 Antigravity 리버스 엔지니어링 파이프라인에 의해 검증된 실제 MIPS 역어셈블리 및 바이너리 덤프 근거를 바탕으로 작성되었습니다.*
