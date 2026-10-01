#!/usr/bin/env python3
"""Append lettered capture notices to v3; compile original indexed TIM2 assets.

No ISO writes. Font is supplied by the user and is never bundled.
"""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'build/python_psd'))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from battle_workbench_v3 import OUT, IMG, RAW, digest, piece, unpack, transform, artwork
from make_battle_lettering_work import layered_psd, LABEL
from ui_texture_codec import parse, preview_rgba, uad_rectangles, unpack_indices
from build_battle_conditions_psd import compile_texture

BUILD = ROOT/'build/capture_notice_euljiro_v1'
PREFIX = 'BATTLE/battle/catch/'


def layout(ident):
    source = PREFIX+ident+'.tm2'
    model = parse((RAW/source).read_bytes())
    assert (model['width'], model['height']) == (256,128) and model['bpp'] in (4,8)
    uad = uad_rectangles((RAW/source).with_suffix('.uad').read_bytes(),256,128)
    if ident == 'catch_cmn00':
        assert [(r['rect'],r['anchor']) for r in uad['rectangles']] == [([0,0,232,80],[116,40])]
        size = (928,320)
        pieces = [piece(source,(0,0,232,80),np.eye(3),(0,0,*size))]
    else:
        assert [(r['rect'],r['anchor']) for r in uad['rectangles']] == [([0,0,256,64],[256,32]),([0,64,256,64],[0,32])]
        size = (2048,256)
        pieces = [piece(source,(0,row*64,256,(row+1)*64),
                        [[1,0,0],[0,1,0],[row*1024,-row*256,1]],
                        (row*1024,0,(row+1)*1024,256)) for row in range(2)]
    return source,size,pieces,uad


def render(text,size,fontpath):
    # Native 2px dark outline. Font shrinks only if the full phrase exceeds
    # the safe rectangle; glyphs are never stretched independently.
    stroke=8;pad=16;w,h=size;fontsize=round(h*.93)
    while True:
        font=ImageFont.truetype(str(fontpath),fontsize)
        box=font.getbbox(text,stroke_width=stroke)
        if box[2]-box[0]<=w-2*pad and box[3]-box[1]<=h-2*pad:break
        fontsize-=1
        assert fontsize>40
    pos=((w-(box[2]-box[0]))//2-box[0],(h-(box[3]-box[1]))//2-box[1])
    outline=Image.new('RGBA',size);fill=Image.new('RGBA',size)
    ImageDraw.Draw(outline).text(pos,text,font=font,fill=(16,16,16,255),
                                stroke_width=stroke,stroke_fill=(16,16,16,255))
    # Match original palette's brightest gray, with fully opaque original GS
    # alpha 128. Inventing 255 white would require modifying the palette.
    ImageDraw.Draw(fill).text(pos,text,font=font,fill=(232,232,232,255))
    merged=Image.alpha_composite(outline,fill)
    bbox=merged.getchannel('A').getbbox()
    assert bbox and bbox[0]>=pad and bbox[1]>=pad and bbox[2]<=w-pad and bbox[3]<=h-pad
    return outline,fill,merged,dict(font_size_native=fontsize/4,stroke_native=2,bbox_4x=bbox)


def pack_art(im,spec,resample=Image.Resampling.LANCZOS):
    source=spec['pieces'][0]['source']
    target=Image.open(IMG/(source+'.png')).convert('RGBA')
    for p in spec['pieces']:
        clipped=Image.new('RGBA',im.size);box=tuple(p['clip'])
        clipped.paste(im.crop(box),box[:2])
        packed=transform(clipped,(1024,512),p['forward'])
        x,y,r,b=p['rect'];tile=packed.crop((x*4,y*4,r*4,b*4)).resize((r-x,b-y),resample)
        target.paste(tile,(x,y))
    return target


def main():
    config=json.loads((ROOT/'localization/capture_notice_euljiro.json').read_text())
    manifest_path=OUT/'manifest.json';manifest=json.loads(manifest_path.read_text())
    assert not manifest.get('capture_notice_extension') and not BUILD.exists(), 'Never overwrite prepared work'
    rows=config['rows'];fontpath=Path(config['font'])
    assert {r['id'] for r in rows}=={p.stem for p in (RAW/PREFIX).glob('*.tm2')}
    fontcheck=ImageFont.truetype(str(fontpath),96)
    missing=bytes(fontcheck.getmask(chr(0x10FFFF)))
    assert all(bytes(fontcheck.getmask(c))!=missing for r in rows for c in r['target'] if not c.isspace()), 'Font lacks a required glyph'
    previous={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*.psd')}
    for r in rows:assert not (OUT/f"14_포획알림_{r['id']}.psd").exists()
    BUILD.mkdir(parents=True)
    specs=[];reports=[];previews=[];copied=[]
    for r in rows:
        source,size,pieces,uad=layout(r['id'])
        spec=dict(id=r['id'],group='14_포획알림',name=r['target'],size=size,pieces=pieces,
                  original_text=r['source'],kind='capture_notice',base=r['id'],
                  psd=f"14_포획알림_{r['id']}.psd",has_existing_korean=True)
        native_original=Image.open(IMG/(source+'.png')).convert('RGBA')
        assert native_original.tobytes()==preview_rgba(parse((RAW/source).read_bytes()))
        original=unpack({source:native_original.resize((1024,512),Image.Resampling.NEAREST)},spec)
        outline,fill,merged,typography=render(r['target'],size,fontpath)
        layered_psd(OUT/spec['psd'],[
            ('원문_일본어_한줄복원_내보내기제외',original,False),
            ('한글_어두운테두리_을지로체',outline,True),
            ('한글_밝은글자_을지로체',fill,True)],merged)
        # Verify the same PSD reader/filter that future user edits will use.
        decoded=artwork(OUT/spec['psd']);a=np.array(decoded);b=np.array(merged)
        # psd-tools composites in float, Pillow uses integer rounding.
        assert np.max(np.abs(a.astype(int)-b.astype(int))[:,:,3])<=1
        assert np.max(np.abs(a[:,:,:3].astype(int)-b[:,:,:3].astype(int))[b[:,:,3]>0])<=1
        merged.save(OUT/f"14_포획알림_{r['id']}_한글.png")
        target=pack_art(decoded,spec)
        raw=(RAW/source).read_bytes();compiled,quality=compile_texture(raw,target)
        tm2=BUILD/'textures'/source;tm2.parent.mkdir(parents=True,exist_ok=True);tm2.write_bytes(compiled)
        png=BUILD/'atlas_png'/(source+'.png');png.parent.mkdir(parents=True,exist_ok=True);target.save(png)
        compiled_model=parse(compiled)
        preview=Image.frombytes('RGBA',(256,128),preview_rgba(compiled_model))
        preview.save(BUILD/(r['id']+'_packed_preview.png'))
        display=unpack({source:preview.resize((1024,512),Image.Resampling.NEAREST)},spec)
        previews.append((r,display))
        indices=np.frombuffer(unpack_indices(compiled_model),np.uint8)
        raw_palette=np.array([list(c) for c in compiled_model['palette']])
        authored=np.array(target).reshape(-1,4)
        brightest=(authored[:,3]==255)&np.all(authored[:,:3]==232,axis=1)
        assert brightest.sum()>0 and np.all(raw_palette[indices[brightest],3]==128)
        assert np.all(raw_palette[indices[brightest],:3]==232)
        # Original -> common coordinates -> stored rows, including the join.
        roundtrip=pack_art(original,spec,Image.Resampling.NEAREST)
        oa=np.array(native_original);ra=np.array(roundtrip)
        np.testing.assert_array_equal(ra[:,:,3],oa[:,:,3])
        np.testing.assert_array_equal(ra[:,:,:3][oa[:,:,3]>0],oa[:,:,:3][oa[:,:,3]>0])
        allowed=np.zeros((128,256),bool)
        for p in pieces:
            x,y,right,bottom=p['rect'];allowed[y:bottom,x:right]=True
        origidx=np.frombuffer(unpack_indices(parse(raw)),np.uint8).reshape(128,256)
        np.testing.assert_array_equal(indices.reshape(128,256)[~allowed],origidx[~allowed])
        for src,dest in [
            (RAW/source,OUT/'원본자료'/source),
            ((RAW/source).with_suffix('.uad'),(OUT/'원본자료'/source).with_suffix('.uad')),
            (IMG/(source+'.png'),OUT/'원본자료/atlas_png'/(source+'.png'))]:
            dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists():assert digest(src)==digest(dest)
            else:shutil.copy2(src,dest)
            copied.append(dict(path=str(dest.relative_to(OUT)),sha256=digest(dest)))
        spec.update(sha256=digest(OUT/spec['psd']),source_sha256=digest(RAW/source))
        specs.append(spec)
        reports.append(dict(**r,**typography,**quality,source_sha256=digest(RAW/source),
                            compiled_sha256=digest(tm2),uad=uad,
                            opaque_bright_pixels=int(brightest.sum()),raw_bright_alpha=128,
                            original_layout_roundtrip=True,psd_export_matches_render=True))
    label=ImageFont.truetype(str(LABEL),23)
    for start in range(0,len(previews),12):
        board=Image.new('RGB',(1120,880),(43,49,56));draw=ImageDraw.Draw(board)
        draw.text((20,14),'마신 포획 알림 · 을지로체 · 게임용 팔레트 변환 후',font=label,fill='white')
        for n,(r,im) in enumerate(previews[start:start+12]):
            x=16+(n%2)*552;y=64+(n//2)*133
            draw.text((x,y),r['id'],font=label,fill=(173,190,204))
            im=im.copy();im.thumbnail((520,90),Image.Resampling.LANCZOS)
            board.paste(im,(x+(520-im.width)//2,y+31),im)
        board.save(OUT/f'포획알림_을지로체_목록_{start//12+1:02}.jpg',quality=95)
    for name,sha in previous.items():assert digest(OUT/name)==sha, 'Existing user artwork changed'
    report=dict(font_path=str(fontpath),font_sha256=digest(fontpath),font_bundled=False,
                textures=len(rows),existing_psds_preserved=len(previous),rows=reports,
                iso_modified=False,runtime_verified=False,
                name_corrections=[r for r in rows if r.get('name_correction')],
                name_db_modified=False)
    (ROOT/'reports/capture_notice_euljiro_v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    manifest['documents'].extend(specs);manifest['raw_files'].extend(copied)
    manifest['source_textures']=sorted(set(manifest['source_textures'])|{p['source'] for s in specs for p in s['pieces']})
    manifest['psd_count']=len(manifest['documents']);manifest['source_texture_count']=len(manifest['source_textures'])
    manifest['capture_notice_extension']={k:v for k,v in report.items() if k!='rows'}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','name_corrections')},ensure_ascii=False))


if __name__=='__main__':main()
