#!/usr/bin/env python3
"""Pack the four common-coordinate PSDs and optionally build a new ISO."""
import argparse
import json
from pathlib import Path
from battle_lettering_layout import ROOT, WORK, read_maps, read_common, pack_common, metadata
from build_battle_conditions_psd import compile_texture
from localization_pipeline import file_hash, sha, hed_tree, write_json
from iso_archive_stage import iso_inventory, exact, overlay
from ui_texture_codec import parse, preview_rgba
from PIL import Image
import build_user_translation_import as verifier

BASE=ROOT/'build/battle_conditions_psd_v1/Poison Pink (Japan) - Korean battle conditions v1.iso'
BASE_SHA='41021fe51f65c13eb12dbf122f251beaa5a742b287f79f2c2ca05a773bb36b8f'
OUT=ROOT/'build/battle_registration_v2'
OUTPUT=OUT/'Poison Pink (Japan) - Korean battle lettering aligned v3.iso'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--build',action='store_true')
    ap.add_argument('--base',type=Path,default=BASE)
    ap.add_argument('--base-sha256',default=BASE_SHA)
    ap.add_argument('--work',type=Path,default=WORK)
    ap.add_argument('--out',type=Path,default=OUT)
    ap.add_argument('--iso-name',default=OUTPUT.name)
    args=ap.parse_args()
    base=args.base.resolve();out=args.out.resolve();work=args.work.resolve()
    if Path(args.iso_name).name!=args.iso_name or not args.iso_name.endswith('.iso'):
        raise ValueError('ISO name must be a filename ending in .iso')
    output=out/args.iso_name
    assert not args.build or not output.exists(), 'Never overwrite an existing ISO'
    out.mkdir(exist_ok=True,parents=True)
    maps=read_maps();inv=iso_inventory(base);entries={e['path']:e for e in inv['files']}
    assets=[];patches=[]
    with base.open('rb') as f:
        he=entries['DATA/DMAP.HED'];de=entries['DATA/DMAP.DAT']
        f.seek(he['lba']*2048);members={e['path']:e for e in hed_tree(exact(f,he['size']))[0]}
        for n in range(5,9):
            source=work/f'bt_tx{n:02}_공통좌표.psd'
            common=read_common(source);packed=pack_common(common,n,maps)
            packed.save(out/f'bt_tx{n:02}.png')
            path=f'dmap/map/bstart/bt_tx{n:02}.tm2';e=members[path]
            offset=de['lba']*2048+e['offset'];f.seek(offset);old=exact(f,e['size'])
            original=(ROOT/'extracted/original/raw/DMAP'/path).read_bytes()
            new,conversion=compile_texture(original,packed)
            (out/f'bt_tx{n:02}.tm2').write_bytes(new)
            Image.frombytes('RGBA',(256,128),preview_rgba(parse(new))).save(out/f'bt_tx{n:02}_compiled.png')
            if old!=new:patches.append(dict(offset=offset,data=new,expected_sha256=sha(old)))
            assets.append(dict(path=path,source=str(source.relative_to(ROOT)),source_sha256=file_hash(source),
                               iso_offset=offset,before_sha256=sha(old),after_sha256=sha(new),
                               changed_bytes=sum(a!=b for a,b in zip(old,new)),conversion=conversion))
    report=dict(base_iso=str(base.relative_to(ROOT)),base_sha256=args.base_sha256,
                iso_path=str(output.relative_to(ROOT)),assets=assets,layout=metadata(maps),
                runtime_verified=False,heading_bt_tx04_unchanged=True,
                user_original_psds_unchanged=True,
                limitations=['Registration fits original flat mesh anchors; timing/deformation remain original.',
                             'This workbench covers bt_tx05–08. Other condition textures need their own maps.'])
    if args.build:
        iso=overlay(base,output,patches,args.base_sha256)
        assert iso_inventory(output)==inv
        verifier.BASE_HASH=args.base_sha256
        report.update(iso=iso,entire_iso_diff=verifier.verify_stream(base,output,patches,iso['output_sha256']))
    write_json(out/('manifest.json' if args.build else 'prepare.json'),report)
    print(json.dumps(dict(iso=str(output) if args.build else None,assets=[(a['path'],a['changed_bytes']) for a in assets]),ensure_ascii=False))


if __name__=='__main__':main()
