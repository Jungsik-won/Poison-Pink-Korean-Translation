#!/usr/bin/env python3
"""Integrate reviewed portrait layout constants over the latest complete ISO.

No emulator patch or code hook is baked into the game. Every other ISO byte is
checked against the fixed base, preserving all accumulated Korean work.
"""
import json
import struct
from pathlib import Path

from localization_pipeline import ROOT, sha, write_json
from iso_archive_stage import iso_inventory, exact, overlay, CHUNK
from runtime_compat import LAYOUT_SPEC, virtual_offset, inspect_integrated_layout, inspect_iso, pcsx2_crc

BASE = ROOT / 'build/dmap_flow_ko_v1/Poison Pink (Japan) - Korean DMAP flow v1.iso'
BASE_SHA = 'b1ebb5db3d0613ea9fe1160f6636c7481fb4d71c43e6b2d9b67f366ea9ca06b2'
OUT = ROOT / 'build/iso_dialogue_fix_v1'
ISO = OUT / 'Poison Pink (Japan) - Korean standalone v1.iso'


def verify_unplanned_bytes(source, output, replacements):
    """Re-read both complete images and reject changes outside the four words."""
    changed = 0
    with source.open('rb') as src, output.open('rb') as dst:
        for row in replacements:
            remaining = row['offset'] - src.tell()
            while remaining:
                size = min(remaining, CHUNK)
                if exact(src, size) != exact(dst, size):
                    raise ValueError('Unexpected ISO change before layout word')
                remaining -= size
            old = exact(src, len(row['data']))
            if sha(old) != row['expected_sha256'] or exact(dst, len(old)) != row['data']:
                raise ValueError('Unexpected layout replacement')
            changed += sum(a != b for a, b in zip(old, row['data']))
        while True:
            data = src.read(CHUNK)
            if not data:
                if dst.read(1):
                    raise ValueError('Output longer than base')
                break
            if data != exact(dst, len(data)):
                raise ValueError('Unexpected ISO change after layout words')
    return dict(passed=True, changed_bytes=changed, all_unplanned_bytes_identical=True)


def main():
    inventory = iso_inventory(BASE)
    entry = next(e for e in inventory['files'] if e['path'] == 'SLPS_258.54')
    with BASE.open('rb') as fp:
        fp.seek(entry['lba'] * 2048)
        before = exact(fp, entry['size'])
    target = bytearray(before)
    changes, replacements = [], []
    for row in json.loads(LAYOUT_SPEC.read_text())['words']:
        address = int(row['address'], 16)
        offset = virtual_offset(before, address)
        old = struct.pack('<I', int(row['original'], 16))
        new = struct.pack('<I', int(row['value'], 16))
        if before[offset:offset + 4] != old:
            raise ValueError('Latest base layout differs from reviewed original')
        target[offset:offset + 4] = new
        replacements.append(dict(offset=entry['lba'] * 2048 + offset, data=new, expected_sha256=sha(old)))
        changes.append(dict(row, elf_offset=offset, iso_offset=entry['lba'] * 2048 + offset))
    replacements.sort(key=lambda r: r['offset'])
    normalized, rows = inspect_integrated_layout(before, target)
    if normalized != before or len(rows) != 4:
        raise ValueError('Unexpected ELF change')
    OUT.mkdir(exist_ok=True)
    (OUT / 'SLPS_258.54').write_bytes(target)
    result = overlay(BASE, ISO, replacements, BASE_SHA)
    verified = verify_unplanned_bytes(BASE, ISO, replacements)
    if iso_inventory(ISO) != inventory:
        raise ValueError('ISO layout changed')
    info, _ = inspect_iso(ISO)
    if info['requires_external_patch'] or Path(str(ISO) + '.pcsx2').exists():
        raise ValueError('Unexpected external patch dependency')
    report = dict(status='built_static_verified', date='2026-10-01',
                  iso_path=str(ISO.relative_to(ROOT)), base_iso=str(BASE.relative_to(ROOT)),
                  iso=result, verification=verified, changes=changes,
                  elf_crc=pcsx2_crc(target), requires_external_patch=False,
                  runtime_verified=False, original_fov_font_width_and_code_preserved=True,
                  previous_translation_images_movies_preserved=True)
    write_json(OUT / 'report.json', report)
    write_json(ROOT / 'reports/iso_dialogue_fix_v1.json', report)
    (OUT / 'SHA256SUMS.txt').write_text(result['output_sha256'] + '  ' + ISO.name + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
