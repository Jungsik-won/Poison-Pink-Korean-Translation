#!/usr/bin/env python3
"""Preserve every original lettering variant; no invented animation states."""
import json,shutil,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from localization_pipeline import ROOT,file_hash,write_json
from make_battle_lettering_work import layered_psd,ROWS,LABEL,bt,S

OUT=ROOT/'outputs/battle_lettering_work_v2'

def main():
    assert not (OUT/'manifest.json').exists()
    OUT.mkdir(parents=True,exist_ok=True)
    groups=[('01_승리패배_제목','승리 조건 / 패배 조건',[bt(4)],'한 장 안에 제목과 반복 효과 조각이 함께 있음')]
    for name,text,_,_,paths,_,group in ROWS[2:8]:
        groups.append((name,text.replace('\n',' '),paths,'파일 번호는 재생 순서가 아님; 원본의 네 형태를 모두 편집'))
    groups.extend([
        ('09_오버킬','오버킬',[S+'sys013.tm2'],'회전된 O/K와 나머지 글자 조각 포함; HP와 테두리는 편집 대상 아님'),
        ('10_구속','구속',[S+'sys031.tm2',S+'sys032.tm2'],'구속 한자·붉은 번짐·BIND 영문 및 효과 조각을 함께 보관'),
        ('11_포획','포획',[S+'sys018.tm2'],'확인된 글자 텍스처는 한 장; 근거 없이 세 형태를 새로 만들지 않음')])
    manifest=[];checked=0;psd_count=0
    font=ImageFont.truetype(str(LABEL),22);small=ImageFont.truetype(str(LABEL),18)
    for name,text,paths,note in groups:
        folder=OUT/name;folder.mkdir(exist_ok=True)
        board=Image.new('RGB',(1120,115+340*((len(paths)+1)//2)),(70,73,80));d=ImageDraw.Draw(board)
        d.text((20,15),text+' — 원본 형태별 식자 작업',font=font,fill='white')
        d.text((20,52),note,font=small,fill=(224,225,228))
        variants=[]
        for i,path in enumerate(paths):
            base=Path(path).stem;png=ROOT/'extracted/original/images'/(path+'.png')
            original=Image.open(png).convert('RGBA')
            enlarged=original.resize((original.width*4,original.height*4),Image.Resampling.NEAREST)
            empty=Image.new('RGBA',enlarged.size)
            # Original is visible, so every supplied variant is immediately apparent.
            layers=[('확인배경_회색_기본끔',Image.new('RGBA',enlarged.size,(70,73,80,255)),False),
                    ('원본_'+base+'_식자후끔',enlarged,True),('한글식자_여기에작업',empty,True)]
            out=folder/(base+'_원본형태_작업.psd');layered_psd(out,layers,enlarged)
            enlarged.save(folder/(base+'_원본형태_4배.png'))
            shutil.copy2(png,folder/(base+'_원본크기.png'))
            np.testing.assert_array_equal(np.array(enlarged.resize(original.size,Image.Resampling.NEAREST)),np.array(original))
            raw=ROOT/'extracted/original/raw'/path;dest=OUT/'원본자료'/path;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(raw,dest);assert file_hash(raw)==file_hash(dest)
            uad=raw.with_suffix('.uad')
            if uad.exists():shutil.copy2(uad,dest.with_suffix('.uad'))
            x=20+560*(i%2);y=110+340*(i//2)
            d.text((x,y),base+f'  ({original.width} × {original.height})',font=font,fill='white')
            reference=original.copy();reference.thumbnail((520,280),Image.Resampling.NEAREST)
            if original.width<=260 and original.height<=140:
                reference=original.resize((original.width*2,original.height*2),Image.Resampling.NEAREST)
            board.paste(reference,(x,y+42),reference)
            variants.append(dict(source=path,source_png_sha256=file_hash(png),raw_sha256=file_hash(raw),
                native_size=list(original.size),work_size=list(enlarged.size),scale=4,
                psd=str(out.relative_to(OUT)),sha256=file_hash(out),original_pixels_preserved=True))
            psd_count+=1;checked+=3
        overview=folder/'형태비교_먼저보기.jpg';board.save(overview,quality=95)
        manifest.append(dict(group=name,text=text,note=note,variants=variants,overview=str(overview.relative_to(OUT))))
    # Keep all previously preserved binary animation/mapping sources, unchanged.
    src=ROOT/'outputs/battle_lettering_work_v1/03_원본보관/raw'
    for p in src.rglob('*'):
        if p.is_file() and p.suffix in ('.upl','.upm','.ups'):
            dest=OUT/'원본자료'/p.relative_to(src);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    write_json(OUT/'manifest.json',dict(version=2,correction='All original texture variants retained individually; v1 single-style drafts superseded',
        groups=manifest,psd_count=psd_count,verified_layer_count=checked,korean_lettering_performed=False,
        animation_state_order_verified=False,iso_modified=False,
        validation='Every PSD merged image and raster layer reread; 4x nearest sampling reverses exactly to source RGBA'))
    print(json.dumps(dict(psds=psd_count,verified_layers=checked,output=str(OUT)),ensure_ascii=False))

if __name__=='__main__':main()
