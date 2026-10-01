#!/usr/bin/env python3
"""Import pinned user help pages over the adopted title/battle-menu build."""
import argparse
import json
import numpy as np
from PIL import Image
from localization_pipeline import ROOT, file_hash, sha, hed_tree, write_json
from iso_archive_stage import iso_inventory, exact, overlay
from ui_slice import verify_overlay
from ui_texture_codec import parse, serialize, preview_rgba
from title_artwork import compile_png


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',default='localization/user_help_artwork.json')
    ap.add_argument('--prepare-only',action='store_true')
    args=ap.parse_args();config_path=ROOT/args.config;c=json.loads(config_path.read_text())
    source=ROOT/c['base_iso'];output=(ROOT/c['output_iso']).resolve()
    if output.exists() or (ROOT/'build').resolve() not in output.parents:
        raise ValueError('Output must be new and below build/')
    if file_hash(source)!=c['base_iso_sha256']:
        raise ValueError('Base ISO changed')
    inv=iso_inventory(source);files={e['path']:e for e in inv['files']}
    output.parent.mkdir(parents=True,exist_ok=True)
    patches=[];checks=[]
    with source.open('rb') as fp:
        he=files['DATA/DMAP.HED'];de=files['DATA/DMAP.DAT']
        fp.seek(he['lba']*2048);members={e['path']:e for e in hed_tree(exact(fp,he['size']))[0]}
        for row in c['assets']:
            png=ROOT/row['png']
            if file_hash(png)!=row['png_sha256']:
                raise ValueError('Authored PNG changed')
            e=members[row['path']];pos=de['lba']*2048+e['offset']
            fp.seek(pos);raw=exact(fp,e['size'])
            if sha(raw)!=row['source_tim2_sha256']:
                raise ValueError('Source help page changed')
            before=parse(raw);width,height=before['width'],before['height']
            with Image.open(png) as im:
                if im.size!=(width,height) or 'A' not in im.getbands():
                    raise ValueError('PNG must match the source texture dimensions and retain alpha')
                authored=np.array(im.convert('RGBA'));alpha=authored[:,:,3]
            original=np.frombuffer(preview_rgba(before),dtype=np.uint8).reshape(height,width,4)
            old_alpha=original[:,:,3]
            if np.any(alpha!=old_alpha):
                raise ValueError('Authored alpha mask changed')
            unchanged=np.array_equal(authored,original)
            if unchanged:
                compiled=raw
                conversion=dict(width=width,height=height,unchanged_source_pixels=True,
                    changed_index_bytes=0,maximum_alpha_error=0,premultiplied_rgba_rmse=0,
                    original_header_and_palette_preserved=True,byte_exact_tim2_roundtrip=True)
            else:
                compiled,conversion=compile_png(raw,png)
            after=parse(compiled)
            if np.any(np.frombuffer(preview_rgba(after),dtype=np.uint8).reshape(height,width,4)[:,:,3]!=old_alpha):
                raise ValueError('Compiled alpha mask changed')
            if serialize(after)!=compiled:
                raise ValueError('TIM2 roundtrip mismatch')
            name=row['path'].split('/')[-1]
            (output.parent/name).write_bytes(compiled)
            Image.frombytes('RGBA',(width,height),preview_rgba(after)).save(output.parent/(name+'.png'))
            if not unchanged:
                patches.append(dict(offset=pos,data=compiled,expected_sha256=sha(raw)))
            checks.append(dict(path=row['path'],png=row['png'],png_sha256=row['png_sha256'],
                before_sha256=sha(raw),after_sha256=sha(compiled),alpha_mask_preserved=True,
                unchanged_source_pixels=unchanged,conversion=conversion))
    report=dict(base_iso=c['base_iso'],base_iso_sha256=c['base_iso_sha256'],iso_path=c['output_iso'],assets=checks,
        config_sha256=file_hash(config_path),tool_sha256=file_hash(ROOT/'tools/user_help_artwork.py'),
        compiler_sha256=file_hash(ROOT/'tools/title_artwork.py'),review=c['review'],runtime_verified=False,
        replaced_texture_count=len(patches),unchanged_texture_count=len(checks)-len(patches))
    if args.prepare_only:
        write_json(output.parent/'prepare.json',report)
    else:
        if c['review']['status']!='accepted':
            raise ValueError('Unresolved review corrections')
        iso=overlay(source,output,patches,c['base_iso_sha256'])
        if iso_inventory(output)!=inv:
            raise ValueError('ISO metadata changed')
        report.update(iso=iso,entire_iso_diff=verify_overlay(source,output,patches,c['base_iso_sha256'],iso['output_sha256']),
            all_other_bytes_preserved=True,adopted_title_and_battle_menu_preserved=True,iso_metadata_preserved=True)
        write_json(output.parent/'manifest.json',report)
        report_path=(ROOT/c.get('report_path','reports/user_help_artwork.json')).resolve()
        if (ROOT/'reports').resolve() not in report_path.parents:
            raise ValueError('Report must be below reports/')
        write_json(report_path,report)
    print(json.dumps(dict(output=str(output),prepared=len(checks),built=not args.prepare_only,
        conversions=[r['conversion'] for r in checks]),ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
