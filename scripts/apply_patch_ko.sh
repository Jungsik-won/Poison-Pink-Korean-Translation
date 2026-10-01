#!/usr/bin/env bash
set -euo pipefail

SOURCE_SHA256="081e5c921fc2b0f517f007dfe053935578174a6880949de961e273426b216103"
PATCH_SHA256="02d32af31433a7016a94e49f93efdd97d5bb1dc6dd6a3672ad2d9fb6c0715714"
OUTPUT_SHA256="f7276bfe1da4b9599d5242daa74ee094ac87e3044173e3c943b6320890fed072"
PATCH_NAME="Poison_Pink_Korean_standalone_v1.xdelta"

source_iso="${1:-}"
output_iso="${2:-Poison Pink (Japan) - Korean standalone v1.iso}"
patch_file="${3:-$PATCH_NAME}"

if [[ -z "$source_iso" ]]; then
  echo "사용법: $0 <일본판 원본 ISO> [출력 ISO] [xdelta 패치]" >&2
  exit 2
fi

command -v xdelta3 >/dev/null 2>&1 || {
  echo "오류: xdelta3를 먼저 설치해 주세요." >&2
  exit 1
}

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

[[ -f "$source_iso" ]] || { echo "오류: 원본 ISO를 찾을 수 없습니다: $source_iso" >&2; exit 1; }
[[ -f "$patch_file" ]] || { echo "오류: 패치를 찾을 수 없습니다: $patch_file" >&2; exit 1; }
[[ ! -e "$output_iso" ]] || { echo "오류: 출력 파일이 이미 있습니다: $output_iso" >&2; exit 1; }

actual_source="$(sha256_file "$source_iso")"
[[ "$actual_source" == "$SOURCE_SHA256" ]] || {
  echo "오류: 지원하는 일본판 원본 ISO가 아닙니다." >&2
  echo "기대값: $SOURCE_SHA256" >&2
  echo "실제값: $actual_source" >&2
  exit 1
}

actual_patch="$(sha256_file "$patch_file")"
[[ "$actual_patch" == "$PATCH_SHA256" ]] || {
  echo "오류: 패치 파일의 해시가 일치하지 않습니다." >&2
  exit 1
}

xdelta3 -d -s "$source_iso" "$patch_file" "$output_iso"

actual_output="$(sha256_file "$output_iso")"
[[ "$actual_output" == "$OUTPUT_SHA256" ]] || {
  echo "오류: 생성된 ISO의 해시가 일치하지 않습니다." >&2
  exit 1
}

echo "완료: $output_iso"
echo "SHA-256: $actual_output"
