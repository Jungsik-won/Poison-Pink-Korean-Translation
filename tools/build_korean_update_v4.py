"""Integrate reviewed voice catalog v3 and four user assets over released v3.

Reconstruct the old ELF first to guard every previous code change. The new ELF
occupies the same reserved ISO gap; only its directory size and new payload grow.
"""
import json
import argparse
import struct
from pathlib import Path

from localization_pipeline import ROOT, sha, hed_tree, write_json, file_hash
from iso_archive_stage import iso_inventory, overlay, exact
from build_iso_dialogue_fix import verify_unplanned_bytes
from build_battle_subtitles import assemble, build_elf, directory_fields
from runtime_compat import inspect_iso, elf_segments, virtual_offset
from ui_texture_codec import parse, unpack_indices

BASE = ROOT/'build/battle_voice_subtitles_v1/Poison Pink (Japan) - Korean battle subtitles v3.iso'
BASE_SHA = '8ba7111a988b095902e727f089bdf5ac12778c59cfeb127e193402ce17a888b9'
OUT = ROOT/'build/korean_update_v4'
ISO = OUT/'Poison Pink (Japan) - Korean update v4.iso'
CATALOG = ROOT/'localization/battle_voice_subtitles_v3.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-existing', action='store_true', help='Recover after a post-build check interruption; never rewrite the ISO')
    args = parser.parse_args()
    inv = iso_inventory(BASE)
    files = {e['path']: e for e in inv['files']}
    catalog = json.loads(CATALOG.read_text())
    assert catalog['counts']['reviewed_translation'] == 442
    old_rows = json.loads((ROOT/'localization/battle_voice_subtitles_v1.json').read_text())['rows']
    original = (ROOT/'build/iso_dialogue_fix_v1/SLPS_258.54').read_bytes()
    old_payload, old_meta = assemble(old_rows)
    old_elf, _ = build_elf(original, old_payload, old_meta)
    payload, meta = assemble(catalog['rows'])
    elf, _ = build_elf(original, payload, meta)
    assert meta['heap_start'] == 0x655000
    assert old_payload[:0x440] == payload[:0x440]
    assert old_meta['heap_start'] == meta['heap_start']
    assert elf_segments(old_elf)[0] == elf_segments(elf)[0]
    # ELF extension length fields differ, but the original loaded game code/data
    # including allocator constants, four dialogue words and hooks is identical.
    start = elf_segments(elf)[0][1]
    end = start + elf_segments(elf)[0][4]
    assert old_elf[start:end] == elf[start:end]
    assert len(elf) > len(old_elf)
    artwork_report = json.loads((ROOT/'reports/user_shop_dictionary_v1.json').read_text())
    assert artwork_report['status'] in ('prepared_not_applied_to_iso', 'applied_to_iso')
    assets = artwork_report.get('pending_assets', artwork_report.get('applied_assets'))
    assert len(assets) == 4
    patches, changed_assets = [], []
    with BASE.open('rb') as f:
        entry = files['SLPS_258.54']
        pos = entry['lba'] * 2048
        f.seek(pos)
        assert exact(f, entry['size']) == old_elf
        assert not any(exact(f, len(elf)-entry['size']))
        for e in inv['files'] + inv['directories']:
            if e['path'] != 'SLPS_258.54':
                assert pos+len(elf) <= e['lba']*2048 or e['lba']*2048+e['size'] <= pos
        f.seek(pos)
        patches.append(dict(offset=pos, data=elf, expected_sha256=sha(exact(f,len(elf)))))
        _, size_field = directory_fields(f, inv, 'SLPS_258.54')
        f.seek(size_field)
        patches.append(dict(offset=size_field, data=struct.pack('<I',len(elf))+struct.pack('>I',len(elf)),
                            expected_sha256=sha(exact(f,8))))
        h, d = files['DATA/STATUS.HED'], files['DATA/STATUS.DAT']
        f.seek(h['lba']*2048)
        members = {e['path']:e for e in hed_tree(exact(f,h['size']))[0]}
        for asset, detail in zip(assets, artwork_report['assets']):
            data = (ROOT/asset['replacement']).read_bytes()
            assert sha(data) == asset['sha256']
            member = members[asset['member']]
            position = d['lba']*2048+member['offset']
            f.seek(position)
            before = exact(f,member['size'])
            assert sha(before) == asset['expected_original_sha256']
            assert len(before) == len(data)
            om, nm = parse(before), parse(data)
            assert om['header'] == nm['header'] and om['palette'] == nm['palette']
            oi, ni = unpack_indices(om), unpack_indices(nm)
            editable = set()
            for x,y,w,height in detail['edit_rectangles_xywh']:
                for row in range(y,y+height):
                    editable.update(range(row*om['width']+x,row*om['width']+x+w))
            assert all(a == b for i,(a,b) in enumerate(zip(oi,ni)) if i not in editable)
            patches.append(dict(offset=position,data=data,expected_sha256=sha(before)))
            changed_assets.append(dict(member=asset['member'],offset=position,size=len(data),
                before_sha256=sha(before),after_sha256=sha(data),outside_edit_regions_preserved=True))
    patches.sort(key=lambda r:r['offset'])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'SLPS_258.54').write_bytes(elf)
    (OUT/'subtitle_segment.bin').write_bytes(payload)
    print('Building ISO with 442 captions and four user textures',flush=True)
    if args.verify_existing:
        assert file_hash(BASE) == BASE_SHA
        result = dict(output_sha256=file_hash(ISO),source_sha256=BASE_SHA,
                      size=ISO.stat().st_size, recovered_existing_output=True)
    else:
        result = overlay(BASE,ISO,patches,BASE_SHA)
    expected = json.loads(json.dumps(inv))
    next(e for e in expected['files'] if e['path']=='SLPS_258.54')['size'] = len(elf)
    assert iso_inventory(ISO) == expected
    print('Verifying every byte outside planned replacements',flush=True)
    verified = verify_unplanned_bytes(BASE,ISO,patches)
    info, _ = inspect_iso(ISO)
    assert info['elf_sha256'] == sha(elf) and not info['requires_external_patch']
    assert not Path(str(ISO)+'.pcsx2').exists()
    with ISO.open('rb') as f:
        for asset in changed_assets:
            f.seek(asset['offset']);assert sha(exact(f,asset['size'])) == asset['after_sha256']
    report = dict(status='built_static_verified',date='2026-10-02',iso_path=str(ISO.relative_to(ROOT)),
        base_iso=str(BASE.relative_to(ROOT)),iso=result,verification=verified,
        catalog=str(CATALOG.relative_to(ROOT)),catalog_sha256=sha(CATALOG.read_bytes()),
        counts=catalog['counts'],translated_bank_slots=511,
        new_captions_vs_released=32,new_translation_bank_slots_vs_released=55,
        replacements=changed_assets,elf=meta,elf_crc=info['elf_crc'],
        previous_game_load_segment_identical=True,previous_translation_images_movies_preserved=True,
        requires_external_patch=False,runtime_verified=False,direct_gpt_audio_input=False,
        human_listening_audit=False)
    write_json(OUT/'report.json',report)
    write_json(ROOT/'reports/korean_update_v4.json',report)
    (OUT/'SHA256SUMS.txt').write_text(result['output_sha256']+'  '+ISO.name+'\n')
    print(json.dumps(dict(iso=report['iso_path'],sha256=result['output_sha256'],
        elf_crc=info['elf_crc'],verification=verified),ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()
