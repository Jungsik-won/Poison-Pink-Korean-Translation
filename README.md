# Poison Pink 한국어화 프로젝트

> [!WARNING]
> **아직 완전 한글화가 아닌 개발·검수 중인 버전이며, 미번역 이미지와 추가 검수가 필요한 내용이 남아 있습니다.**
> 전체 구간의 실제 플레이 검증이 끝난 완성판이 아닙니다. 세이브를 백업하고 개발판으로 이용해 주세요.

PlayStation 2용 일본판 **Poison Pink**를 한국어로 즐길 수 있도록 텍스트, UI 이미지, 지도, 영상 자막을 연구하고 패치하는 비공식 팬 프로젝트입니다. 원본 게임 데이터는 배포하지 않으며, 정품 일본판 디스크 이미지에 적용하는 xdelta 차분 패치만 Release에서 제공합니다.

## 최신 개발판

**v0.1.0-dev · DMAP flow v1**

- 누적 한국어 대사 및 UI 작업 반영
- 지역명 이미지 11종 최신본 반영
- 월드/지역 지도 이미지 최신본 반영
- 상점 메시지와 컨트롤러 안내문 반영
- 클래스 체인지 관련 문구 수정 반영
- PCSX2 대화 표시 호환 패치 동봉
- 구조·해시·재구성 검증 완료
- 전체 게임 플레이와 모든 분기의 런타임 검증은 미완료

| 지역명 이미지 | 지도 이미지 |
|---|---|
| ![지역명 이미지 예시](artwork/region-names/bf_nm_s.png) | ![지도 이미지 예시](artwork/maps/vd010030.png) |

## 다운로드와 적용

1. 이 저장소의 **Releases**에서 `Poison_Pink_Korean_DMAP_flow_v1.xdelta`를 받습니다.
2. 본인이 소유한 일본판 ISO의 SHA-256이 아래 원본 해시와 일치하는지 확인합니다.
3. [xdelta3](https://github.com/jmacd/xdelta)를 설치합니다.
4. Release의 자동 적용 스크립트 또는 아래 명령을 사용합니다.

```bash
xdelta3 -d -s "Poison Pink (Japan).iso" \
  "Poison_Pink_Korean_DMAP_flow_v1.xdelta" \
  "Poison Pink (Japan) - Korean DMAP flow v1.iso"
```

macOS/Linux에서는 `scripts/apply_patch_ko.sh`, Windows PowerShell에서는 `scripts/apply_patch_ko.ps1`을 사용할 수 있습니다. 두 스크립트 모두 원본·패치·출력 해시를 확인하며 기존 출력 파일을 덮어쓰지 않습니다.

### 검증값

| 항목 | 값 |
|---|---|
| 지원 원본 | Poison Pink 일본판 ISO |
| 원본 ISO 크기 | 4,245,454,848 bytes |
| 원본 SHA-256 | `081e5c921fc2b0f517f007dfe053935578174a6880949de961e273426b216103` |
| xdelta 크기 | 311,221,958 bytes |
| xdelta SHA-256 | `8e56374561879106237e04ca3aa4875462bf0743aeac917c0987749bc5fe2a55` |
| 출력 ISO 크기 | 4,245,454,848 bytes |
| 출력 SHA-256 | `b1ebb5db3d0613ea9fe1160f6636c7481fb4d71c43e6b2d9b67f366ea9ca06b2` |

패치 적용 후 ISO가 약 4.25GB인 것은 패치가 원본에 파일을 단순 추가하는 방식이 아니라, 에뮬레이터가 읽을 수 있는 **완전한 디스크 이미지 전체를 재구성**하기 때문입니다. 다운로드하는 xdelta 파일 자체는 약 297MiB이며, 완성 ISO와 원본 ISO를 동시에 보관하면 저장 공간이 두 배가량 필요합니다.

## PCSX2 대화 표시 호환 패치

일부 대화의 표시에 필요한 PCSX2 패치는 `release/pcsx2/SLPS-25854_565FA10D.pnach`에 있습니다. 자세한 배치 방법은 같은 폴더의 `README.txt`를 참고하세요. Release에도 호환 패키지를 별도 자산으로 제공합니다.

## 현재 알려진 한계

- 전체 게임의 처음부터 끝까지 실제 플레이 검증이 끝나지 않았습니다.
- 일부 이미지와 문맥 의존 문장은 추가 번역·검수가 필요합니다.
- 영상 자막 중 노래 가사 등 일부 표현은 추가 확인이 필요합니다.
- RTB 크기 변경 제어 흐름, 폰트 용량, 아카이브 무변경 부팅 관련 검증 게이트가 아직 닫히지 않았습니다.
- PCSX2 버전과 설정에 따라 표시 결과가 다를 수 있습니다.

## 저장소 구성

- `localization/` — 번역 DB, 용어집, UI/시스템 메시지 설정, 검수 기록
- `artwork/` — 최신 지역명 11종과 지도 한국어 이미지
- `tools/` — 추출·분석·빌드·검증 도구
- `review/latest/` — 최신 전체 대사 검수본과 수정 내역
- `reports/` — 최신 빌드 및 잔여 작업 검증 보고서
- `docs/DEVELOPMENT_HANDOVER.md` — 다음 작업을 바로 이어가기 위한 상세 인계 문서
- `release/` — 적용 안내, 해시, PCSX2 호환 자료

빌드를 다시 진행할 때는 먼저 [개발 인계 문서](docs/DEVELOPMENT_HANDOVER.md)와 [파이프라인 문서](docs/LOCALIZATION_PIPELINE.md), `localization/pipeline.json`을 함께 확인하세요.

## 배포 원칙

- 원본 또는 수정 ISO, 추출한 원본 게임 자산, 영상·음악, 세이브·메모리카드는 저장소와 Release에 포함하지 않습니다.
- 패치는 이용자가 소유한 정품 일본판에만 적용해야 합니다.
- 게임과 관련 상표·저작권은 각 권리자에게 있습니다. 본 프로젝트는 비공식·비영리 팬 작업입니다.

