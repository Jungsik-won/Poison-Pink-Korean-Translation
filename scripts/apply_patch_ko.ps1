param(
    [Parameter(Mandatory = $true)][string]$SourceIso,
    [string]$OutputIso = "Poison Pink (Japan) - Korean DMAP flow v1.iso",
    [string]$PatchFile = "Poison_Pink_Korean_DMAP_flow_v1.xdelta"
)

$ErrorActionPreference = "Stop"
$SourceSha256 = "081e5c921fc2b0f517f007dfe053935578174a6880949de961e273426b216103"
$PatchSha256 = "8e56374561879106237e04ca3aa4875462bf0743aeac917c0987749bc5fe2a55"
$OutputSha256 = "b1ebb5db3d0613ea9fe1160f6636c7481fb4d71c43e6b2d9b67f366ea9ca06b2"

if (-not (Get-Command xdelta3 -ErrorAction SilentlyContinue)) {
    throw "xdelta3를 먼저 설치해 주세요."
}
if (-not (Test-Path -LiteralPath $SourceIso -PathType Leaf)) {
    throw "원본 ISO를 찾을 수 없습니다: $SourceIso"
}
if (-not (Test-Path -LiteralPath $PatchFile -PathType Leaf)) {
    throw "패치를 찾을 수 없습니다: $PatchFile"
}
if (Test-Path -LiteralPath $OutputIso) {
    throw "출력 파일이 이미 있습니다: $OutputIso"
}

$ActualSource = (Get-FileHash -LiteralPath $SourceIso -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualSource -ne $SourceSha256) {
    throw "지원하는 일본판 원본 ISO가 아닙니다. 실제 SHA-256: $ActualSource"
}

$ActualPatch = (Get-FileHash -LiteralPath $PatchFile -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualPatch -ne $PatchSha256) {
    throw "패치 파일의 SHA-256이 일치하지 않습니다."
}

& xdelta3 -d -s $SourceIso $PatchFile $OutputIso
if ($LASTEXITCODE -ne 0) {
    throw "xdelta3 적용에 실패했습니다."
}

$ActualOutput = (Get-FileHash -LiteralPath $OutputIso -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualOutput -ne $OutputSha256) {
    throw "생성된 ISO의 SHA-256이 일치하지 않습니다. 실제값: $ActualOutput"
}

Write-Host "완료: $OutputIso"
Write-Host "SHA-256: $ActualOutput"

