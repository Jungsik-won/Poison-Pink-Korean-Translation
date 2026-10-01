#!/usr/bin/env python3
"""Render reviewed Korean UI text from a pinned font into native atlas rectangles.

User explicitly selected Python font rendering for this stage. These PNGs feed
the existing palette/rectangle compiler; no generated or flattened alpha input.
"""
import argparse
import io
import json
import unicodedata
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,__version__ as PIL_VERSION
from localization_pipeline import ROOT,file_hash,sha,hed_tree,write_json
from iso_archive_stage import iso_inventory,exact
from ui_texture_codec import parse,preview_rgba,rect_indices,uad_rectangles


def render_asset(raw,asset,font_path):
    m=parse(raw)
    if sha(raw)!=asset['source_sha256']:raise ValueError('Source texture changed')
    canvas=Image.frombytes('RGBA',(m['width'],m['height']),preview_rgba(m));source=canvas.copy()
    checks=[];occupied=set()
    for r in asset['records']:
        rect=r['rect'];x,y,w,h=rect
        if sha(rect_indices(m,rect))!=r['source_rect_sha256']:raise ValueError('Source rectangle changed')
        if r['status']!='reviewed' or not r['reviewer'] or not r['target'] or unicodedata.normalize('NFC',r['target'])!=r['target']:
            raise ValueError('Unreviewed/empty/non-NFC text')
        points={(xx,yy) for yy in range(y,y+h) for xx in range(x,x+w)}
        if points & occupied:raise ValueError('Overlapping rectangles')
        occupied.update(points);style=r['render'];bg=style['background']
        if bg['mode']=='transparent':tile=Image.new('RGBA',(w,h),(0,0,0,0))
        elif bg['mode']=='source_rect':
            bx,by,bw,bh=bg['rect'];rect_indices(m,bg['rect'])
            if (bw,bh)!=(w,h):raise ValueError('Background dimensions differ')
            tile=source.crop((bx,by,bx+bw,by+bh))
        elif bg['mode']=='clear_interior':
            tile=source.crop((x,y,x+w,y+h));margin=bg['margin']
            if margin<1 or margin*2>=min(w,h):raise ValueError('Invalid clear margin')
            ImageDraw.Draw(tile).rectangle((margin,margin,w-margin-1,h-margin-1),fill=tuple(bg['rgba']))
        else:raise ValueError('Unknown background mode')
        scale=4;layer=Image.new('RGBA',(w*scale,h*scale),(0,0,0,0));draw=ImageDraw.Draw(layer)
        size=style['font_size'];font=ImageFont.truetype(str(font_path),size*scale)
        stroke=style['stroke_width']*scale
        box=draw.textbbox((0,0),r['target'],font=font,stroke_width=stroke)
        tw,th=box[2]-box[0],box[3]-box[1]
        pad=style['padding']*scale
        right_pad=2*scale if style['align']=='left' else pad
        if tw>w*scale-pad-right_pad or th>h*scale-4*scale:raise ValueError('Rendered text exceeds safe bounds: '+r['id'])
        left=pad if style['align']=='left' else (w*scale-tw)//2
        top=(h*scale-th)//2
        draw.text((left-box[0],top-box[1]),r['target'],font=font,fill=tuple(style['fill']),
                  stroke_width=stroke,stroke_fill=tuple(style['stroke_fill']))
        layer=layer.resize((w,h),Image.LANCZOS);tile=Image.alpha_composite(tile,layer)
        canvas.paste(tile,(x,y))
        checks.append(dict(id=r['id'],target=r['target'],glyph_box=[left/scale,top/scale,tw/scale,th/scale],
                           rgba_sha256=sha(tile.tobytes()),alpha_extrema=tile.getchannel('A').getextrema()))
    return canvas,checks


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--review',default='localization/ui_remaining.json');args=ap.parse_args()
    rp=(ROOT/args.review).resolve()
    if (ROOT/'localization').resolve() not in rp.parents:raise ValueError('Review path outside localization')
    review=json.loads(rp.read_text());font=Path(review['artwork_font'])
    if file_hash(font)!=review['artwork_font_sha256']:raise ValueError('Artwork font changed')
    iso=ROOT/review['base_iso']
    if file_hash(iso)!=review['base_iso_sha256']:raise ValueError('Base ISO changed')
    entries={e['path']:e for e in iso_inventory(iso)['files']};checks=[]
    with iso.open('rb') as fp:
        for asset in review['assets']:
            h=entries['DATA/'+asset['archive']+'.HED'];d=entries['DATA/'+asset['archive']+'.DAT']
            fp.seek(h['lba']*2048);members,_=hed_tree(exact(fp,h['size']));members={m['path']:m for m in members}
            def read_member(path):
                e=members[path];fp.seek(d['lba']*2048+e['offset']);return exact(fp,e['size'])
            raw=read_member(asset['path']);uad=read_member(asset['uad_path']);m=parse(raw)
            if sha(uad)!=asset['uad_sha256']:raise ValueError('UAD changed')
            rectangles=uad_rectangles(uad,m['width'],m['height'])['rectangles']
            for row in asset['records']:
                if row['rect']!=rectangles[row['uad_index']]['rect']:raise ValueError('UAD rectangle mismatch')
            im,records=render_asset(raw,asset,font);path=(ROOT/asset['author_image']).resolve()
            if (ROOT/'build').resolve() not in path.parents:raise ValueError('Artwork must be below build/')
            encoded=io.BytesIO();im.save(encoded,format='PNG');png=encoded.getvalue()
            if path.exists() and path.read_bytes()!=png:raise ValueError('Refusing different authored PNG overwrite')
            path.parent.mkdir(parents=True,exist_ok=True)
            if not path.exists():path.write_bytes(png)
            asset['author_image_sha256']=file_hash(path)
            checks.append(dict(path=asset['author_image'],sha256=asset['author_image_sha256'],records=records))
    review['artwork_provenance']=dict(mode='Python/Pillow pinned-font renderer, explicitly requested by user',
        pillow_version=PIL_VERSION,font_sha256=review['artwork_font_sha256'],assets=checks)
    write_json(rp,review)
    print(json.dumps(checks,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
