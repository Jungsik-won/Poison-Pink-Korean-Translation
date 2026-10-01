"""Import four user-authored shop/dictionary assets without changing an ISO.

Only game-defined text sprite rectangles are replaced. The original palette,
headers, UAD files and indices outside those rectangles remain unchanged.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build/python_psd'))
import numpy as np
from PIL import Image, ImageDraw
from psd_tools import PSDImage
from ui_texture_codec import parse, serialize, preview_rgba, unpack_indices, uad_rectangles
from build_battle_conditions_psd import compile_texture
from localization_pipeline import sha, write_json

SOURCE = Path('/Users/j.swon/Desktop/무제 폴더')
OUT = ROOT / 'outputs/user_shop_dictionary_v1'
BUILD = ROOT / 'build/user_shop_dictionary_v1'
ASSETS = {
    'dic_pt04': ('dic_pt04.tm2.psd', [10, 11, 12, 14, 17, 18, 19, 20, 21, 28, 29]),
    'sys007': ('sys007.tm2.psd', [2]),
    'sys019': ('sys019.tm2.psd', [0, 2, 3, 4, 5, 6, 7, 8, 9]),
    'dic_pt02': ('dic_pt02_ko.png', [1]),
}


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    rows, pending, panels = [], [], []
    for name, (filename, slots) in ASSETS.items():
        src = SOURCE / filename
        source_bytes = src.read_bytes()
        copy = OUT / filename
        if copy.exists():
            assert copy.read_bytes() == source_bytes, 'User source changed: ' + filename
        else:
            shutil.copy2(src, copy)
        if filename.endswith('.psd'):
            psd = PSDImage.open(copy)
            art = psd.composite().convert('RGBA')
        else:
            art = Image.open(copy).convert('RGBA')
        rawpath = ROOT / 'extracted/original/raw/STATUS/status' / (name + '.tm2')
        raw, uad = rawpath.read_bytes(), rawpath.with_suffix('.uad').read_bytes()
        model = parse(raw)
        size = (model['width'], model['height'])
        assert art.size == size
        original = Image.frombytes('RGBA', size, preview_rgba(model))
        rects = uad_rectangles(uad, *size)['rectangles']
        mask = np.zeros((size[1], size[0]), bool)
        for slot in slots:
            x, y, w, h = rects[slot]['rect']
            mask[y:y+h, x:x+w] = True
        pixels = np.array(original)
        pixels[mask] = np.array(art)[mask]
        target = Image.fromarray(pixels)
        compiled, checks = compile_texture(raw, target)
        result = parse(compiled)
        old = np.frombuffer(unpack_indices(model), np.uint8).reshape(mask.shape)
        new = np.frombuffer(unpack_indices(result), np.uint8).reshape(mask.shape).copy()
        new[~mask] = old[~mask]
        palette = np.array([list(c) for c in result['palette']])
        solid = mask & (pixels[:, :, 3] == 255)
        bad = solid & (palette[new, 3] < 128)
        candidates = np.where(palette[:, 3] >= 128)[0]
        if bad.any():
            assert candidates.size
            distances = ((pixels[bad, :3].astype(float)[:, None, :]
                          - palette[candidates, :3][None, :, :]) ** 2).sum(2)
            new[bad] = candidates[distances.argmin(1)]
        flat = new.reshape(-1)
        result['indices'] = (flat.tobytes() if result['bpp'] == 8 else
                             (flat[::2] | (flat[1::2] << 4)).tobytes())
        compiled = serialize(result)
        reparsed = parse(compiled)
        assert len(compiled) == len(raw)
        assert reparsed['header'] == model['header']
        assert reparsed['palette'] == model['palette']
        assert np.array_equal(new[~mask], old[~mask])
        assert np.all(palette[new[solid], 3] >= 128)
        assert rawpath.read_bytes() == raw and rawpath.with_suffix('.uad').read_bytes() == uad
        assert src.read_bytes() == source_bytes
        dest = BUILD / 'textures/STATUS/status' / (name + '.tm2')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(compiled)
        preview = Image.frombytes('RGBA', size, preview_rgba(reparsed))
        art.save(OUT / (name + '_user_visible.png'))
        original.save(OUT / (name + '_original.png'))
        target.save(OUT / (name + '_ko.png'))
        preview.save(OUT / (name + '_game_preview.png'))
        panels.append((name, original, preview))
        rows.append(dict(name=name, user_source=str(src), source_sha256=sha(source_bytes),
                         original_texture_sha256=sha(raw), uad_sha256=sha(uad), size=list(size),
                         edit_slots=slots, edit_rectangles_xywh=[rects[i]['rect'] for i in slots],
                         header_palette_size_preserved=True, outside_indices_exact=True,
                         opaque_ink_checked=True, user_source_unchanged=True,
                         original_texture_and_uad_unchanged=True,
                         changed_bytes=sum(a != b for a, b in zip(raw, compiled)),
                         compiler_initial_checks=checks))
        pending.append(dict(archive='STATUS', member='status/' + name + '.tm2',
                            replacement=str(dest.relative_to(ROOT)), sha256=sha(compiled),
                            expected_original_sha256=sha(raw)))
    board = Image.new('RGB', (1040, sum(p[1].height * 2 + 32 for p in panels)), (38, 42, 46))
    draw, y = ImageDraw.Draw(board), 0
    for name, original, preview in panels:
        draw.text((8, y+8), name + ' - original', fill='white')
        draw.text((528, y+8), name + ' - game texture', fill='white')
        y += 32
        for x, im in [(8, original), (528, preview)]:
            scaled = im.resize((im.width*2, im.height*2), Image.Resampling.NEAREST)
            board.paste(scaled, (x, y), scaled)
        y += original.height * 2
    board.save(OUT / 'comparison.png')
    report = dict(status='prepared_not_applied_to_iso', iso_built=False, runtime_verified=False,
                  date='2026-10-01', artwork='user-authored PSD composite and PNG; no relettering',
                  supersedes_rejected_assets_from='reports/shop_dictionary_ko_v1.json',
                  excluded_asset='dic_pt03: no new user artwork supplied', assets=rows,
                  pending_assets=pending, preview='outputs/user_shop_dictionary_v1/comparison.png')
    write_json(BUILD / 'report.json', report)
    write_json(ROOT / 'reports/user_shop_dictionary_v1.json', report)
    (OUT / 'README_KO.txt').write_text(
        '사용자 PSD 3장(dic_pt04/sys007/sys019), PNG 1장(dic_pt02) 반영 대기.\n'
        '글꼴·문구·크기·간격을 다시 식자하지 않고 가시 합성을 원본 크기로 변환했습니다.\n'
        '게임 정의 글자 영역 밖 인덱스, 팔레트, 헤더, 원본 UAD와 사용자 원본 보존 검사 통과.\n'
        '다음 ISO 통합에서 reports/user_shop_dictionary_v1.json pending_assets 4개를 사용합니다.\n'
        '거절된 자동 식자본과 dic_pt03은 포함하지 않습니다. ISO 및 실제 실행 검증은 아직 하지 않았습니다.\n',
        encoding='utf-8')
    print(json.dumps(dict(prepared=len(pending), iso_built=False, report='reports/user_shop_dictionary_v1.json')))


if __name__ == '__main__':
    prepare()
