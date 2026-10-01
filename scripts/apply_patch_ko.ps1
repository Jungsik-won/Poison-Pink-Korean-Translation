param(
    [Parameter(Mandatory = $true)][string]$SourceIso,
    [string]$OutputIso = "Poison Pink (Japan) - Korean update v4.iso",
    [string]$PatchFile = "Poison_Pink_Korean_update_v4.xdelta"
)

$ErrorActionPreference = "Stop"
$SourceSha256 = "081e5c921fc2b0f517f007dfe053935578174a6880949de961e273426b216103"
$PatchSha256 = "dfb1389c87fffcfd4350253cf30bf2d3e1f6c8121aab6be3c689bcfc52782267"
$OutputSha256 = "b6601a8b7a6a5c6de956a9ccaa33804a304429e29cfa94bbe9e7d7f59a017445"

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
