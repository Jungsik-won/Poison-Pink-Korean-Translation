#!/usr/bin/env python3
"""Consolidate reviewed lettering over the pinned Korean dialogue/system build."""
import json
from collections import Counter
from pathlib import Path

from localization_pipeline import sha, file_hash, hed_tree, write_json
from iso_archive_stage import iso_inventory, exact, overlay
from ui_texture_codec import parse, serialize
from runtime_compat import inspect_iso, inspect_profile
import build_user_translation_import as verifier

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'build/battle_heading_v1/Poison Pink (Japan) - Korean heading alignment v1.iso'
BASE_SHA = '22b4219433f1e3d3d429c1cc6bc37738ea463163782b53d6e1ec47d1c4ea8c58'
OUT = ROOT / 'build/korean_integrated_20260920'
OUTPUT = OUT / 'Poison Pink (Japan) - Korean integrated 20260920.iso'


def main():
    if OUTPUT.exists():
        raise ValueError('Refusing to overwrite a completed ISO')
    work = ROOT / 'outputs/battle_lettering_work_v3'
    manifest = json.loads((work / 'manifest.json').read_text())
    for doc in manifest['documents']:
        assert file_hash(work / doc['psd']) == doc['sha256'], doc['psd']
    selected = {}
    reports = ['capture_notice_euljiro_v1', 'battle_titles_euljiro_v1', 'battle_spacing_euljiro_v2']
    for name in reports:
        report = json.loads((ROOT / 'reports' / (name + '.json')).read_text())
        rows = report['rows'] if name.startswith('capture') else report['textures']
        for row in rows:
            source = 'BATTLE/battle/catch/' + row['id'] + '.tm2' if name.startswith('capture') else row['source']
            if name == 'battle_spacing_euljiro_v2':
                assert source in selected
            else:
                assert source not in selected
            path = ROOT / 'build' / name / 'textures' / source
            data = path.read_bytes()
            assert sha(data) == row['compiled_sha256'], source
            original = (ROOT / 'extracted/original/raw' / source).read_bytes()
            if 'source_sha256' in row:
                assert sha(original) == row['source_sha256'], source
            before, after = parse(original), parse(data)
            assert len(data) == len(original)
            assert after['header'] == before['header'] and after['palette'] == before['palette']
            assert serialize(after) == data
            selected[source] = dict(data=data, compiled_from=str(path.relative_to(ROOT)), report=name,
                                    original_sha256=sha(original))
    counts = dict(Counter(p.split('/')[0] for p in selected))
    assert counts == {'BATTLE': 56, 'DMAP': 137} and len(selected) == 193
    inventory = iso_inventory(BASE)
    files = {e['path']: e for e in inventory['files']}
    patches, entries = [], []
    with BASE.open('rb') as fp:
        archives = {}
        for archive in counts:
            hed = files['DATA/' + archive + '.HED']
            fp.seek(hed['lba'] * 2048)
            members, _ = hed_tree(exact(fp, hed['size']))
            archives[archive] = {e['path']: e for e in members}
        for source, entry in sorted(selected.items()):
            archive, member = source.split('/', 1)
            info = archives[archive][member]
            data = entry['data']
            assert info['size'] == len(data), source
            dat = files['DATA/' + archive + '.DAT']
            assert info['offset'] + len(data) <= dat['size']
            offset = dat['lba'] * 2048 + info['offset']
            fp.seek(offset)
            old = exact(fp, len(data))
            assert parse(old)['header'] == parse(data)['header']
            patches.append(dict(offset=offset, data=data, expected_sha256=sha(old)))
            entries.append(dict(source=source, offset=offset, size=len(data), before_sha256=sha(old),
                                compiled_sha256=sha(data), **{k: v for k, v in entry.items() if k != 'data'}))
    print('Validated 150 PSDs and 193 same-size texture replacements; writing ISO.', flush=True)
    result = overlay(BASE, OUTPUT, patches, BASE_SHA)
    print('ISO published; verifying every byte against the integration plan.', flush=True)
    assert iso_inventory(OUTPUT) == inventory
    verifier.BASE_HASH = BASE_SHA
    validation = verifier.verify_stream(BASE, OUTPUT, patches, result['output_sha256'])
    with OUTPUT.open('rb') as fp:
        for entry in entries:
            fp.seek(entry['offset'])
            assert sha(exact(fp, entry['size'])) == entry['compiled_sha256']
    compat, raw = inspect_iso(OUTPUT)
    assert compat['elf_crc'] == '7502FF83' and compat['patch_count'] == 34
    profile = inspect_profile(Path.home() / 'Library/Application Support/PCSX2', compat, raw)
    report = dict(iso_path=str(OUTPUT.relative_to(ROOT)), base_iso=str(BASE.relative_to(ROOT)),
                  base_iso_sha256=BASE_SHA, iso=result, validation=validation,
                  texture_count=len(entries), archive_counts=counts, textures=entries,
                  psd_hashes_verified=len(manifest['documents']), source_reports=reports,
                  compatibility=compat, user_profile_readonly_check=profile,
                  runtime_verified=False, inherited_nontexture_bytes_identical=True,
                  previous_dialogue_runtime_evidence='reports/dialogue_missing_fix.json',
                  name_db_synchronized=False)
    write_json(ROOT / 'reports/korean_integrated_20260920.json', report)
    print(json.dumps(dict(iso=str(OUTPUT), sha256=result['output_sha256'], verification=validation,
                          profile=profile), ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
