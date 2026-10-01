#!/usr/bin/env python3
"""Import reviewed authored UI rectangles into the original indexed palette.

This is a texture compiler: preserve all source bytes outside the allowlist,
all CLUT entries, TIM2 headers, UAD coordinates, and the base ISO layout.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from localization_pipeline import ROOT, hed_tree, sha, file_hash, write_json
from iso_archive_stage import iso_inventory, exact, overlay, CHUNK
from ui_texture_codec import parse, serialize, preview_rgba, rect_indices, replace_rect, uad_rectangles


def compile_asset(raw, asset, author_image, uad=None):
    model=parse(raw)
    if model['source_sha256']!=asset['source_sha256']:raise ValueError('Source asset changed')
    if file_hash(author_image)!=asset['author_image_sha256']:raise ValueError('Authored image changed')
    if model['bpp']!=8:raise ValueError('This compiler imports only verified 8-bit linear textures')
    alpha_mode=asset.get('import_mode','opaque_rgb')
    if alpha_mode not in ('opaque_rgb','rgba_palette'):raise ValueError('Unknown import mode')
    def load_author(path):
        with Image.open(path) as source_image:
            if alpha_mode=='rgba_palette' and ('A' not in source_image.getbands() or source_image.getextrema()[-1][0]==255):
                raise ValueError('RGBA import requires authored transparency')
            return source_image.convert('RGBA' if alpha_mode=='rgba_palette' else 'RGB')
    im=load_author(author_image);width,height=model['width'],model['height']
    # The image service rounds output dimensions to pixels. Permit <=1 output
    # pixel of aspect rounding, never an arbitrary crop or changed composition.
    if abs(im.width*height-im.height*width)>max(width,height):raise ValueError('Author/source aspect ratios differ')
    if asset.get('uad_sha256'):
        if uad is None or sha(uad)!=asset['uad_sha256']:raise ValueError('UAD changed')
        uad=uad_rectangles(uad,width,height)
    palette=np.array([list(c[:3]) for c in model['palette']],dtype=np.int32)
    opaque=np.array([i for i,c in enumerate(model['palette']) if c[3]==128])
    out=raw;occupied=set();checks=[];ids=set()
    for r in asset['records']:
        if r['id'] in ids or r['status']!='reviewed' or not r['reviewer'] or not r['target']:
            raise ValueError('Unreviewed, empty or duplicate record')
        ids.add(r['id']);rect=r['rect'];x,y,w,h=rect;old=rect_indices(model,rect)
        if sha(old)!=r['source_rect_sha256']:raise ValueError('Source rectangle changed')
        if 'uad_index' in r and (uad is None or rect!=uad['rectangles'][r['uad_index']]['rect']):
            raise ValueError('Rectangle does not match UAD')
        positions={yy*width+xx for yy in range(y,y+h) for xx in range(x,x+w)}
        if occupied & positions:raise ValueError('Overlapping authored rectangles')
        occupied.update(positions)
        if alpha_mode=='opaque_rgb' and any(model['palette'][i][3]!=128 for i in old):raise ValueError('Import requires an opaque source rectangle')
        # Normalize the generated asset to the game's fixed sampling coordinates.
        selected_image=im
        if 'author_image' in r:
            override=ROOT/r['author_image']
            if file_hash(override)!=r['author_image_sha256']:raise ValueError('Authored override changed')
            selected_image=load_author(override)
            if abs(selected_image.width*height-selected_image.height*width)>max(width,height):
                raise ValueError('Author override aspect differs')
        sx,sy=selected_image.width/width,selected_image.height/height
        ax,ay,aw,ah=r.get('author_rect',rect)
        rect_indices(model,[ax,ay,aw,ah])  # also bounds-check the authored source tile
        if (aw,ah)!=(w,h):raise ValueError('Authored tile dimensions differ')
        tile=selected_image.transform((w,h),Image.EXTENT,(ax*sx,ay*sy,(ax+aw)*sx,(ay+ah)*sy),resample=Image.BICUBIC)
        if alpha_mode=='rgba_palette':
            # Compare premultiplied displayed colors plus alpha. Transparent RGB
            # is invisible; its arbitrary color must not win over actual alpha.
            def premultiplied(values):
                v=np.asarray(values,dtype=np.int32).copy()
                v[:,:3]=(v[:,:3]*v[:,3:4]+127)//255
                return v
            colors=[list(c[:3])+[min(255,c[3]*2)] for c in model['palette']]
            target=premultiplied(np.asarray(tile).reshape(-1,4));pal=premultiplied(colors)
            d=((target[:,None,:]-pal[None,:,:])**2).sum(axis=2)
            ix=d.argmin(axis=1).astype(np.uint8)
        else:
            rgb=np.asarray(tile,dtype=np.int32).reshape(-1,3)
            d=((rgb[:,None,:]-palette[opaque][None,:,:])**2).sum(axis=2)
            ix=opaque[d.argmin(axis=1)].astype(np.uint8)
        errors=d.min(axis=1)
        out=replace_rect(out,rect,ix.tobytes(),sha(out),sha(old))
        checks.append(dict(id=r['id'],target=r['target'],rect=rect,
                           mean_rgb_squared_error=float(errors.mean()),max_rgb_squared_error=int(errors.max())))
    after=parse(out)
    if after['header']!=model['header'] or after['palette']!=model['palette']:raise ValueError('Header/palette changed')
    changed={i for i,(a,b) in enumerate(zip(model['indices'],after['indices'])) if a!=b}
    if not changed or not changed<=occupied:raise ValueError('Empty or out-of-rectangle patch')
    return out,dict(before_sha256=sha(raw),after_sha256=sha(out),bytes=len(out),changed_index_bytes=len(changed),
                    allowed_pixels=len(occupied),outside_rectangles_preserved=True,raw_palette_preserved=True,
                    header_preserved=True,records=checks)


def verify_overlay(source,output,patches,source_hash,output_hash):
    changes={}
    with source.open('rb') as f:
        for p in patches:
            f.seek(p['offset']);old=exact(f,len(p['data']))
            if sha(old)!=p['expected_sha256']:raise ValueError('Wrong source range')
            changes.update((p['offset']+i,(a,b)) for i,(a,b) in enumerate(zip(old,p['data'])) if a!=b)
    count=len(changes);hs=hashlib.sha256();ho=hashlib.sha256();pos=0
    with source.open('rb') as a,output.open('rb') as b:
        while True:
            old=a.read(CHUNK)
            if not old:break
            new=exact(b,len(old));hs.update(old);ho.update(new)
            if old!=new:
                for i,(x,y) in enumerate(zip(old,new)):
                    if x!=y and changes.pop(pos+i,None)!=(x,y):raise ValueError('Unplanned ISO byte')
            pos+=len(old)
        if b.read(1):raise ValueError('Trailing ISO bytes')
    if changes or hs.hexdigest()!=source_hash or ho.hexdigest()!=output_hash:raise ValueError('ISO hash mismatch')
    return dict(passed=True,changed_bytes=count)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',default='build/ui_slice');p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    out=(ROOT/a.output_dir).resolve()
    if (ROOT/'build').resolve() not in out.parents:raise ValueError('Output must be below build/')
    output=out/'Poison Pink (Japan) - UI slice.iso'
    if output.exists() or (out/'manifest.json').exists():raise ValueError('Refusing completed build overwrite')
    review_path=ROOT/'localization/ui_slice.json';review=json.loads(review_path.read_text());source=ROOT/review['base_iso']
    inv=iso_inventory(source);entries={e['path']:e for e in inv['files']};patches=[];checks=[]
    out.mkdir(parents=True,exist_ok=True)
    with source.open('rb') as fp:
        for asset in review['assets']:
            hed=entries['DATA/'+asset['archive']+'.HED'];dat=entries['DATA/'+asset['archive']+'.DAT']
            fp.seek(hed['lba']*2048);members,_=hed_tree(exact(fp,hed['size']));members={e['path']:e for e in members}
            e=members[asset['path']];off=dat['lba']*2048+e['offset'];fp.seek(off);raw=exact(fp,e['size'])
            uad=None
            if asset.get('uad_sha256'):
                ue=members[asset['path'][:-4]+'.uad'];fp.seek(dat['lba']*2048+ue['offset']);uad=exact(fp,ue['size'])
            modified,check=compile_asset(raw,asset,ROOT/asset['author_image'],uad)
            target=out/e['name'];target.write_bytes(modified);m=parse(modified)
            Image.frombytes('RGBA',(m['width'],m['height']),preview_rgba(m)).save(out/(e['name']+'.png'))
            patches.append(dict(offset=off,data=modified,expected_sha256=sha(raw)))
            checks.append(dict(path=asset['path'],iso_offset=off,**check))
    report=dict(schema_version=1,review_sha256=file_hash(review_path),base_iso_sha256=review['base_iso_sha256'],
                assets=checks,asset_count=len(checks),runtime_verified=False,
                preserved=['UAD files','TIM2 headers and raw palettes','all pixels outside approved rectangles',
                           'all DB numeric/text fields','tutorial RTB translations','font and glyph mapping','ISO extents and sizes'])
    if a.prepare_only:
        write_json(out/'prepare.json',report);print('Prepared:',len(checks),'assets');return
    result=overlay(source,output,patches,review['base_iso_sha256'])
    report['iso']=result;report['iso_path']=str(output.relative_to(ROOT))
    report['entire_iso_diff']=verify_overlay(source,output,patches,review['base_iso_sha256'],result['output_sha256'])
    write_json(out/'manifest.json',report);write_json(ROOT/'reports/ui_slice.json',report)
    print('Built:',report['iso_path'],result['output_sha256'])


if __name__=='__main__':main()
