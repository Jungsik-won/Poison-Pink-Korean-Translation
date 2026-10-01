#!/usr/bin/env python3
"""Read-only source audit and review catalog. Does not build a game patch.

Python 3.8+, standard library only. Paths resolve from this file, not cwd.
"""
import argparse
import collections
import hashlib
import json
import re
import struct
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as fp:
        for block in iter(lambda: fp.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read_jsonl(path):
    with path.open(encoding='utf-8') as fp:
        return [json.loads(line) for line in fp if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + '\n')


def hed_tree(blob):
    """Decode observed HED directory ranges, retaining original record bytes.

    Zero timestamp directory records point to HED record indices, not DAT bytes.
    Unknown layouts fail rather than guessing or dropping entries.
    """
    if len(blob) % 44:
        raise ValueError('HED size is not a multiple of 44')
    entries = []
    for index in range(len(blob) // 44):
        off, size, raw_name, stamp = struct.unpack_from('<II32sI', blob, index * 44)
        name = raw_name.split(b'\0', 1)[0].decode('ascii')
        entries.append(dict(index=index, offset=off, size=size, name=name,
                            timestamp=stamp, raw_name=raw_name))
    rebuilt = b''.join(struct.pack('<II32sI', e['offset'], e['size'], e['raw_name'],
                                  e['timestamp']) for e in entries)
    if rebuilt != blob:
        raise ValueError('HED roundtrip mismatch')
    visited = set()
    files, directories = [], []

    def walk(directory, prefix):
        start, count = directory['offset'], directory['size']
        if count < 2 or start + count > len(entries):
            raise ValueError('Invalid directory range: ' + prefix)
        if entries[start]['name'] != '..' or entries[start + count - 1]['name'] != '--DirEnd--':
            raise ValueError('Invalid directory boundaries: ' + prefix)
        directories.append(dict(path=prefix, index=directory['index'], start=start, count=count))
        for e in entries[start:start + count]:
            if e['index'] in visited:
                raise ValueError('Overlapping or cyclic HED directory')
            visited.add(e['index'])
            if e['name'] in ('..', '--DirEnd--'):
                continue
            if '/' in e['name'] or '\\' in e['name'] or e['name'] in ('', '.'):
                raise ValueError('Unsafe HED name')
            path = prefix + '/' + e['name']
            if e['timestamp'] == 0:
                walk(e, path)
            else:
                files.append({k: v for k, v in dict(e, path=path).items() if k != 'raw_name'})

    if len(entries) < 4 or entries[0]['timestamp'] != 0 or entries[1]['name'] != '--DirEnd--':
        raise ValueError('Unknown HED root layout')
    visited.update((0, 1))
    walk(entries[0], entries[0]['name'])
    if len(visited) != len(entries):
        raise ValueError('Unvisited HED records')
    return files, directories


def symbol_end(data):
    if len(data) < 3 or data[0] != 0xfe:
        raise ValueError('Unknown RTB header')
    pos = 3
    for _ in range(struct.unpack_from('<H', data, 1)[0]):
        if pos + 5 > len(data):
            raise ValueError('Truncated RTB symbol')
        size = data[pos + 4]
        pos += 5 + size
        if pos > len(data):
            raise ValueError('Truncated RTB symbol name')
    return pos


def candidates(data, entry):
    # Full VM boundaries are still unknown: these are explicitly untrusted candidates.
    pos = symbol_end(data)
    rows = []
    while True:
        off = data.find(b'\x33\x01', pos)
        if off < 0:
            break
        pos = off + 1
        if off + 6 > len(data):
            continue
        size = data[off + 5]
        end = off + 6 + size
        if end > len(data):
            continue
        raw = data[off + 6:end]
        try:
            source = raw.decode('cp932', errors='strict')
        except UnicodeDecodeError:
            source = None
        rows.append(dict(
            id='DMAP:{:04d}:{:08x}'.format(entry['index'], off),
            archive='DMAP', hed_index=entry['index'], path=entry['path'],
            member_sha256=sha(data), opcode_offset=off, payload_offset=off + 6,
            length_offset=off + 5, source_byte_length=size, raw_hex=raw.hex(),
            source_sha256=sha(raw), source=source, tag_hex=data[off+2:off+5].hex(),
            next_bytes_hex=data[end:end+5].hex(),
            confidence='pattern_candidate', role='unclassified',
            classification_hint=('decode_error' if source is None else
                                 'japanese_candidate' if re.search('[\u3040-\u30ff\u3400-\u9fff]', source) else
                                 'non_japanese_candidate'),
            review_required=True))
    return rows


def source_files(source):
    return sorted(p for p in source.rglob('*') if p.is_file() and p.name != '.DS_Store')


def source_snapshot(source):
    return {str(p.relative_to(source)): dict(size=p.stat().st_size, sha256=file_hash(p))
            for p in source_files(source)}


def audit(config):
    source = ROOT / config['source_root']
    lock_path = ROOT / config['source_lock']
    existed = lock_path.exists()
    snapshot = source_snapshot(source)
    if lock_path.exists():
        old = json.loads(lock_path.read_text(encoding='utf-8'))
        if old['files'] != snapshot:
            raise ValueError('Source differs from source.lock.json; baseline was NOT updated')
    report = dict(schema_version=1, archives={}, legacy={}, status='audit_only')
    catalog = []
    members = {}
    for hed in sorted((source / 'DATA').glob('*.HED')):
        if hed.name == 'SUBDIR.HED':
            report['subdir_raw_hex'] = hed.read_bytes().hex()
            continue
        files, dirs = hed_tree(hed.read_bytes())
        dat = hed.with_suffix('.DAT')
        dat_size = dat.stat().st_size
        spans = sorted((e['offset'], e['offset'] + e['size']) for e in files)
        if any(end > dat_size for start, end in spans):
            raise ValueError('Member outside DAT: ' + hed.name)
        if any(spans[i][1] > spans[i+1][0] for i in range(len(spans)-1)):
            raise ValueError('Overlapping DAT members: ' + hed.name)
        report['archives'][hed.stem] = dict(
            files=len(files), directories=len(dirs), hed_records=hed.stat().st_size // 44,
            dat_size=dat_size, all_files_aligned_0x4000=all(e['offset'] % 0x4000 == 0 for e in files),
            hed_roundtrip_equal=True, directory_ranges=dirs, members=files)
        with dat.open('rb') as fp:
            for e in files:
                if e['name'].lower().endswith('.rtb') or hed.stem in ('SYSTEM', 'ROOT', 'STATUS'):
                    fp.seek(e['offset'])
                    data = fp.read(e['size'])
                    members[(hed.stem, e['path'])] = data
                    if e['name'].lower().endswith('.rtb'):
                        if hed.stem != 'DMAP':
                            raise ValueError('Unexpected RTB archive')
                        catalog.extend(candidates(data, e))
    def member(archive, basename):
        found = [v for (a, p), v in members.items() if a == archive and p.split('/')[-1] == basename]
        if len(found) != 1:
            raise ValueError('Ambiguous member: ' + basename)
        return found[0]
    for name in ('all_dmap_dialogues', 'all_skills', 'all_characters_and_monsters', 'all_params'):
        rows = json.loads((ROOT / 'tools' / (name + '.json')).read_text(encoding='utf-8'))
        report['legacy'][name] = dict(rows=len(rows),
            replacement_character_rows=sum('\ufffd' in json.dumps(r, ensure_ascii=False) for r in rows),
            empty_name_rows=sum(r.get('name') == '' for r in rows))
    for name in ('PPITEM.dat', 'PPSKILL.dat', 'PPPARAM.dat'):
        data = member('STATUS', name)
        from status_db_codec import parse as parse_db, serialize as serialize_db, text_fields
        parsed_db = parse_db(data, name[:-4])
        if serialize_db(parsed_db) != data:
            raise ValueError('DB roundtrip mismatch: ' + name)
        for _, field in text_fields(parsed_db):
            field['value'].decode('cp932', errors='strict')
        report.setdefault('db_headers', {})[name] = dict(bytes=len(data),
            declared_count=struct.unpack_from('<H', data)[0], count_scope='first_section_only')
        report.setdefault('db_structure', {})[name] = dict(
            section_counts=[s['count'] for s in parsed_db['sections']],
            total_records=sum(s['count'] for s in parsed_db['sections']),
            exact_eof=True, lossless_roundtrip=True, strict_cp932=True)
    table_data = member('SYSTEM', 'kantable.dat')
    table = struct.unpack('<{}h'.format(len(table_data)//2), table_data)
    c_text = member('SYSTEM', 'kantable.h').decode('ascii')
    initializer = c_text[c_text.index('{') + 1:c_text.index('}')]
    parsed = tuple(int(x) for x in re.findall(r'-?\d+', initializer))
    if parsed != table:
        raise ValueError('Font C initializer differs from binary table')
    report['font'] = dict(table_entries=len(table), assigned=sum(x >= 0 for x in table),
                          min_id=min(table), max_id=max(table), first_16=list(table[:16]),
                          initializer_equals_binary=True, kanji_bytes=len(member('SYSTEM', 'kanji.dat')),
                          bitmap_layout='paired glyph layout inferred; runtime probe pending')
    elf = (source / 'SLPS_258.54').read_bytes()
    if elf[:6] != b'\x7fELF\x01\x01':
        raise ValueError('Expected ELF32 little endian')
    phoff = struct.unpack_from('<I', elf, 28)[0]
    phsize, phnum = struct.unpack_from('<HH', elf, 42)
    segments = [struct.unpack_from('<8I', elf, phoff + i*phsize) for i in range(phnum)]
    def va_to_offset(va):
        for typ, off, addr, _, size, _, _, _ in segments:
            if typ == 1 and addr <= va < addr + size:
                return off + va - addr
        raise ValueError('VA outside ELF file-backed LOAD segment')
    report['elf'] = dict(load_segments=[dict(file_offset=p[1], vaddr=p[2], file_size=p[4]) for p in segments if p[0] == 1], evidence=[])
    for start, count in ((0x1d5b08, 9), (0x1d61e0, 40), (0x1d6320, 20)):
        report['elf']['evidence'].append(dict(vaddr=hex(start), file_offset=hex(va_to_offset(start)),
            words=[dict(va=hex(start+i*4), word='{:08x}'.format(struct.unpack_from('<I', elf, va_to_offset(start+i*4))[0])) for i in range(count)]))
    report['rtb'] = dict(files=sum(p.lower().endswith('.rtb') for a, p in members if a == 'DMAP'),
                         candidates=len(catalog), hints=dict(collections.Counter(r['classification_hint'] for r in catalog)),
                         unique_ids=len(set(r['id'] for r in catalog)), complete_vm_parse=False)
    report['runtime_gates'] = config['gates']
    write_json(ROOT / 'reports' / 'audit.json', report)
    write_jsonl(ROOT / config['catalog'], catalog)
    if not lock_path.exists():
        write_json(lock_path, dict(schema_version=1, files=snapshot))
    print(json.dumps(dict(archives=len(report['archives']), rtb=report['rtb'], legacy=report['legacy'],
                          source_lock='matched' if existed else 'created'), ensure_ascii=False, indent=2))


def structural_exclusions(config):
    path = config.get('candidate_exclusions')
    if not path:
        return set()
    report = json.loads((ROOT / path).read_text())
    if file_hash(ROOT / config['catalog']) != report['catalog_sha256']:
        raise ValueError('Structural exclusions are stale; rerun RTB structural review')
    return {r['id'] for r in report['entries'] if r['status'] == 'exclude'}


def template(config, output):
    path = Path(output).resolve()
    if path.exists():
        raise ValueError('Refusing to overwrite an existing translation file')
    rows = read_jsonl(ROOT / config['catalog'])
    excluded = structural_exclusions(config)
    write_jsonl(path, [dict(id=r['id'], source_sha256=r['source_sha256'],
                           source=r['source'], target='', role='unclassified', status='unreviewed',
                           reviewer='', notes='') for r in rows if r['classification_hint'] == 'japanese_candidate' and r['id'] not in excluded])
    print('Created ' + str(path))


def lint(config, translation_path):
    catalog = {r['id']: r for r in read_jsonl(ROOT / config['catalog'])}
    excluded = structural_exclusions(config)
    rows = read_jsonl(Path(translation_path))
    errors, seen = [], set()
    for line, row in enumerate(rows, 1):
        def err(message):
            errors.append(dict(line=line, id=row.get('id'), error=message))
        ident = row.get('id')
        if ident in seen:
            err('duplicate id')
        seen.add(ident)
        ref = catalog.get(ident)
        if ref is None:
            err('unknown id')
            continue
        if row.get('source_sha256') != ref['source_sha256'] or row.get('source') != ref['source']:
            err('source changed or wrong revision')
        if row.get('status') not in ('unreviewed', 'draft', 'reviewed', 'exclude'):
            err('unknown status')
        target = row.get('target', '')
        if not isinstance(target, str):
            err('target must be a string')
            continue
        if ident in excluded and (target or row.get('status') in ('draft', 'reviewed')):
            err('not an RTB string instruction; structurally excluded candidate')
        if unicodedata.normalize('NFC', target) != target:
            err('target must be NFC composed Hangul')
        if any(ord(c) < 32 and c != '\n' for c in target):
            err('unsupported target control character')
        if row.get('status') == 'reviewed':
            if not target or not row.get('reviewer') or row.get('role') not in ('dialogue', 'speaker', 'choice', 'ui'):
                err('reviewed row requires target, reviewer, and explicit role')
        # Token grammar is not yet proven. Flag known-looking tokens for manual review.
        if target:
            token_pattern = r'@[A-Za-z0-9_]+|%[-+0-9.]*[A-Za-z]'
            if collections.Counter(re.findall(token_pattern, ref['source'] or '')) != collections.Counter(re.findall(token_pattern, target)):
                err('possible runtime token changed')
    result = dict(rows=len(rows), errors=errors, build_ready=False,
                  structurally_excluded_rows=sum(r.get('id') in excluded for r in rows),
                  byte_length_checked=False, reason='General translation encoding, role review, layout and runtime gates remain incomplete')
    write_json(ROOT / 'reports' / 'translation_lint.json', result)
    print(json.dumps(dict(rows=len(rows), errors=len(errors), build_ready=False), ensure_ascii=False))
    return bool(errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('audit', help='Hash original files including ISO; inspect archives; regenerate review candidates')
    p = sub.add_parser('template', help='Create review worksheet without overwriting existing work')
    p.add_argument('--output', default=str(ROOT / 'localization/translations.jsonl'))
    p = sub.add_parser('lint', help='Lint translation data; passing does not authorize a patch build')
    p.add_argument('--translations', default=str(ROOT / 'localization/translations.jsonl'))
    config = json.loads((ROOT / 'localization/pipeline.json').read_text(encoding='utf-8'))
    args = parser.parse_args()
    try:
        if args.command == 'audit':
            audit(config)
        elif args.command == 'template':
            template(config, args.output)
        else:
            return int(lint(config, args.translations))
    except (ValueError, OSError, KeyError, struct.error) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
