"""Publish documentation only after the final 13-movie ISO checks pass."""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'build/movie_subtitles_v1'
OUT = ROOT / 'extracted_movies/korean_reviewed_v1'
report = json.loads((ROOT / 'reports/movie_subtitles_v1.json').read_text())
assert report['whole_iso_verification']['passed']
assert report['whole_iso_verification']['all_unplanned_bytes_identical']
assert len(report['changed_movies']) == 13 and report['cue_count'] == 149
assert report['song_lyrics_applied'] and report['original_audio_preserved']
iso = report['iso_path']
digest = report['iso']['output_sha256']
assert (ROOT / iso).is_file()

readme = f'''# 영상 자막 통합 ISO v1 — 2026-09-20

실행 파일: `{Path(iso).name}`

- 대사 검수 v4에 원본 MOVIE 한글 자막 추가. 기존 대사·시스템·사용자 이미지·레터링 유지.
- 대화/내레이션 8편 67개 + 엔딩/스태프롤 주제가 5편 82개 = 13편 149개 자막.
- 입력은 원본 IPU. 기존 추출 MP4를 입력으로 쓰지 않았다. 모든 AG 음성 바이트 동일.
- s01/s15 음악 영상은 원본 그대로. 스태프롤은 크레딧과 가사가 겹치지 않도록 비율을 유지한 576×432 화면과 하단 가사 공간으로 구성.
- 원본 출력 해상도·프레임 수·순서 유지. 재인코딩 구간에는 압축 손실이 있다.

## 실행

이전 상태저장 대신 새 ISO로 부팅한 뒤 게임 내 메모리카드에서 불러오는 것을 권장한다. 기존 대화 표시용 CRC7502FF83 패치가 계속 필요하다. 이미 같은 패치를 설치했다면 그대로 사용한다. 다른 PC에서는 동봉 `PCSX2_대화표시_호환패키지.zip`의 README에 따라 패치를 설치한다. ISO 옆 sidecar 폴더만 둔다고 PCSX2에 자동 설치되지는 않는다.

사용자의 카드·상태저장·PCSX2 설정은 변경하지 않았다.

## 검증 범위와 남은 확인

변경된 13개 IPU의 디코드 프레임 수, 사용된 변환 프레임의 MPEG-2↔IPU 픽셀 일치, 원본 음성, 변경 멤버 재읽기 및 전체 ISO 계획 범위 밖 동일 검사를 통과했다. 실제 PCSX2에서 영상 전체를 재생하는 검증은 아직 하지 않았다.

번역은 확정 자막과 자동 인식 대조를 바탕으로 했다. s09 주문의 수식어와 주제가 1절의 불명확한 술어는 생략했고, 스태프롤 약 172~178초 가사는 잠정 번역이다. 문맥으로 보정한 가사 표기도 있다. 공식 가사집과 대조한 완전 확정본은 아니다. 자세한 내용은 자막 폴더의 `청취_확인필요.json`과 README 참고.

## 편집 자료

`../../extracted_movies/korean_reviewed_v1/`에 한글 SRT/ASS, 원문 대조 SRT, 대조표, 판독 한계 기록을 보관했다. `검수자막_편집자료.zip`에도 포함했다. 적용 입력은 `../../localization/movie_subtitles_v1.json`이며 SRT만 바꾸면 자동 반영되지는 않는다.

SHA-256: `{digest}`
검증 기록: `../../reports/movie_subtitles_v1.json`
'''
(B / '먼저읽기.md').write_text(readme)
with zipfile.ZipFile(B / '검수자막_편집자료.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):
        if p.is_file():
            z.write(p, p.name)

pipeline = ROOT / 'localization/pipeline.json'
p = json.loads(pipeline.read_text())
p['latest_experimental_build'] = dict(path=iso, sha256=digest, pcsx2_sidecar=iso+'.pcsx2', report='reports/movie_subtitles_v1.json', runtime_verified=False)
p['static_checks']['movie_subtitles_v1_entire_iso_verified'] = True
p['movie_subtitles'] = dict(source='extracted/original/raw/MOVIE', authoring='localization/movie_subtitles_v1.json', editable='extracted_movies/korean_reviewed_v1', movies=13, cues=149, original_audio_preserved=True, song_lyrics_applied=True, song_lyrics_fully_confirmed=False, uncertainties='extracted_movies/korean_reviewed_v1/청취_확인필요.json', runtime_verified=False)
pipeline.write_text(json.dumps(p, ensure_ascii=False, indent=2)+'\n')

handover = ROOT / 'HANDOVER.md'
s = handover.read_text()
heading = '## 최신 실행 ISO: 원본 영상 자막 v1 (2026-09-20)'
assert heading not in s
s = s.replace('## 최신 실행 ISO: 대사 검수 v4', '## 이전 기반 ISO: 대사 검수 v4', 1)
section = f'''{heading}

`{iso}`
SHA-256: `{digest}`.

대사 검수 v4를 기반으로 원본 IPU 13편에 자막149개(대화8편/67개, 주제가5편/82개) 반영. 기존 MP4 재사용 없음. 원본 AG15개 바이트 보존, s01/s15 원본 영상 보존. 기존 사용자 이미지·레터링·시스템·텍스트·ELF는 MOVIE 범위 밖 전체 동일 검사로 유지 확인.

- 입력/자료: `localization/movie_subtitles_v1.json`, `extracted_movies/korean_reviewed_v1/`. 기존 SRT 보존. 자동 인식 원자료는 `asr_unreviewed/`이며 적용본 아님.
- 빌드 순서: `tools/author_movie_subtitles.py` → `tools/export_movie_subtitles.py` → `tools/export_movie_review_notes.py` → `tools/build_movie_subtitle_assets.py` → `tools/build_movie_subtitle_iso.py` → `tools/finalize_movie_subtitles.py`. author 도구에 번역을 보관하므로 JSON을 직접 수정한 뒤 author를 재실행하면 덮어쓰는 점 유의.
- IPU 출력 해상도·프레임 수·플래그 유지, 사용 프레임의 MPEG-2/IPU 왕복 픽셀 일치 검사. 원본 프레임 보존(s04 기존자막 영역, s14 크레딧 배치 제외), 모든 멤버 재읽기, 전체 ISO 계획 범위 밖 동일 통과.
- s04 원래 일본어 자막 영역을 한글로 대체. s10~s13 그림 아래 빈 공간에 가사. s14는 크레딧 보존을 위해 전체 영상을 같은 비율의576×432로 축소하여640×480 안에 배치, 하단48픽셀 가사 공간, 전체 프레임 재압축. 재압축 손실 있음.
- **가사 완전 확정본 아님:** s09 주문 수식어/주제가1절 술어 일부 생략, s14 약172~178초 잠정 번역 및 문맥 보정 구절 존재. `청취_확인필요.json` 필수 참조. 공식 가사집과 전곡 청취 확정 미실시.
- 검증: `reports/movie_subtitles_v1.json`, `build/movie_subtitles_v1/asset_report.json`. CRC7502FF83/34곳 호환 패치 sidecar/ZIP 동봉. 실제 PCSX2 영상 재생 검증 미실시. 사용자 설정·카드·상태저장 무변경.

'''
s = s.replace('\n\n', '\n\n'+section, 1)
handover.write_text(s)
print('Published', iso, digest)
