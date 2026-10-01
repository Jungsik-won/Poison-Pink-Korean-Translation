"""Pack generated Korean title masks; preserve English atlas indices verbatim."""
import argparse
import json
import sys
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from ui_texture_codec import parse, serialize, unpack_indices, preview_rgba, uad_rectangles
from localization_pipeline import sha, file_hash, hed_tree, write_json
from iso_archive_stage import iso_inventory, exact, overlay
import build_user_translation_import as verifier

OUT = ROOT / 'outputs/dmap_flow_ko_v1'
BUILD = ROOT / 'build/dmap_flow_ko_v1'
BASE = ROOT / 'build/dmap_map_ko_v1/Poison Pink (Japan) - Korean DMAP maps v1.iso'
BASE_SHA = '481a8ea8e042b0dd3385bb5ed56aa3b3d8e41dad222fef053c81c751854f1f3e'
ISO = BUILD / 'Poison Pink (Japan) - Korean DMAP flow v1.iso'
RAW = ROOT / 'extracted/original/raw/DMAP/dmap/flow'


def prepare():
    rows = json.loads((OUT / 'manifest.json').read_text())
    assets, missing = [], []
    for row in rows:
        glyph = OUT / 'final_glyphs' / (row['id'] + '.png')
        if not glyph.exists():
            missing.append(row['id'])
            continue
        alpha = Image.open(glyph).convert('RGBA').getchannel('A')
        assert alpha.getextrema() == (0, 255), 'Expected transparent glyph mask'
        bounds = alpha.point(lambda v: 255 if v > 20 else 0).getbbox()
        assert bounds
        for name in [row['id']] + row['duplicates']:
            raw_path = RAW / (name + '.tm2')
            raw = raw_path.read_bytes()
            model = parse(raw)
            assert (model['width'], model['height'], model['bpp']) == (256, 128, 8)
            old = unpack_indices(model)
            uad = raw_path.with_suffix('.uad')
            assert [r['rect'] for r in uad_rectangles(uad.read_bytes(), 256, 128)['rectangles']] == [
                [0, 0, 256, 40], [0, 40, 256, 32], [0, 72, 256, 32]]
            original = Image.frombytes('RGBA', (256, 128), preview_rgba(model))
            box = original.crop((0, 0, 256, 40)).getchannel('A').getbbox()
            # The game atlas defines title position, ink width/height, and palette.
            # Only the AI-authored glyph alpha enters the first 40 scanlines.
            native_alpha = Image.new('L', (256, 40))
            native_alpha.paste(alpha.crop(bounds).resize((box[2]-box[0], box[3]-box[1]),
                Image.Resampling.LANCZOS), box[:2])
            candidates = [i for i,c in enumerate(model['palette']) if c[3] == 0 or c[:3] == bytes((255,255,255))]
            lut = [min(candidates, key=lambda i: abs(min(model['palette'][i][3]*2,255)-v)) for v in range(256)]
            model['indices'] = bytes(lut[v] for v in native_alpha.tobytes()) + old[256*40:]
            data = serialize(model)
            encoded = parse(data)
            assert len(data) == len(raw) and serialize(encoded) == data
            assert encoded['header'] == parse(raw)['header'] and encoded['palette'] == parse(raw)['palette']
            assert unpack_indices(encoded)[256*40:] == old[256*40:]
            preview = Image.frombytes('RGBA', (256,128), preview_rgba(encoded))
            assert preview.crop((0,40,256,128)).tobytes() == original.crop((0,40,256,128)).tobytes()
            actual_box = preview.crop((0,0,256,40)).getchannel('A').getbbox()
            assert actual_box == box, (name, box, actual_box)
            dest = BUILD / 'textures' / (name + '.tm2')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            png = OUT / 'native' / (name + '.tm2.png')
            png.parent.mkdir(parents=True, exist_ok=True)
            preview.save(png)
            assets.append(dict(member='dmap/flow/'+name+'.tm2', target=row['target'],
                replacement=str(dest.relative_to(ROOT)), sha256=sha(data),
                original_sha256=sha(raw), uad_sha256=file_hash(uad),
                glyph=str(glyph.relative_to(ROOT)), glyph_sha256=file_hash(glyph),
                ink_bbox=list(box), english_indices_identical=True, native_size=[256,128],
                palette_header_size_preserved=True, alpha_preserved=True))
    write_json(BUILD/'assets.json', dict(assets=assets,missing=missing))
    sheet = Image.new('RGB',(768,580),'#20252b')
    draw = ImageDraw.Draw(sheet)
    for j,r in enumerate(rows):
        p = OUT/'native'/(r['id']+'.tm2.png')
        if p.exists():
            art = Image.open(p).convert('RGBA')
            sheet.paste(art,(j%3*256,j//3*190),art)
            draw.text((j%3*256+6,j//3*190+140),r['id'],fill='white')
    (OUT/'review').mkdir(exist_ok=True)
    sheet.save(OUT/'review/native_all.png')
    print(json.dumps(dict(prepared=len(assets),missing=missing)),flush=True)


def build():
    prepared = json.loads((BUILD/'assets.json').read_text())
    assert not prepared['missing'] and len(prepared['assets']) == 11
    review = json.loads((OUT/'visual_review.json').read_text())
    assert review['native_review_complete']
    inventory = iso_inventory(BASE)
    files = {r['path']:r for r in inventory['files']}
    patches = []
    with BASE.open('rb') as f:
        he,de = files['DATA/DMAP.HED'],files['DATA/DMAP.DAT']
        f.seek(he['lba']*2048)
        members = {r['path']:r for r in hed_tree(exact(f,he['size']))[0]}
        for asset in prepared['assets']:
            assert review['glyph_sha256'][Path(asset['glyph']).stem] == file_hash(ROOT/asset['glyph']) == asset['glyph_sha256']
            r = members[asset['member']]
            pos = de['lba']*2048+r['offset']
            f.seek(pos)
            old = exact(f,r['size'])
            data = (ROOT/asset['replacement']).read_bytes()
            assert sha(old) == asset['original_sha256'] and sha(data) == asset['sha256'] and len(data) == len(old)
            patches.append(dict(offset=pos,data=data,expected_sha256=sha(old)))
    print('Building and verifying ISO',flush=True)
    result = overlay(BASE,ISO,patches,BASE_SHA)
    assert iso_inventory(ISO) == inventory
    verifier.BASE_HASH = BASE_SHA
    checked = verifier.verify_stream(BASE,ISO,patches,result['output_sha256'])
    assert checked['passed'] and checked['all_unplanned_bytes_identical']
    with ISO.open('rb') as f:
        for patch in patches:
            f.seek(patch['offset'])
            assert exact(f,len(patch['data'])) == patch['data']
    assert result['runtime_compatibility']['elf_crc'] == '565FA10D'
    side = Path(str(ISO)+'.pcsx2')
    assert json.loads((side/'manifest.json').read_text())['iso_sha256'] == result['output_sha256']
    package = BUILD/'PCSX2_대화표시_호환패키지.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(side.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(side))
    with zipfile.ZipFile(package) as z: assert z.testzip() is None
    report = dict(status='applied_to_iso',date='2026-10-01',iso_path=str(ISO.relative_to(ROOT)),
        base_iso=str(BASE.relative_to(ROOT)),iso=result,verification=checked,
        assets=prepared['assets'],newly_localized_images=11,unique_titles=8,
        english_pixels_indices_unchanged=True,uad_unchanged=True,
        previous_map_class_shop_controller_changes_preserved=True,
        image_generation_mode='built-in image_gen alpha glyphs, native palette packing',
        runtime_verified=False)
    write_json(BUILD/'report.json',report)
    write_json(ROOT/'reports/dmap_flow_ko_v1.json',report)
    (BUILD/'SHA256SUMS.txt').write_text(result['output_sha256']+'  '+ISO.name+'\n')
    (BUILD/'먼저읽기.txt').write_text('DMAP 지역명 한글화 추가 v1\n기반: Korean DMAP maps v1. 기존 지도 75장 및 클래스·상점·컨트롤러 수정 유지.\nbf_nm_a~j 및 s 11장: 일본어 지역명을 한국어로 교체. 영어 픽셀·팔레트·UAD·원본 제목 폭과 높이 유지.\n실행 파일은 이전 DMAP maps v1과 같아 CRC 565FA10D 유지. 동봉한 PCSX2 대화표시 호환 패치를 사용하세요.\n전체 ISO 비교 검증 통과. 실제 게임 실행은 미검증.\n')
    cfg_path = ROOT/'localization/pipeline.json'
    cfg = json.loads(cfg_path.read_text())
    cfg['latest_experimental_build'] = dict(path=report['iso_path'],sha256=result['output_sha256'],
        pcsx2_sidecar=report['iso_path']+'.pcsx2',report='reports/dmap_flow_ko_v1.json',runtime_verified=False)
    cfg['static_checks']['dmap_flow_ko_v1_entire_iso_verified'] = True
    write_json(cfg_path,cfg)
    hp = ROOT/'HANDOVER.md'
    text = hp.read_text().replace('## 최신 실행 ISO: DMAP 지도 이미지 한글화 v1','## 이전 기반 ISO: DMAP 지도 이미지 한글화 v1',1)
    section = ('## 최신 실행 ISO: DMAP 지역명 한글화 추가 v1 (2026-10-01)\n\n`'+report['iso_path']+'`\n\n'
        +'SHA-256: `'+result['output_sha256']+'`. DMAP maps v1에 flow/bf_nm_a~j,s 11장 추가. '
        +'기존 지도 이미지 75장과 클래스·상점·컨트롤러 수정 보존. 일본어 제목만 기존 용어로 한국어화; 영어 영역의 원본 인덱스·픽셀 및 UAD 보존. '
        +'원본 제목 잉크 영역의 폭·높이·위치 유지, 한국어 자간은 시각 검수. 전체 ISO 계획 밖 바이트 동일 검증. '
        +'ELF CRC 565FA10D 유지, 해당 호환 ZIP 동봉. 실제 게임 실행 미검증.\n\n'
        +'보고서: reports/dmap_flow_ko_v1.json. 원본 생성 결과·프롬프트·게임용 미리보기: outputs/dmap_flow_ko_v1. '
        +'빌더: tools/build_dmap_flow_ko_v1.py.\n\n')
    hp.write_text(text.replace('\n\n','\n\n'+section,1))
    print(json.dumps(dict(iso=str(ISO),sha256=result['output_sha256'],verified=checked),ensure_ascii=False),flush=True)


if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--build',action='store_true');args=ap.parse_args()
    BUILD.mkdir(parents=True,exist_ok=True)
    build() if args.build else prepare()
