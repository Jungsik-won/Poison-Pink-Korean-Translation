#!/usr/bin/env python3
"""ISO9660 inventory and size-preserving overlays, with original hash guards."""
import argparse
import hashlib
import json
import os
import struct
import tempfile
from pathlib import Path

from localization_pipeline import ROOT, file_hash, hed_tree, sha, write_json

BLOCK = 2048
CHUNK = 4 * 1024 * 1024
SOURCE = ROOT / 'Poison Pink (Japan)'
ISO = SOURCE / 'Poison Pink (Japan).iso'


def exact(fp, size):
    data = fp.read(size)
    if len(data) != size:
        raise ValueError('Truncated input')
    return data


def both32(data, off):
    little = struct.unpack_from('<I', data, off)[0]
    if little != struct.unpack_from('>I', data, off + 4)[0]:
        raise ValueError('ISO endian fields disagree')
    return little


def parse_record(record):
    if len(record) < 34 or record[0] != len(record):
        raise ValueError('Invalid ISO directory record')
    name_size = record[32]
    if 33 + name_size > len(record):
        raise ValueError('Invalid ISO name length')
    if record[1] or record[26] or record[27] or record[25] & 0x80:
        raise ValueError('Extended, interleaved, or multi-extent ISO entry unsupported')
    return dict(lba=both32(record, 2), size=both32(record, 10),
                directory=bool(record[25] & 2), raw_name=record[33:33 + name_size])


def iso_inventory(path):
    size = path.stat().st_size
    files, dirs, visited = [], [], set()
    with path.open('rb') as fp:
        fp.seek(16 * BLOCK)
        pvd = exact(fp, BLOCK)
        if pvd[:7] != b'\x01CD001\x01':
            raise ValueError('Expected primary ISO9660 volume descriptor at sector 16')
        if struct.unpack_from('<H', pvd, 128)[0] != BLOCK or struct.unpack_from('>H', pvd, 130)[0] != BLOCK:
            raise ValueError('Unexpected ISO block size')
        volume_blocks = both32(pvd, 80)
        if volume_blocks * BLOCK != size:
            raise ValueError('Unexpected trailing or missing ISO bytes')
        root = parse_record(pvd[156:156 + pvd[156]])

        def walk(entry, prefix):
            if entry['lba'] in visited:
                raise ValueError('Cyclic/aliased ISO directories')
            visited.add(entry['lba'])
            if entry['lba'] * BLOCK + entry['size'] > size:
                raise ValueError('Directory outside ISO')
            fp.seek(entry['lba'] * BLOCK)
            data = exact(fp, entry['size'])
            dirs.append(dict(path=prefix, lba=entry['lba'], size=entry['size']))
            pos = 0
            while pos < len(data):
                count = data[pos]
                if not count:
                    pos = ((pos // BLOCK) + 1) * BLOCK
                    continue
                if pos + count > len(data) or pos % BLOCK + count > BLOCK:
                    raise ValueError('Directory record crosses boundary')
                item = parse_record(data[pos:pos + count])
                pos += count
                if item['raw_name'] in (b'\0', b'\1'):
                    continue
                raw_name = item.pop('raw_name').decode('ascii')
                name = raw_name.split(';')[0].rstrip('.')
                if not name or name in ('.', '..') or '/' in name or '\\' in name:
                    raise ValueError('Unsafe ISO name')
                full = prefix + '/' + name if prefix else name
                if item['lba'] * BLOCK + item['size'] > size:
                    raise ValueError('File outside ISO')
                if item['directory']:
                    walk(item, full)
                else:
                    files.append(dict(item, path=full, iso_name=raw_name))
        walk(root, '')
    paths = [f['path'] for f in files]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate normalized ISO paths')
    spans = sorted((f['lba'] * BLOCK, f['lba'] * BLOCK + f['size']) for f in files)
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('Overlapping ISO file extents')
    return dict(volume_blocks=volume_blocks, logical_block_size=BLOCK,
                files=files, directories=dirs)


def lock():
    return json.loads((ROOT / 'localization/source.lock.json').read_text())['files']


def source_sha(path):
    return lock()[str(path.resolve().relative_to(SOURCE.resolve()))]['sha256']


def compare_iso():
    inventory = iso_inventory(ISO)
    baseline = lock()
    with ISO.open('rb') as fp:
        for entry in inventory['files']:
            local = SOURCE / entry['path']
            if not local.is_file() or local.stat().st_size != entry['size']:
                raise ValueError('Missing or wrong-sized extracted file: ' + entry['path'])
            fp.seek(entry['lba'] * BLOCK)
            h = hashlib.sha256()
            remaining = entry['size']
            while remaining:
                chunk = exact(fp, min(CHUNK, remaining))
                h.update(chunk)
                remaining -= len(chunk)
            extracted_hash = file_hash(local)
            if h.hexdigest() != extracted_hash or extracted_hash != baseline[entry['path']]['sha256']:
                raise ValueError('ISO/extracted/baseline mismatch: ' + entry['path'])
            entry['sha256'] = extracted_hash
    expected = set(baseline) - {ISO.name}
    if expected != {entry['path'] for entry in inventory['files']}:
        raise ValueError('ISO and extracted file sets differ')
    if file_hash(ISO) != source_sha(ISO):
        raise ValueError('Original ISO hash mismatch')
    inventory.update(all_extracted_files_match=True, source_iso_sha256=source_sha(ISO), runtime_boot_test=False)
    write_json(ROOT / 'reports/iso_inventory.json', inventory)
    print('ISO/extracted/baseline match: {} files'.format(len(inventory['files'])), flush=True)
    return inventory


def validate_ranges(size, replacements):
    prev = 0
    for r in sorted(replacements, key=lambda v: v['offset']):
        off, data = r['offset'], r['data']
        if not isinstance(off, int) or off < prev or off + len(data) > size:
            raise ValueError('Overlapping or out-of-range replacement')
        prev = off + len(data)


def overlay(source, output, replacements, expected_sha):
    """Atomically publish only after checking the whole source and old payload hashes.

    Same-size ranges only: no ISO metadata, archive offsets, or lengths change.
    """
    source, output = source.resolve(), output.resolve()
    if output == source or output.exists():
        raise ValueError('Output already exists or aliases source')
    if SOURCE.resolve() == output or SOURCE.resolve() in output.parents:
        raise ValueError('Output may not be inside the original game folder')
    replacements = sorted(replacements, key=lambda r: r['offset'])
    validate_ranges(source.stat().st_size, replacements)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=output.name + '.', suffix='.partial', dir=str(output.parent))
    original_hash, result_hash = hashlib.sha256(), hashlib.sha256()
    changed = 0
    compat = None
    sidecar = None
    sidecar_created = False
    try:
        with source.open('rb') as src, os.fdopen(fd, 'wb') as dst:
            def copy(size):
                while size:
                    data = exact(src, min(size, CHUNK))
                    original_hash.update(data)
                    result_hash.update(data)
                    dst.write(data)
                    size -= len(data)
            for replacement in replacements:
                copy(replacement['offset'] - src.tell())
                data = replacement['data']
                old = exact(src, len(data))
                if sha(old) != replacement['expected_sha256']:
                    raise ValueError('Original replacement payload hash mismatch')
                changed += sum(a != b for a, b in zip(old, data))
                original_hash.update(old)
                result_hash.update(data)
                dst.write(data)
            copy(source.stat().st_size - src.tell())
        if original_hash.hexdigest() != expected_sha:
            raise ValueError('Original whole-file hash mismatch; output not published')
        if file_hash(Path(tmp)) != result_hash.hexdigest():
            raise ValueError('Written output verification failed')
        if output.suffix.lower() == '.iso':
            # Validate the final ELF before publication. Legacy builds require
            # a CRC-matched sidecar; the reviewed four-word integrated layout
            # is self-contained. HED/DAT overlays do not enter this ISO-only gate.
            from runtime_compat import inspect_iso, publish_sidecar
            info, raw = inspect_iso(Path(tmp))
            if info.get('integrated_dialogue_layout'):
                compat = dict(elf_crc=info['elf_crc'], requires_external_patch=False,
                              integrated_dialogue_layout=info['integrated_dialogue_layout'],
                              checked_patch_addresses=info['patch_count'])
            else:
                sidecar, sidecar_created = publish_sidecar(output, info, raw, result_hash.hexdigest())
                compat = dict(elf_crc=info['elf_crc'], sidecar=str(sidecar),
                              checked_patch_addresses=info['patch_count'])
        # hard-link publication refuses a raced existing destination, unlike replace().
        os.link(tmp, str(output))
        return dict(source_sha256=expected_sha, output_sha256=result_hash.hexdigest(),
                    bytes=output.stat().st_size, changed_bytes=changed, size_preserved=True,
                    runtime_compatibility=compat,
                    replacements=[dict(offset=r['offset'], size=len(r['data']),
                        before_sha256=r['expected_sha256'], after_sha256=sha(r['data'])) for r in replacements])
    except Exception:
        if sidecar_created:
            import shutil
            shutil.rmtree(sidecar)
        raise
    finally:
        Path(tmp).unlink(missing_ok=True)


def plan_archive_replacements(hed_bytes, dat, replacements, allow_padding_growth=False, allow_shrink=False):
    files, _ = hed_tree(hed_bytes)
    ordered = sorted(files, key=lambda e: e['offset'])
    by_path = {e['path']: e for e in files}
    limits = {e['path']: (ordered[i+1]['offset'] if i+1 < len(ordered) else dat.stat().st_size)
              for i,e in enumerate(ordered)}
    patches, hed_patches, growth = [], [], []
    with dat.open('rb') as fp:
        for path, data in replacements.items():
            entry = by_path[path]
            old_size, new_size = entry['size'], len(data)
            if new_size != old_size:
                if new_size == 0 or (new_size < old_size and not allow_shrink) or (new_size > old_size and not allow_padding_growth):
                    raise ValueError('Member resize not supported')
                if entry['offset'] + new_size > limits[path]:
                    raise ValueError('Growth exceeds reserved archive padding')
                if new_size > old_size:
                    fp.seek(entry['offset'] + old_size)
                    if any(exact(fp, new_size - old_size)):
                        raise ValueError('Growth would overwrite nonzero padding')
                field = entry['index']*44 + 4
                hed_patches.append(dict(offset=field, data=struct.pack('<I', new_size),
                                        expected_sha256=sha(hed_bytes[field:field+4])))
                growth.append(dict(path=path, old_size=old_size, new_size=new_size,
                                   consumed_zero_padding=max(0,new_size-old_size),
                                   released_zero_padding=max(0,old_size-new_size), offset=entry['offset']))
            fp.seek(entry['offset'])
            old = exact(fp, max(old_size,new_size))
            payload = data + bytes(max(0,old_size-new_size))
            patches.append(dict(offset=entry['offset'], data=payload, expected_sha256=sha(old)))
    validate_ranges(dat.stat().st_size, patches)
    return files, patches, hed_patches, growth


def stage_archive(archive, output_dir, replacements=None, allow_padding_growth=False, allow_shrink=False):
    if archive not in {p.stem for p in (SOURCE / 'DATA').glob('*.DAT')}:
        raise ValueError('Unknown archive')
    hed = SOURCE / 'DATA' / (archive + '.HED')
    dat = hed.with_suffix('.DAT')
    files, patches, hed_patches, growth = plan_archive_replacements(
        hed.read_bytes(), dat, replacements or {}, allow_padding_growth, allow_shrink)
    output_dir = Path(output_dir)
    h_report = overlay(hed, output_dir / hed.name, hed_patches, source_sha(hed))
    d_report = overlay(dat, output_dir / dat.name, patches, source_sha(dat))
    # Verify each archived member independently; retain all gaps/padding via overlay.
    with dat.open('rb') as src, (output_dir / dat.name).open('rb') as dst:
        for entry in files:
            src.seek(entry['offset']); dst.seek(entry['offset'])
            old = exact(src, entry['size'])
            expected = (replacements or {}).get(entry['path'], old)
            new = exact(dst, len(expected))
            if new != expected:
                raise ValueError('Staged member verification failed: ' + entry['path'])
    staged_entries, _ = hed_tree((output_dir / hed.name).read_bytes())
    for old, new in zip(files, staged_entries):
        expected_size = len((replacements or {}).get(old['path'], b'')) if old['path'] in (replacements or {}) else old['size']
        if new['offset'] != old['offset'] or new['size'] != expected_size or new['path'] != old['path']:
            raise ValueError('Staged HED member mismatch')
    return dict(archive=archive, hed=h_report, dat=d_report, members_verified=len(files),
                offsets_preserved=True, bounded_growth=growth)


def stage_iso(output, staged_files):
    inventory = iso_inventory(ISO)
    by_path = {e['path']: e for e in inventory['files']}
    patches = []
    for path, staged in staged_files.items():
        entry = by_path[path]
        data = Path(staged).read_bytes()
        if len(data) != entry['size']:
            raise ValueError('ISO file resize not supported')
        patches.append(dict(offset=entry['lba'] * BLOCK, data=data,
                           expected_sha256=lock()[path]['sha256']))
    report = overlay(ISO, Path(output), patches, source_sha(ISO))
    if iso_inventory(Path(output)) != inventory:
        raise ValueError('ISO directory layout changed')
    report.update(lba_layout_preserved=True, runtime_boot_test=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['iso-audit', 'noop-archives'])
    args = parser.parse_args()
    if args.command == 'iso-audit':
        compare_iso()
    else:
        reports = []
        for dat in sorted((SOURCE / 'DATA').glob('*.DAT')):
            report = stage_archive(dat.stem, ROOT / 'build/noop/DATA')
            if report['dat']['changed_bytes'] or report['hed']['changed_bytes']:
                raise ValueError('No-op output changed')
            reports.append(report)
            print(dat.stem + ': no-op exact match', flush=True)
        write_json(ROOT / 'reports/noop_archives.json', dict(archives=reports, runtime_boot_test=False))


if __name__ == '__main__':
    main()
