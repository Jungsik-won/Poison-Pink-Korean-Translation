#!/usr/bin/env python3
"""Apply the reviewed user battle-menu sheet to the pinned integrated ISO."""
import json
import numpy as np
from PIL import Image
from localization_pipeline import ROOT, file_hash, sha, hed_tree, write_json
from iso_archive_stage import iso_inventory, exact, overlay
from ui_slice import verify_overlay
from ui_texture_codec import parse, preview_rgba, uad_rectangles
from title_artwork import compile_png


def main():
    config_path = ROOT/'localization/battle_menu_artwork.json'
    c = json.loads(config_path.read_text())
    source = ROOT/c['base_iso']; authored = ROOT/c['png']
    output = (ROOT/c['output_iso']).resolve()
    if output.exists() or (ROOT/'build').resolve() not in output.parents:
        raise ValueError('Output must be new and below build/')
    if file_hash(source) != c['base_iso_sha256'] or file_hash(authored) != c['png_sha256']:
        raise ValueError('Pinned input changed')
    inv = iso_inventory(source); entries = {e['path']: e for e in inv['files']}
    with source.open('rb') as fp:
        h = entries['DATA/STATUS.HED']; d = entries['DATA/STATUS.DAT']
        fp.seek(h['lba']*2048)
        members = {e['path']: e for e in hed_tree(exact(fp,h['size']))[0]}
        def read_member(name):
            e = members[name]; pos = d['lba']*2048+e['offset']
            fp.seek(pos)
            return pos, exact(fp,e['size'])
        offset, raw = read_member('status/sys000.tm2')
        _, uad = read_member('status/sys000.uad')
    if sha(raw) != c['source_tim2_sha256'] or sha(uad) != c['uad_sha256']:
        raise ValueError('Source texture or sprite coordinates changed')
    model = parse(raw); w,h = model['width'],model['height']
    rectangles = uad_rectangles(uad,w,h)['rectangles']
    mask = np.zeros((h,w),dtype=bool)
    for r in rectangles:
        x,y,rw,rh = r['rect']
        if (rw,rh) == (64,24):
            mask[y:y+rh,x:x+rw] = True
    before = np.frombuffer(preview_rgba(model),dtype=np.uint8).reshape(h,w,4)
    with Image.open(authored) as im:
        if im.size != (w,h) or 'A' not in im.getbands():
            raise ValueError('PNG dimensions or alpha channel changed')
        authored_pixels = np.array(im.convert('RGBA'))
    if np.any(before[:,:,3] != authored_pixels[:,:,3]):
        raise ValueError('Original alpha mask must remain unchanged')
    visible_changes = np.any(before != authored_pixels,axis=2) & (before[:,:,3]>0)
    if np.any(visible_changes & ~mask):
        raise ValueError('Authored changes outside menu rectangles')
    compiled, check = compile_png(raw,authored)
    after = parse(compiled)
    changed = np.frombuffer(model['indices'],dtype=np.uint8) != np.frombuffer(after['indices'],dtype=np.uint8)
    if np.any(changed & ~mask.reshape(-1)):
        raise ValueError('Compiled changes outside menu rectangles')
    if np.any(np.frombuffer(preview_rgba(after),dtype=np.uint8).reshape(h,w,4)[:,:,3] != before[:,:,3]):
        raise ValueError('Compiled alpha mask changed')
    output.parent.mkdir(parents=True,exist_ok=True)
    (output.parent/'sys000.tm2').write_bytes(compiled)
    Image.frombytes('RGBA',(w,h),preview_rgba(after)).save(output.parent/'sys000.tm2.png')
    patches = [dict(offset=offset,data=compiled,expected_sha256=sha(raw))]
    title_config_path = ROOT/c['title_config']
    if file_hash(title_config_path) != c['title_config_sha256']:
        raise ValueError('Title configuration changed')
    titles = json.loads(title_config_path.read_text())
    if titles['base_iso_sha256'] != c['base_iso_sha256']:
        raise ValueError('Title and menu base ISOs differ')
    title_checks = []
    with source.open('rb') as fp:
        he = entries['DATA/DMAP.HED']; de = entries['DATA/DMAP.DAT']
        fp.seek(he['lba']*2048)
        ms = {e['path']:e for e in hed_tree(exact(fp,he['size']))[0]}
        for row in titles['assets']:
            png = ROOT/row['png']
            if file_hash(png) != row['png_sha256']:
                raise ValueError('User title PNG changed')
            e = ms[row['path']]; pos = de['lba']*2048+e['offset']
            fp.seek(pos); old = exact(fp,e['size'])
            if sha(old) != row['original_tim2_sha256']:
                raise ValueError('Original title changed')
            new, conversion = compile_png(old,png)
            if sha(new) != c['expected_title_hashes'][row['path']]:
                raise ValueError('Title differs from previously verified user build')
            name = row['path'].split('/')[-1]
            (output.parent/name).write_bytes(new)
            tm = parse(new)
            Image.frombytes('RGBA',(tm['width'],tm['height']),preview_rgba(tm)).save(output.parent/(name+'.png'))
            patches.append(dict(offset=pos,data=new,expected_sha256=sha(old)))
            title_checks.append(dict(path=row['path'],after_sha256=sha(new),
                matches_previous_user_title_build=True,conversion=conversion))
    iso = overlay(source,output,patches,c['base_iso_sha256'])
    if iso_inventory(output) != inv:
        raise ValueError('ISO metadata changed')
    diff = verify_overlay(source,output,patches,c['base_iso_sha256'],iso['output_sha256'])
    report = dict(base_iso=c['base_iso'],iso_path=c['output_iso'],iso=iso,entire_iso_diff=diff,
        png=c['png'],png_sha256=c['png_sha256'],before_sha256=sha(raw),after_sha256=sha(compiled),
        asset='status/sys000.tm2',iso_offset=offset,conversion=check,
        alpha_mask_preserved=True,all_bytes_outside_three_textures_preserved=True,iso_metadata_preserved=True,
        user_title_assets=title_checks,
        authored_image_reviewed=True,review=c['review'],runtime_verified=False,
        config_sha256=file_hash(config_path),tool_sha256=file_hash(ROOT/'tools/battle_menu_artwork.py'),
        compiler_sha256=file_hash(ROOT/'tools/title_artwork.py'))
    write_json(output.parent/'manifest.json',report)
    write_json(ROOT/'reports/battle_menu_artwork.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__ == '__main__':
    main()
