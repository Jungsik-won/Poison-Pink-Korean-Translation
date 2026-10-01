#!/usr/bin/env python3
"""Decode paired 2bpp glyphs and build a font-only Korean display probe.

The three Korean glyphs are simple original diagnostic strokes, not a release font.
No RTB, table, language config, ELF, or file sizes are changed.
"""
import argparse
import hashlib
import json
import struct

from localization_pipeline import ROOT, hed_tree, sha, write_json
from iso_archive_stage import SOURCE, ISO, CHUNK, exact, source_sha, stage_archive, stage_iso, iso_inventory
from tim2_to_png import write_png


def japanese_index(code):
    lead, trail = code >> 8, code & 255
    if not (0x81 <= lead <= 0x9f or 0xe0 <= lead <= 0xfc) or not (0x40 <= trail <= 0xfc and trail != 0x7f):
        raise ValueError('Invalid two-byte Shift-JIS code')
    linear = lead * 189 + trail
    return linear - (24445 if code <= 0x84fc else 24823 if code <= 0x9ffc else 36919)


def decode_glyph(font, glyph_id):
    if glyph_id < 0 or (glyph_id // 2 + 1) * 288 > len(font):
        raise ValueError('Glyph ID outside font')
    offset, component = (glyph_id // 2) * 288, (glyph_id & 1) * 2
    return [((font[offset + y*12 + x//2] >> ((x & 1)*4 + component)) & 3)
            for y in range(24) for x in range(24)]


def encode_glyph(font, glyph_id, pixels):
    if len(pixels) != 576 or any(p not in (0, 1, 2, 3) for p in pixels):
        raise ValueError('Expected 24x24 2bpp pixels')
    decode_glyph(font, glyph_id)  # bounds check
    offset, component = (glyph_id // 2) * 288, (glyph_id & 1) * 2
    for y in range(24):
        for x in range(24):
            index, shift = offset + y*12 + x//2, (x & 1)*4 + component
            font[index] = (font[index] & ~(3 << shift)) | (pixels[y*24+x] << shift)


def diagnostic_hangul(char):
    pixels = [0] * 576
    def rect(x0, y0, x1, y1):
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                pixels[y*24+x] = 3
    # ㅏ, shared by 가 / 나 / 다.
    rect(17, 3, 19, 21)
    rect(20, 10, 23, 12)
    if char == '가':
        rect(2, 5, 12, 7); rect(10, 8, 12, 18)
    elif char == '나':
        rect(2, 5, 4, 18); rect(5, 16, 12, 18)
    elif char == '다':
        rect(2, 5, 12, 7); rect(2, 8, 4, 18); rect(5, 16, 12, 18)
    else:
        raise ValueError('Only diagnostic 가나다 is available')
    return pixels


def get_font():
    hed = SOURCE / 'DATA/SYSTEM.HED'
    dat = hed.with_suffix('.DAT')
    if sha(hed.read_bytes()) != source_sha(hed):
        raise ValueError('SYSTEM.HED changed')
    files, _ = hed_tree(hed.read_bytes())
    with dat.open('rb') as fp:
        def read(path):
            entry = next(e for e in files if e['path'] == path)
            fp.seek(entry['offset'])
            return exact(fp, entry['size'])
        font = read('system/kanji.dat')
        table_raw = read('system/kantable.dat')
    return font, struct.unpack('<{}h'.format(len(table_raw)//2), table_raw)


def preview(original, modified, ids, output):
    # Two rows, original then modified. Pure diagnostic rendering, no external font.
    scale, gap = 4, 12
    width, height = len(ids)*(24*scale+gap)+gap, 2*(24*scale+gap)+gap
    rgba = bytearray([245, 245, 245, 255] * width * height)
    for row, font in enumerate((original, modified)):
        for col, gid in enumerate(ids):
            pixels = decode_glyph(font, gid)
            for y in range(24*scale):
                for x in range(24*scale):
                    v = 255 - pixels[(y//scale)*24+x//scale] * 85
                    px, py = gap+col*(24*scale+gap)+x, gap+row*(24*scale+gap)+y
                    p = (py*width+px)*4
                    rgba[p:p+4] = bytes((v, v, v, 255))
    output.write_bytes(write_png(width, height, bytes(rgba)))


def build_probe(make_iso):
    original, table = get_font()
    font = bytearray(original)
    for gid in range(len(original)//144):
        encode_glyph(font, gid, decode_glyph(original, gid))
    if bytes(font) != original:
        raise ValueError('All-glyph byte roundtrip failed')
    mapping = []
    for source, target in zip('テージ', '가나다'):
        encoded = source.encode('cp932')
        index = japanese_index(int.from_bytes(encoded, 'big'))
        gid = table[index]
        encode_glyph(font, gid, diagnostic_hangul(target))
        mapping.append(dict(source_character=source, source_code_hex=encoded.hex(),
                            displayed_character=target, table_index=index, glyph_id=gid,
                            pair_offset=gid//2*288, component=gid & 1))
    changed_ids = {r['glyph_id'] for r in mapping}
    for gid in range(len(original)//144):
        if gid not in changed_ids and decode_glyph(original, gid) != decode_glyph(font, gid):
            raise ValueError('Untargeted glyph changed: ' + str(gid))
    out = ROOT / 'build/font_probe'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'kanji.dat').write_bytes(font)
    preview(original, font, [r['glyph_id'] for r in mapping], out / 'preview.png')
    preview(original, font, [gid for r in mapping for gid in (r['glyph_id'] & ~1, r['glyph_id'] | 1)], out / 'pair_neighbors.png')
    staged = stage_archive('SYSTEM', out / 'DATA', {'system/kanji.dat': bytes(font)})
    report = dict(experiment='font_only_global_slot_substitution', expected_display='テージ → 가나다',
                  warning='Every occurrence of テ, ー, ジ changes globally; this is not a translation patch.',
                  font_source='Original diagnostic rectangles; no third-party Korean font',
                  original_font_sha256=sha(original), patched_font_sha256=sha(font),
                  all_glyph_roundtrip=True, glyph_count=len(original)//144,
                  unchanged_glyphs_verified=len(original)//144-len(changed_ids),
                  mapping=mapping, stage=staged, runtime_verified=False,
                  original_layout='24 rows, 12 bytes per row per pair; nibble order low then high; even bits 0:1 / odd bits 2:3')
    if make_iso:
        iso_path = out / 'Poison Pink (Japan) - font-probe.iso'
        report['iso'] = stage_iso(iso_path, {'DATA/SYSTEM.DAT': out / 'DATA/SYSTEM.DAT'})
        report['iso_path'] = str(iso_path.relative_to(ROOT))
    write_json(ROOT / 'reports/font_probe.json', report)
    write_json(out / 'glyph_mapping.json', mapping)
    print('Font probe complete: 2016 glyph roundtrip, 2013 untouched glyphs verified', flush=True)


def verify_iso_probe():
    report_path = ROOT / 'reports/font_probe.json'
    report = json.loads(report_path.read_text())
    output = ROOT / report['iso_path']
    inventory = iso_inventory(ISO)
    if iso_inventory(output) != inventory or output.stat().st_size != ISO.stat().st_size:
        raise ValueError('Probe ISO layout/size differs')
    entry = next(e for e in inventory['files'] if e['path'] == 'DATA/SYSTEM.DAT')
    members, _ = hed_tree((SOURCE / 'DATA/SYSTEM.HED').read_bytes())
    member = next(e for e in members if e['path'] == 'system/kanji.dat')
    absolute_font_offset = entry['lba'] * 2048 + member['offset']
    original, table = get_font()
    expected = bytearray(original)
    for source, target in zip('テージ', '가나다'):
        index = japanese_index(int.from_bytes(source.encode('cp932'), 'big'))
        encode_glyph(expected, table[index], diagnostic_hangul(target))
    expected_changes = {absolute_font_offset+i: (a,b) for i,(a,b) in enumerate(zip(original,expected)) if a != b}
    total_changes = len(expected_changes)
    first, last = min(expected_changes), max(expected_changes)
    source_hash, output_hash = hashlib.sha256(), hashlib.sha256()
    offset = 0
    with ISO.open('rb') as a, output.open('rb') as b:
        while True:
            old = a.read(CHUNK)
            if not old:
                break
            new = exact(b, len(old))
            source_hash.update(old); output_hash.update(new)
            if old != new:
                for i,(x,y) in enumerate(zip(old,new)):
                    if x != y and expected_changes.pop(offset+i, None) != (x,y):
                        raise ValueError('Unexpected ISO change at {}'.format(hex(offset+i)))
            offset += len(old)
    if expected_changes or source_hash.hexdigest() != source_sha(ISO) or output_hash.hexdigest() != report['iso']['output_sha256']:
        raise ValueError('Missing expected changes or ISO hash mismatch')
    verification = dict(entire_iso_compared=True, exact_expected_changes_only=True,
                        changed_bytes=total_changes, first_changed_offset=hex(first), last_changed_offset=hex(last),
                        source_iso_sha256=source_hash.hexdigest(), output_iso_sha256=output_hash.hexdigest(),
                        runtime_verified=False)
    report['independent_iso_diff'] = verification
    write_json(report_path, report)
    print(json.dumps(verification, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--iso', action='store_true')
    group.add_argument('--verify-iso', action='store_true')
    args = parser.parse_args()
    if args.verify_iso:
        verify_iso_probe()
    else:
        build_probe(args.iso)
