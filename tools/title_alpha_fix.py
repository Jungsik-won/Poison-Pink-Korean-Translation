#!/usr/bin/env python3
"""Repair opaque title palette selection over the completed PSD build."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from localization_pipeline import ROOT, file_hash, sha, hed_tree, write_json
from iso_archive_stage import iso_inventory, exact, overlay
from ui_texture_codec import parse, preview_rgba
from title_artwork import compile_png
import build_user_translation_import as verifier

BASE = ROOT/'build/title_psd_v1/Poison Pink (Japan) - Korean system and title v2.iso'
BASE_SHA = '28045de9491f9cbf9f7819b539c6381d0e7525086c67335f74b128e1e562fb94'
PNG = ROOT/'localization/artwork/title_user_psd_v1/tit_tx01.png'
PNG_SHA = 'd771d8b8706eca7bc350b75bc3ab21f3683248fee421122c0b793f104c93d493'
OUT = ROOT/'build/title_alpha_v1'


def main():
    output = OUT/'Poison Pink (Japan) - Korean title alpha fix.iso'
    assert not output.exists() and file_hash(PNG) == PNG_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    inv = iso_inventory(BASE)
    entries = {e['path']: e for e in inv['files']}
    with BASE.open('rb') as f:
        h = entries['DATA/DMAP.HED']; d = entries['DATA/DMAP.DAT']
        f.seek(h['lba']*2048)
        member = next(e for e in hed_tree(exact(f,h['size']))[0] if e['path']=='dmap/title/tit_tx01.tm2')
        offset = d['lba']*2048+member['offset']
        f.seek(offset); old = exact(f,member['size'])
    new, conversion = compile_png(old, PNG)
    before, after = parse(old), parse(new)
    a = np.array(Image.open(PNG).convert('RGBA')).reshape(-1,4)
    old_indices = np.frombuffer(before['indices'],dtype=np.uint8)
    new_indices = np.frombuffer(after['indices'],dtype=np.uint8)
    palette = np.array([list(c) for c in after['palette']],dtype=np.int32)
    changed = old_indices != new_indices
    white = np.all(a == 255,axis=1)
    assert np.all(a[changed,3] == 255)
    assert np.all(palette[new_indices[white]] == 255)
    assert np.all(palette[new_indices[changed],:3] == palette[old_indices[changed],:3])
    assert np.all(palette[new_indices[changed],3] > palette[old_indices[changed],3])
    assert preview_rgba(before) == preview_rgba(after), 'Only clipped-alpha equivalents may change'
    assert before['palette'] == after['palette'] and before['header'] == after['header']
    counts = lambda x: {str(int(k)):int(v) for k,v in zip(*np.unique(x,return_counts=True))}
    check = dict(opaque_white_pixels=int(white.sum()),
        white_stored_alpha_before=counts(palette[old_indices[white],3]),
        white_stored_alpha_after=counts(palette[new_indices[white],3]),
        changed_indices=int(changed.sum()),partial_alpha_input_indices_unchanged=True,
        palette_and_header_unchanged=True,all_changed_rgb_unchanged=True,
        preview_clipping_hides_the_bug=True)
    (OUT/'tit_tx01.tm2').write_bytes(new)
    patches = [dict(offset=offset,data=new,expected_sha256=sha(old))]
    iso = overlay(BASE,output,patches,BASE_SHA)
    assert iso_inventory(output) == inv
    verifier.BASE_HASH = BASE_SHA
    diff = verifier.verify_stream(BASE,output,patches,iso['output_sha256'])
    with output.open('rb') as f:
        f.seek(offset); assert exact(f,len(new)) == new
    report = dict(base_iso=str(BASE.relative_to(ROOT)),base_iso_sha256=BASE_SHA,
        iso_path=str(output.relative_to(ROOT)),iso=iso,png=str(PNG.relative_to(ROOT)),png_sha256=PNG_SHA,
        asset='dmap/title/tit_tx01.tm2',iso_offset=offset,before_tim2_sha256=sha(old),after_tim2_sha256=sha(new),
        checks=check,conversion=conversion,entire_iso_diff=diff,
        all_other_assets_and_text_preserved=True,runtime_verified=False,
        limitation='Clipped preview is not evidence of runtime opacity; game draw-time effects remain unverified.',
        tool_sha256=file_hash(Path(__file__)),compiler_sha256=file_hash(ROOT/'tools/title_artwork.py'))
    write_json(OUT/'manifest.json',report)
    write_json(ROOT/'reports/title_alpha_v1.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__ == '__main__':
    main()
