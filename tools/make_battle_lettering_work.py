#!/usr/bin/env python3
"""Authoring kit only: layered Korean draft masters, source archive, mapping."""
import io, json, shutil, struct, sys, zipfile
from pathlib import Path
from html import escape
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from localization_pipeline import ROOT, file_hash, write_json
from ui_texture_codec import parse, uad_rectangles

OUT=ROOT/'outputs/battle_lettering_work_v1'
FONT=Path('/Library/Fonts/NanumGothicExtraBold.ttf')
LABEL=Path('/Library/Fonts/NanumGothic.ttf')
B='DMAP/dmap/map/bstart/'
S='STATUS/status/'
def bt(n):return B+f'bt_tx{n:02d}.tm2'
ROWS=[
 ('01_승리조건','승리 조건','勝利条件',[128,40],[bt(4)],None,'conditions'),
 ('02_패배조건','패배 조건','敗北条件',[128,40],[bt(4)],None,'conditions'),
 ('03_모든적격파','모든 적을\n격파하라','全ての敵を撃破せよ',[256,128],[bt(n) for n in range(5,9)],None,'conditions'),
 ('04_주인공전투불능','주인공 전투불능','主人公の戦闘不能',[256,64],[bt(n) for n in range(9,13)],None,'conditions'),
 ('05_루나셰격파','루나셰를\n격파하라','ルナーシェを撃破せよ',[256,128],[bt(n) for n in range(13,17)],None,'conditions'),
 ('06_테이지전투불능','테이지 전투불능','テージの戦闘不能',[256,64],[bt(n) for n in range(17,21)],None,'conditions'),
 ('07_보스격파','보스를\n격파하라','ボスを撃破せよ',[256,128],[bt(n) for n in range(21,25)],None,'conditions'),
 ('08_발드왕격파','발드 왕을\n격파하라','バルド王を撃破せよ',[256,128],[bt(n) for n in range(25,29)],None,'conditions'),
 ('09_오버킬','오버킬','OVERKILL',[256,48],[S+'sys013.tm2'],[248,0,264,48],'capture'),
 ('10_구속','구속','拘束 / BIND',[200,104],[S+'sys031.tm2',S+'sys032.tm2'],[0,120,200,104],'capture'),
 ('11_포획','포획','CAPTURE',[120,24],[S+'sys018.tm2'],[0,0,120,24],'capture'),
]

def pack(fmt,*a):return struct.pack('>'+fmt,*a)
def layered_psd(path,layers,merged):
    """Minimal PSD v1: straight RGBA raster layers, Unicode names, raw channels.
    Adobe specification: https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/
    Layers supplied bottom to top; hidden layers have flags bit 1 set.
    """
    w,h=merged.size;records=[];payload=[]
    for i,(name,im,visible) in enumerate(layers):
        assert im.mode=='RGBA' and im.size==(w,h)
        a=np.array(im);channels=[pack('H',0)+a[:,:,j].tobytes() for j in range(4)]
        info=b''.join(pack('hI',cid,len(c)) for cid,c in zip([0,1,2,-1],channels))
        ascii_name=f'Layer {i+1}'.encode();pascal=bytes([len(ascii_name)])+ascii_name
        pascal+=b'\0'*((-len(pascal))%4)
        un=name.encode('utf-16be');luni=pack('I',len(un)//2)+un
        extra=pack('II',0,0)+pascal+b'8BIMluni'+pack('I',len(luni))+luni
        extra+=b'\0'*(len(luni)%2)
        records.append(pack('iiiiH',0,0,h,w,4)+info+b'8BIMnorm'+bytes([255,0,0 if visible else 2,0])+pack('I',len(extra))+extra)
        payload.extend(channels)
    data=pack('h',-len(layers))+b''.join(records)+b''.join(payload)
    data+=b'\0'*(len(data)%2)
    lm=pack('I',len(data))+data+pack('I',0)
    # Photoshop saved merged RGB is associated with white; layer RGBA is straight.
    a=np.array(merged,dtype=np.uint32);alpha=a[:,:,3:4]
    a[:,:,:3]=(a[:,:,:3]*alpha+255*(255-alpha)+127)//255
    a=a.astype(np.uint8)
    composite=pack('H',0)+b''.join(a[:,:,j].tobytes() for j in range(4))
    raw=b'8BPS'+pack('H',1)+bytes(6)+pack('HIIHH',4,h,w,8,3)+pack('II',0,0)+pack('I',len(lm))+lm+composite
    path.write_bytes(raw)
    with Image.open(path) as check:
        assert check.size==(w,h) and check.mode=='RGBA'
        np.testing.assert_array_equal(np.array(check),a)
        assert check.n_frames==len(layers)
        # This bundled Pillow parses layer tiles from BytesIO but leaves their
        # offsets relative to that buffer. Rebase for its file-backed decoder.
        check.layers=[(n,m,b,[t._replace(offset=t.offset+check._layers_position) for t in tiles])
                      for n,m,b,tiles in check.layers]
        # Independent Pillow PSD layer decoder verifies every plane and ordering.
        # Pillow initially labels the merged image frame 1; move away first.
        check.seek(2)
        for j,(_,im,_) in enumerate(layers,1):
            check.seek(j)
            np.testing.assert_array_equal(np.array(check.convert('RGBA')),np.array(im))

def checker(size):
    im=Image.new('RGBA',size,(32,39,48,255));d=ImageDraw.Draw(im)
    for y in range(0,size[1],24):
        for x in range(0,size[0],24):
            if (x//24+y//24)%2:d.rectangle((x,y,x+23,y+23),fill=(43,51,61,255))
    return im

def render(text,size,accent):
    w,h=size;lines=text.split('\n');pad=max(6,round(h*.04));font_size=int(h*.85/len(lines))
    while True:
        font=ImageFont.truetype(str(FONT),font_size)
        boxes=[font.getbbox(s) for s in lines];heights=[b[3]-b[1] for b in boxes]
        gap=max(8,round(font_size*.24))
        if max(b[2]-b[0] for b in boxes)<w-2*pad-16 and sum(heights)+gap*(len(lines)-1)<h-2*pad-16:break
        font_size-=1
        assert font_size>10
    mask=Image.new('L',size,0);d=ImageDraw.Draw(mask);y=(h-sum(heights)-gap*(len(lines)-1))//2;positions=[]
    for s,b,ht in zip(lines,boxes,heights):
        x=(w-(b[2]-b[0]))//2-b[0];yy=y-b[1]
        d.text((x,yy),s,font=font,fill=255);positions.append([s,x,yy+font.getmetrics()[0]])
        y+=ht+gap
    inner=mask.filter(ImageFilter.MaxFilter(9));outer=mask.filter(ImageFilter.MaxFilter(17))
    def colored(color,alpha):
        im=Image.new('RGBA',size,(*color,0));im.putalpha(alpha);return im
    fill=colored((255,255,255),mask)
    dark=colored((24,14,24),ImageChops.subtract(inner,mask))
    border=colored(accent,ImageChops.subtract(outer,inner))
    glow=colored(accent,outer.filter(ImageFilter.GaussianBlur(10)).point(lambda v:round(v*.65)))
    merged=Image.alpha_composite(Image.alpha_composite(border,dark),fill)
    assert merged.getchannel('A').getextrema()==(0,255)
    return fill,dark,border,glow,merged,font_size,positions

def main():
    assert not (OUT/'manifest.json').exists(),'Version already complete'
    OUT.mkdir(parents=True,exist_ok=True)
    for sub in ['01_승리패배조건','02_마신포획','03_원본보관','04_검수']:(OUT/sub).mkdir(exist_ok=True)
    manifest=[];all_sources={};previews={'conditions':[],'capture':[]}
    for name,text,source,native,paths,crop,group in ROWS:
        folder=OUT/('01_승리패배조건' if group=='conditions' else '02_마신포획')
        size=tuple(n*4 for n in native)
        accent=(232,179,75) if group=='conditions' else ((233,75,112) if name.startswith('10') else (187,109,240))
        fill,dark,border,glow,merged,font_size,positions=render(text,size,accent)
        ref=Image.open(ROOT/'extracted/original/images'/ (paths[0]+'.png')).convert('RGBA')
        if crop:
            x,y,w,h=crop;ref=ref.crop((x,y,x+w,y+h))
        ref.thumbnail(size,Image.Resampling.NEAREST)
        reference=Image.new('RGBA',size);reference.alpha_composite(ref,((size[0]-ref.width)//2,(size[1]-ref.height)//2))
        layers=[('참고_체크배경_내보낼때끔',checker(size),False),('참고_일본어원본_끔',reference,False),
                ('선택_발광효과_끔',glow,False),('테두리_색상',border,True),('테두리_검정',dark,True),('한글초안_흰색_픽셀레이어',fill,True)]
        psd=folder/(name+'.psd');layered_psd(psd,layers,merged)
        merged.save(folder/(name+'_4배_투명.png'))
        merged.resize(tuple(native),Image.Resampling.LANCZOS).save(folder/(name+'_원배율_참고.png'))
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{size[0]}" height="{size[1]}" viewBox="0 0 {size[0]} {size[1]}">',
             '<title>한글 식자 초안 — 글자 수정용, 게임 조각 배치 전</title>']
        for color,stroke in [(f'rgb{accent}',16),('#180e18',8),('#ffffff',0)]:
            svg.append(f'<g font-family="NanumGothic, 나눔고딕" font-weight="800" font-size="{font_size}" fill="{color}" stroke="{color}" stroke-width="{stroke}" stroke-linejoin="round">')
            for line,x,y in positions:svg.append(f'<text x="{x}" y="{y}">{escape(line)}</text>')
            svg.append('</g>')
        svg.append('</svg>');(folder/(name+'_문구편집.svg')).write_text('\n'.join(svg))
        for path in paths:
            if path in all_sources:continue
            records={}
            for kind,ext in [('images','.png'),('raw','')]:
                src=ROOT/'extracted/original'/kind/(path+ext)
                dest=OUT/'03_원본보관'/kind/(path+ext);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
                assert file_hash(src)==file_hash(dest);records[kind]=dict(path=str(dest.relative_to(OUT)),sha256=file_hash(src))
            rawpath=ROOT/'extracted/original/raw'/path;model=parse(rawpath.read_bytes())
            records['size']=[model['width'],model['height']]
            records['raw_palette_rgba_hex']=[c.hex() for c in model['palette']]
            uad=rawpath.with_suffix('.uad')
            if uad.exists():
                dest=OUT/'03_원본보관/raw'/Path(path).with_suffix('.uad');shutil.copy2(uad,dest)
                records['uad']=uad_rectangles(uad.read_bytes(),model['width'],model['height'])
            all_sources[path]=records
        row=dict(name=name,korean_draft=text,japanese_or_english=source,group=group,logical_native_size=native,
                 work_size=list(size),scale=4,sources=paths,reference_crop=crop,psd=str(psd.relative_to(OUT)),
                 psd_sha256=file_hash(psd),psd_layers=6,text_layer_type='raster; SVG text and TXT also supplied',
                 placement_status='logical authoring canvas; atlas/UV/effect packing not performed',runtime_verified=False)
        manifest.append(row);previews[group].append((row,merged))
    # Preserve model/animation files needed to locate title character UVs later.
    for src in (ROOT/'extracted/original/raw'/B).iterdir():
        if src.suffix in ('.upm','.upl','.ups'):
            dst=OUT/'03_원본보관/raw'/B/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    for group,rows in previews.items():
        board=Image.new('RGB',(1200,100+len(rows)*230),(19,25,33));d=ImageDraw.Draw(board)
        f=ImageFont.truetype(str(LABEL),25)
        d.text((30,20),'승리·패배 조건 식자 초안' if group=='conditions' else '마신 포획 연출 식자 초안',font=ImageFont.truetype(str(FONT),34),fill='white')
        for i,(row,im) in enumerate(rows):
            y=100+i*230;d.text((30,y),row['name']+'  ·  '+Path(row['sources'][0]).name,font=f,fill=(196,205,218))
            tile=checker((1140,170));art=im.copy();art.thumbnail((1080,150),Image.Resampling.LANCZOS)
            tile.alpha_composite(art,((1140-art.width)//2,(170-art.height)//2));board.paste(tile.convert('RGB'),(30,y+40))
        board.save(OUT/('승리패배조건_한눈에보기.jpg' if group=='conditions' else '마신포획_한눈에보기.jpg'),quality=94)
    (OUT/'문구목록.txt').write_text('\n\n'.join(r['name']+'\n'+r['korean_draft'] for r in manifest)+'\n')
    write_json(OUT/'manifest.json',dict(format='battle_lettering_work_v1',authoring_only=True,iso_modified=False,
        font=str(FONT),font_sha256=file_hash(FONT),assets=manifest,sources=all_sources,
        psd_spec='https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/',
        validation=dict(psd_merged_and_all_66_layers_roundtrip=True,source_copies_hash_identical=True,transparent_pngs_have_opaque_core=True)))
    print(json.dumps(dict(output=str(OUT),masters=len(manifest),source_textures=len(all_sources)),ensure_ascii=False))

if __name__=='__main__':main()
