#!/usr/bin/env python3
"""Import user-authored title PNGs without changing TIM2 palettes or ISO layout."""
import argparse
import json
import numpy as np
from PIL import Image
from localization_pipeline import ROOT, file_hash, sha, hed_tree, write_json
from iso_archive_stage import iso_inventory, exact, overlay
from ui_slice import verify_overlay
from ui_texture_codec import parse, serialize, preview_rgba


def prefer_opaque_palette_entries(indices, target, raw_palette):
    """Keep distinct stored alpha values when preview conversion clips them.

    For fully opaque authored pixels only, resolve equal preview RGBA entries
    to the highest stored alpha. The title's original solid white uses 255;
    choosing the first matching white instead selects stored alpha 140.
    Partial-alpha input and entries with different preview colors stay intact.
    """
    raw = np.asarray([list(c) for c in raw_palette], dtype=np.int32)
    preview = raw.copy()
    preview[:, 3] = np.minimum(raw[:, 3] * 2, 255)
    canonical = np.arange(len(raw), dtype=np.uint8)
    for i, color in enumerate(preview):
        matches = np.flatnonzero(np.all(preview == color, axis=1))
        best = matches[np.argmax(raw[matches, 3])]
        if raw[best, 3] > raw[i, 3]:
            canonical[i] = best
    result = indices.copy()
    opaque = target[:, 3] == 255
    result[opaque] = canonical[result[opaque]]
    return result


def compile_png(raw, path):
    model = parse(raw)
    if model['bpp'] != 8:
        raise ValueError('Expected 8-bit indexed title texture')
    with Image.open(path) as im:
        if im.size != (model['width'], model['height']) or 'A' not in im.getbands():
            raise ValueError('PNG must retain original dimensions and alpha channel')
        target = np.asarray(im.convert('RGBA'), dtype=np.int32).reshape(-1, 4)
    original = np.frombuffer(preview_rgba(model), dtype=np.uint8).reshape(-1, 4)
    palette = np.array([list(c[:3]) + [min(255, c[3]*2)] for c in model['palette']], dtype=np.int32)
    def premultiply(v):
        v = v.copy()
        v[:, :3] = (v[:, :3] * v[:, 3:4] + 127) // 255
        return v
    pal = premultiply(palette)
    values = premultiply(target)
    # Preserve duplicate palette indices where displayed input pixels are unchanged.
    positions = np.flatnonzero(np.any(values != premultiply(original.astype(np.int32)), axis=1))
    indices = np.frombuffer(model['indices'], dtype=np.uint8).copy()
    for start in range(0, len(positions), 1024):
        selected = positions[start:start+1024]
        distances = ((values[selected, None, :] - pal[None, :, :])**2).sum(axis=2)
        indices[selected] = distances.argmin(axis=1)
    corrected = prefer_opaque_palette_entries(indices, target, model['palette'])
    alpha_ties_fixed = int(np.count_nonzero(corrected != indices))
    indices = corrected
    model['indices'] = indices.tobytes()
    result = serialize(model)
    if result[:64] != raw[:64] or result[64+len(indices):] != raw[64+len(indices):]:
        raise ValueError('Header or palette changed')
    if len(result) != len(raw) or serialize(parse(result)) != result or result == raw:
        raise ValueError('Invalid or empty texture replacement')
    errors = pal[indices] - values
    return result, dict(width=model['width'], height=model['height'],
        input_edited_pixels=len(positions), changed_index_bytes=sum(a != b for a, b in zip(raw, result)),
        premultiplied_rgba_rmse=float(np.sqrt(np.mean(errors.astype(np.float64)**2))),
        maximum_alpha_error=int(np.abs(palette[indices, 3]-target[:, 3]).max()),
        opaque_raw_alpha_ties_corrected=alpha_ties_fixed,
        alpha_error_metric='clipped preview only; not a runtime opacity guarantee',
        original_header_and_palette_preserved=True, byte_exact_tim2_roundtrip=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='localization/title_artwork.json')
    args = parser.parse_args()
    config_path = ROOT / args.config
    config = json.loads(config_path.read_text())
    source = ROOT / config['base_iso']
    output = (ROOT / config['output_iso']).resolve()
    if (ROOT/'build').resolve() not in output.parents or output.exists():
        raise ValueError('Output must be a new ISO below build/')
    if file_hash(source) != config['base_iso_sha256']:
        raise ValueError('Base ISO changed')
    inv = iso_inventory(source)
    entries = {e['path']: e for e in inv['files']}
    patches, checks = [], []
    output.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as fp:
        h = entries['DATA/DMAP.HED']; d = entries['DATA/DMAP.DAT']
        fp.seek(h['lba']*2048)
        members = {e['path']: e for e in hed_tree(exact(fp, h['size']))[0]}
        for row in config['assets']:
            authored = ROOT / row['png']
            if file_hash(authored) != row['png_sha256']:
                raise ValueError('Authored PNG changed')
            e = members[row['path']]; offset = d['lba']*2048 + e['offset']
            fp.seek(offset); raw = exact(fp, e['size'])
            if sha(raw) != row['original_tim2_sha256']:
                raise ValueError('Title texture differs from pinned original')
            result, check = compile_png(raw, authored)
            name = row['path'].split('/')[-1]
            (output.parent/name).write_bytes(result)
            model = parse(result)
            Image.frombytes('RGBA', (model['width'], model['height']), preview_rgba(model)).save(output.parent/(name+'.png'))
            patches.append(dict(offset=offset, data=result, expected_sha256=sha(raw)))
            checks.append(dict(path=row['path'], png=row['png'], png_sha256=row['png_sha256'],
                iso_offset=offset, before_sha256=sha(raw), after_sha256=sha(result), **check))
    iso = overlay(source, output, patches, config['base_iso_sha256'])
    if iso_inventory(output) != inv:
        raise ValueError('ISO layout changed')
    verification = verify_overlay(source, output, patches, config['base_iso_sha256'], iso['output_sha256'])
    report = dict(base_iso=config['base_iso'], base_iso_sha256=config['base_iso_sha256'],
        iso_path=str(output.relative_to(ROOT)), iso=iso, assets=checks, entire_iso_diff=verification,
        config_sha256=file_hash(config_path), tool_sha256=file_hash(ROOT/'tools/title_artwork.py'),
        iso_layout_preserved=True, all_other_bytes_preserved=True, visual_review=False, runtime_verified=False)
    write_json(output.parent/'manifest.json', report)
    write_json(ROOT/'reports/title_artwork.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
