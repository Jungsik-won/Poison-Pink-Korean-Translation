# HANDOVER v1 검수 결과

2026-09-15. 범위: 현재 로컬 원본, 기존 Python 분석 도구, JSON 추출물, ELF 원시 명령어.
외부 웹 자료의 재인용이나 에뮬레이터 실행 결과를 근거로 한 검수가 아니다.

## 수정 우선순위

| 중요도 | 기존 주장 | 확인 결과 / 조치 |
| --- | --- | --- |
| 치명 | language=6에서 한국어 플래그=1 | 실제 명령어는 0/6 모두 플래그=0. 경로 A의 활성화 설명 폐기 |
| 치명 | 한국어 글리프 주소=ID×288 | ID 하위 1비트 출력과 우측 시프트가 누락됨. 실제 관측은 `(ID>>1)×288` |
| 치명 | 직접 16비트 한국어 인덱싱 | table 인덱스는 앞선 코드에서 산출한 `$t4`; 원시 문자 코드와 혼동. 해당 루틴은 language!=0일 때 테이블 접근을 건너뜀 |
| 치명 | 문자열 길이를 자유롭게 바꿔도 점프 안전 | 완전한 명령 파서/VM 추적/실행 실험 없음. `analyze_opcodes.py`는 후보 정수 출력에 그침 |
| 높음 | ELF 주소가 검증됨 | LOAD의 파일 오프셋 0x1000 누락. 기존 단순 산식으로 계산한 주소는 실제 VA보다 0x1000 큼 |
| 높음 | HED 디렉터리 offset=2 | 실제 SYSTEM/cir_sdw=17, DMAP/script=2779. HED 레코드 범위를 가리킴 |
| 높음 | Shift-JIS 인덱스는 row×188+col+1 | C 타입명 숫자 오염으로 +1 발생. ELF에는 189가 등장하며 0x7f 자리를 건너 압축하지 않음 |
| 높음 | 194개 스킬 100% 정상 파싱 | 194행 중 9행에 U+FFFD; 오류 무시 디코딩. 66바이트 블록/0 패딩 규칙 미확정 |
| 높음 | 도감 271개 구조 규명 | 산출물은 135행, ID 검색 오탐 포함. 128~271 도감 구획 입증 없음 |
| 높음 | 아이템 이름 확장 안전 | 첫 레코드 분석만 존재. 로더/전체 필드/참조 검증 없음 |
| 높음 | 폰트 크기 확장을 엔진이 정상 수용 | HED 길이 기반 할당만으로 캐시/힙/상한 안전성을 증명할 수 없음. 제시 주소와 호출 의미도 다시 검증 필요 |
| 중간 | 17,992개 대사 완전 추출 | 이름 길이 비교로 화자/본문을 합친 후보 묶음. `next_op`도 검사 없이 저장하며 리소스 제외 목록도 부분적 |
| 중간 | text_offset은 텍스트 위치 | 기존 JSON의 text_offset은 0x33 위치. 텍스트 바이트는 +6 |
| 중간 | TM2 디코더 무손실 완성 | 단일 이미지/바이트 인덱스 중심 구현. 4bpp, direct color, 이미지 스위즐, 다중 picture, mipmap 검증 없음. alpha 변환도 원시값 왕복 불가 |
| 중간 | 아카이브의 모든 리소스가 비압축 | 컨테이너의 직접 접근 사실만 확인. 내부 리소스 자체의 인코딩/압축 여부는 별도 |

## ELF 근거: 주소와 분기

ELF program header: `PT_LOAD offset=0x1000, vaddr=0x100000`.
현재 원본의 해당 세그먼트에서 `file offset = VA - 0x100000 + 0x1000`.
기존 문서의 모든 주소가 같은 의미의 유효 함수라는 뜻이 아니다. 범위별 재해석이 필요하다.

```text
VA 0x001d5b08  10800004  beq   a0, zero, 0x001d5b1c
VA 0x001d5b0c  af84b0c8  sw    a0, -20280(gp)   ; delay slot
VA 0x001d5b10  240f0006  addiu t7, zero, 6
VA 0x001d5b14  148f0003  bne   a0, t7, 0x001d5b24
VA 0x001d5b18  240f0001  addiu t7, zero, 1       ; delay slot
VA 0x001d5b1c  03e00008  jr    ra
VA 0x001d5b20  af80b0cc  sw    zero, -20276(gp)  ; delay slot, a0=0/6
VA 0x001d5b24  03e00008  jr    ra
VA 0x001d5b28  af8fb0cc  sw    t7, -20276(gp)    ; delay slot, other modes
```

다른 언어 처리 기능이 없다는 뜻은 아니다. 위 명령어는 기존 문서의 플래그 설명이 반대라는 직접 근거다.

```text
VA 0x001d61e0  lw language
VA 0x001d61e4  bne language, zero, 0x001d624c
VA 0x001d61e8  t5 = 0                         ; delay slot
VA 0x001d61ec  t7 = 189
... Shift-JIS code range calculation into t4 ...
VA 0x001d622c  table = *(gp - 20096)
VA 0x001d6230  t7 = t4 << 1
VA 0x001d6238  t5 = signed16(table + t7)
... missing glyph fallback ...
VA 0x001d624c  t7 = t5 & 1
VA 0x001d6250  t6 = 288
VA 0x001d6254  t5 = t5 >> 1
VA 0x001d6258  *a1 = t7
VA 0x001d625c  mult t5, t5, t6               ; R5900 result destination
VA 0x001d6260  font = *(gp - 20264)
VA 0x001d6264  t7 = font + t5
```

원시 명령어는 [../reports/audit.json](../reports/audit.json)의 `elf.evidence`에 기록했다.
기존 간이 역어셈블러는 branch-likely, movn, R5900 확장 등 미지원 명령이 있어, 알 수 없는 명령을 무시하고 흐름을 확정하면 안 된다.

## 폰트 근거와 실험 기준

- C initializer와 binary int16 7,560개가 정확히 일치한다.
- `table[0]=0`, `[1]=1`, `[2]=2`, `[3]=-1`. `Sint16`의 16은 데이터가 아니다.
- 첫 영역에서 `index=(code>>8)*189+(code&255)-24445`로 0x8140→0, 0x8141→1이 된다.
- 다른 코드 범위에는 별도 보정/조건부 이동이 존재한다. 첫 영역 공식을 전 코드에 적용하면 안 된다.
- 폰트 크기 `290304=1008×288=2016×144`만으로 물리 저장 규격을 결정할 수 없다.
- 주소 계산과 `0x3333/0xCCCC` 마스크는 글리프 2개를 288B에 함께 저장한다는 해석을 지지한다.
- 실험: 같은 pair의 짝수/홀수 글리프를 서로 다른 비대칭 패턴으로 바꾸고 일본어 모드에서 각 슬롯을 출력한다. 좌우/상하 방향, 비트 선택, 투명도, 획 손상 여부를 기록한다.

## 추출물 검수

| 산출물 | 실제 행 수 | 알려진 문제 |
| --- | ---: | --- |
| all_dmap_dialogues.json | 17,992 | `, `, ` -> ` 등 비대사 포함, 화자 휴리스틱 |
| all_skills.json | 194 | 9행 U+FFFD, 첫 설명도 `ﾎ属性`로 시작하여 바이트 경계 의심 |
| all_characters_and_monsters.json | 135 | 3행 U+FFFD, ID 2의 name이 `d`인 오탐 등 |
| all_params.json | 10 | 빈 name 2행, 제어문자/이상 문자열 포함 |

해당 JSON들은 수정하지 않고 조사 이력으로 남겼다. 새 후보 파일은 CP932 디코딩 실패도 raw_hex와 함께 보존한다.
31,520행의 번역 양식은 검토용이며 초기 target은 모두 비어 있다. 빈 양식의 lint 통과는 번역 완료나 게임 삽입 가능을 뜻하지 않는다.

## 완료한 검증 / 남은 검증

완료: 11개 HED 전체 순회, 디렉터리 범위 확인, HED byte roundtrip, DAT 범위·비중첩·0x4000 정렬,
원본 해시 생성, 280 RTB 심볼 테이블 길이 범위 확인과 패턴 추출, C/binary font table 비교, 기존 JSON 품질 통계.

남음: 완전 VM 파싱, DB lossless 왕복, 폰트 pair 화면 검증, language 전체 분기 추적, 힙/캐시 확장,
아카이브 재빌드 부팅, ISO/추출 폴더 대조 및 LBA 보존, 게임 전체 화면 QA.
