#!/usr/bin/env python3
"""Render/review 14 tutorial help pages and overlay only approved text rectangles."""
import argparse
import io
import json
import re
import unicodedata
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,__version__ as PIL_VERSION
from localization_pipeline import ROOT,sha,file_hash,hed_tree,write_json
from iso_archive_stage import iso_inventory,exact,overlay
from ui_texture_codec import parse,preview_rgba,rect_indices
from ui_slice import compile_asset,verify_overlay


def number_tokens(text):
    return re.findall(r'\d+',unicodedata.normalize('NFKC',text))


def clean_text(tile,mode):
    """Bounded harmonic fill of the old lettering; no inference outside this tile."""
    rgb=np.asarray(tile.convert('RGB'),dtype=np.float32)
    if mode=='title':
        # Titles occupy a blue band with clear side margins. Interpolate
        # their median colors; lettering cannot become a fill anchor.
        left=np.median(rgb[4:-4,:2],axis=(0,1))
        right=np.median(rgb[4:-4,-2:],axis=(0,1))
        t=np.linspace(0,1,tile.width,dtype=np.float32)[None,:,None]
        filled=np.repeat(left*(1-t)+right*t,tile.height,axis=0)
        result=Image.fromarray(filled.round().astype('uint8'),'RGB').convert('RGBA')
        result.putalpha(tile.getchannel('A'))
        return result,dict(method='side_margin_gradient',pixels=tile.width*tile.height)
    red,green,blue=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
    if mode=='dark':mask=rgb.max(axis=2)<110
    else:
        white=(rgb.min(axis=2)>185)&((rgb.max(axis=2)-rgb.min(axis=2))<70)
        gold=(red>180)&(green>120)&(red>blue*1.25)
        scarlet=(red>180)&(red>green*1.7)&(red>blue*1.7)
        cyan=(green>125)&(blue>140)&(red>65)
        mask=white|gold|scarlet
        if mode=='cyan':mask|=cyan
    mask=np.asarray(Image.fromarray(mask.astype('uint8')*255).filter(ImageFilter.MaxFilter(15)))>0
    # The input rectangle includes margins around the source text. Boundary
    # samples anchor the fill and retain the surrounding picture's colors.
    mask[:1]=False;mask[-1:]=False;mask[:,:1]=False;mask[:,-1:]=False
    if not mask.any() or mask.mean()>.96:raise ValueError('Invalid text-cleanup mask')
    filled=rgb.copy();filled[mask]=rgb[~mask].mean(axis=0)
    for _ in range(800):
        pad=np.pad(filled,((1,1),(1,1),(0,0)),mode='edge')
        neighbors=(pad[:-2,1:-1]+pad[2:,1:-1]+pad[1:-1,:-2]+pad[1:-1,2:])*.25
        filled[mask]=neighbors[mask]
    result=Image.fromarray(np.clip(filled,0,255).round().astype('uint8'),'RGB').convert('RGBA')
    result.putalpha(tile.getchannel('A'))
    return result,dict(mask_pixels=int(mask.sum()),pixels=mask.size)


def render(raw,asset,font_path):
    model=parse(raw)
    if sha(raw)!=asset['source_sha256']:raise ValueError('Source page changed')
    original=Image.frombytes('RGBA',(model['width'],model['height']),preview_rgba(model));out=original.copy()
    occupied=set();checks=[]
    for r in asset['records']:
        if r['status']!='reviewed' or not r['reviewer'] or not r['target']:raise ValueError('Unreviewed text')
        if unicodedata.normalize('NFC',r['target'])!=r['target']:raise ValueError('Target must be NFC')
        if number_tokens(r['source'])!=number_tokens(r['target']):raise ValueError('Numeric tokens changed')
        x,y,w,h=r['rect'];old=rect_indices(model,r['rect'])
        if sha(old)!=r['source_rect_sha256']:raise ValueError('Source rectangle changed')
        points={yy*model['width']+xx for yy in range(y,y+h) for xx in range(x,x+w)}
        if occupied & points:raise ValueError('Overlapping help rectangles: '+r['id'])
        occupied.update(points)
        tile,cleanup=clean_text(original.crop((x,y,x+w,y+h)),r.get('ink','light'))
        scale=4;layer=Image.new('RGBA',(w*scale,h*scale));draw=ImageDraw.Draw(layer)
        font=ImageFont.truetype(str(font_path),r['font_size']*scale);stroke=r.get('stroke',1)*scale
        spacing=r.get('line_spacing',3)*scale
        box=draw.multiline_textbbox((0,0),r['target'],font=font,spacing=spacing,stroke_width=stroke,align=r.get('align','center'))
        tw,th=box[2]-box[0],box[3]-box[1]
        if tw>(w-4)*scale or th>(h-4)*scale:raise ValueError('Text does not fit: '+r['id']+' '+str((tw/scale,th/scale,w,h)))
        left=2*scale if r.get('align')=='left' else (w*scale-tw)//2;top=(h*scale-th)//2
        fill=tuple(r.get('fill',[255,255,255,255]));outline=(0,0,0,255) if r.get('ink')!='dark' else fill
        draw.multiline_text((left-box[0],top-box[1]),r['target'],font=font,spacing=spacing,fill=fill,
            stroke_width=stroke,stroke_fill=outline,align=r.get('align','center'))
        tile=Image.alpha_composite(tile,layer.resize((w,h),Image.LANCZOS));out.paste(tile,(x,y))
        checks.append(dict(id=r['id'],source=r['source'],target=r['target'],glyph_box=[left/scale,top/scale,tw/scale,th/scale],cleanup=cleanup))
    return out,checks


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-dir',default='build/help_pages');ap.add_argument('--build',action='store_true');a=ap.parse_args()
    out=(ROOT/a.output_dir).resolve();rp=ROOT/'localization/help_pages.json';review=json.loads(rp.read_text())
    if (ROOT/'build').resolve() not in out.parents:raise ValueError('Output outside build/')
    output=out/'Poison Pink (Japan) - tutorial help.iso'
    if output.exists() or (out/'manifest.json').exists():raise ValueError('Refusing completed build overwrite')
    source=ROOT/review['base_iso'];font=Path(review['font_path'])
    if file_hash(font)!=review['font_sha256'] or file_hash(source)!=review['base_iso_sha256']:raise ValueError('Input changed')
    out.mkdir(parents=True,exist_ok=True);inv=iso_inventory(source);entries={e['path']:e for e in inv['files']}
    patches=[];checks=[];render_checks=[]
    with source.open('rb') as fp:
        hed=entries['DATA/DMAP.HED'];dat=entries['DATA/DMAP.DAT'];fp.seek(hed['lba']*2048)
        members,_=hed_tree(exact(fp,hed['size']));members={e['path']:e for e in members}
        for asset in review['assets']:
            e=members[asset['path']];pos=dat['lba']*2048+e['offset'];fp.seek(pos);raw=exact(fp,e['size'])
            author,rc=render(raw,asset,font);name=Path(asset['path']).name;path=out/(name+'.authored.png')
            png=io.BytesIO();author.save(png,format='PNG');encoded=png.getvalue()
            if path.exists() and path.read_bytes()!=encoded:raise ValueError('Different authored PNG exists')
            if not path.exists():path.write_bytes(encoded)
            compiled_asset=dict(asset,author_image_sha256=file_hash(path))
            changed,check=compile_asset(raw,compiled_asset,path)
            (out/name).write_bytes(changed);m=parse(changed)
            Image.frombytes('RGBA',(m['width'],m['height']),preview_rgba(m)).save(out/(name+'.png'))
            patches.append(dict(offset=pos,data=changed,expected_sha256=sha(raw)))
            checks.append(dict(path=asset['path'],author_image=str(path.relative_to(ROOT)),author_sha256=file_hash(path),**check))
            render_checks.append(dict(path=asset['path'],records=rc))
    report=dict(schema_version=1,review_sha256=file_hash(rp),base_iso=review['base_iso'],base_iso_sha256=review['base_iso_sha256'],
        iso_path=str(output.relative_to(ROOT)),assets=checks,render=render_checks,pillow_version=PIL_VERSION,font_sha256=review['font_sha256'],
        font_elf_rtb_db_preserved=True,iso_metadata_preserved=True,runtime_verified=False)
    if a.build:
        iso=overlay(source,output,patches,review['base_iso_sha256'])
        if iso_inventory(output)!=inv:raise ValueError('ISO metadata changed')
        report.update(iso=iso,entire_iso_diff=verify_overlay(source,output,patches,review['base_iso_sha256'],iso['output_sha256']))
        write_json(out/'manifest.json',report);write_json(ROOT/'reports/help_pages.json',report)
    else:write_json(out/'prepare.json',report)
    print(json.dumps(dict(pages=len(checks),rectangles=sum(len(c['records']) for c in checks),output=str(out)),ensure_ascii=False))


if __name__=='__main__':main()
