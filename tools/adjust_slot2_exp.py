#!/usr/bin/env python3
"""Change only EXP for the three verified Poison Pink characters in slot 2."""
import argparse
import copy
import json
import os
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path

from adjust_slot2_stats import ROOT, SOURCE, digest, read_members

OUT = ROOT / 'build/exp5000_slot2_20260930'


def prepare(companions=False):
    OUT.mkdir(exist_ok=True)
    backup = OUT / 'slot2-before-exp5000.p2s'
    if not backup.exists():
        shutil.copy2(SOURCE, backup)
    assert digest(SOURCE.read_bytes()) == digest(backup.read_bytes()), 'Slot changed since backup'
    infos, original = read_members(backup)
    old = original['eeMemory.bin']
    ram = bytearray(old)
    edits = []
    targets = [(1, '테이지', 0x4b885c),
               (2, '라난큘러스', 0x4b8948),
               (3, '루티카', 0x4b8a34)]
    if companions:
        targets = [(20, '시트라', 0x4ce8a4),
                   (16, '코모라', 0x4ce4f4),
                   (14, '알렉세이', 0x4ce31c)]
    for ident, name, base in targets:
        assert struct.unpack_from('<H', old, base)[0] == ident
        assert old[base + 3] in range(1, 100)
        record = old[base:base + 0xec]
        if companions:
            expected = {20: (5, 72, 117), 16: (3, 77, 102), 14: (4, 127, 150)}[ident]
            assert (old[base + 3], *struct.unpack_from('<2H', old, base + 4)) == expected
        locations = []
        start = 0
        while True:
            # Historical copies can have older EXP; require every other record byte identical.
            start = old.find(record[:4] if companions else record, start)
            if start < 0:
                break
            if not companions or old[start + 6:start + 0xec] == record[6:]:
                locations.append(start)
            start += 1
        assert len(locations) == (4 if companions else 5), (name, locations)
        for location in locations:
            address = location + 4
            before = struct.unpack_from('<H', old, address)[0]
            struct.pack_into('<H', ram, address, 5000)
            edits.append(dict(character=name, address=hex(address),
                              before=before, after=5000,
                              level_unchanged=old[base + 3]))
    allowed = {int(e['address'], 16) + i for e in edits for i in range(2)}
    changed = {i for i, (a, b) in enumerate(zip(old, ram)) if a != b}
    assert changed <= allowed and len(old) == len(ram)
    expected = dict(original, **{'eeMemory.bin': bytes(ram)})
    modified = OUT / 'slot2-exp5000.p2s'
    with zipfile.ZipFile(modified, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for info in infos:
            entry = copy.copy(info)
            if entry.compress_type == 93:
                entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, expected[entry.filename])
    _, actual = read_members(modified)
    assert actual == expected
    assert all(actual[k] == original[k] for k in original if k != 'eeMemory.bin')
    report = dict(source=str(SOURCE), backup=str(backup), modified=str(modified),
                  source_sha256=digest(backup.read_bytes()),
                  modified_sha256=digest(modified.read_bytes()), edits=edits,
                  changed_bytes=len(changed), zip_crc_verified=True,
                  other_fields_preserved=True, installed=False, runtime_verified=False)
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


def install():
    report = json.loads((OUT / 'report.json').read_text())
    source = Path(report['modified'])
    assert digest(SOURCE.read_bytes()) == report['source_sha256'], 'Slot changed; refusing overwrite'
    assert digest(source.read_bytes()) == report['modified_sha256']
    suffix = '.before-companions-exp5000-20260930-2202.bak' if 'companions' in OUT.name else '.before-exp5000-20260930.bak'
    external_backup = SOURCE.with_name(SOURCE.name + suffix)
    if not external_backup.exists():
        shutil.copy2(SOURCE, external_backup)
    assert digest(external_backup.read_bytes()) == report['source_sha256']
    fd, temporary = tempfile.mkstemp(prefix='.slot2-exp5000-', suffix='.tmp', dir=SOURCE.parent)
    os.close(fd)
    try:
        shutil.copyfile(source, temporary)
        assert digest(Path(temporary).read_bytes()) == report['modified_sha256']
        os.replace(temporary, SOURCE)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()
    assert digest(SOURCE.read_bytes()) == report['modified_sha256']
    assert read_members(SOURCE)[1] == read_members(source)[1]
    report.update(installed=True, external_backup=str(external_backup))
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--companions', action='store_true')
    args = parser.parse_args()
    if args.companions:
        OUT = ROOT / 'build/companions_exp5000_slot2_20260930_2202'
    report = install() if args.install else prepare(companions=args.companions)
    print(json.dumps(report, ensure_ascii=False, indent=2))
