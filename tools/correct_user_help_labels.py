#!/usr/bin/env python3
"""Correct approved labels using the author's pinned clean background and font."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from localization_pipeline import ROOT, file_hash, write_json


def text_layer(e, font_path):
    x0,y0,x1,y1=e['box'];w=x1-x0;h=y1-y0;s=4;size=e['size'];sw=e['stroke']
    while True:
        font=ImageFont.truetype(str(font_path),round(size*s))
        width=font.getlength(e['text'])/s
        bbox=font.getbbox('한글공격');height=(bbox[3]-bbox[1])/s
        if width+sw*2+2<=w and height+sw*2+1<=h:
            break
        size-=.25
        if size<8:
            raise ValueError('Corrected label does not fit')
    layer=Image.new('RGBA',(w*s,h*s));draw=ImageDraw.Draw(layer)
    draw.text((round((w-width)/2*s),round((h-height)/2*s-bbox[1])),e['text'],font=font,
        fill=e['color'],stroke_width=round(sw*s),stroke_fill=e.get('stroke_color','#070a0b'))
    return layer.resize((w,h),Image.Resampling.LANCZOS),size


def main():
    cp=ROOT/'localization/help_label_corrections.json';c=json.loads(cp.read_text())
    font=ROOT/c['font'];assert file_hash(font)==c['font_sha256']
    checks=[]
    for page in c['pages']:
        source=ROOT/page['source'];clean=ROOT/page['clean'];dest=ROOT/page['output']
        assert file_hash(source)==page['source_sha256'] and file_hash(clean)==page['clean_sha256']
        before=Image.open(source).convert('RGBA');background=Image.open(clean).convert('RGBA');result=before.copy()
        allowed=np.zeros((384,640),dtype=bool)
        for e in page['edits']:
            box=e['box'];x0,y0,x1,y1=box
            # Verify the original render before replacing it, binding the background,
            # font and placement to the supplied user image.
            old=dict(e,text=e['source_text']);old_layer,_=text_layer(old,font)
            rebuilt=Image.alpha_composite(background.crop(box),old_layer)
            assert rebuilt.tobytes()==before.crop(box).tobytes(), 'Original label render mismatch'
            layer,size=text_layer(e,font)
            result.paste(Image.alpha_composite(background.crop(box),layer),(x0,y0))
            allowed[y0:y1,x0:x1]=True
            checks.append(dict(page=page['page'],box=box,source=e['source_text'],target=e['text'],rendered_size=size))
        a=np.array(before);b=np.array(result)
        assert np.array_equal(a[:,:,3],b[:,:,3])
        assert np.array_equal(a[~allowed],b[~allowed])
        dest.parent.mkdir(parents=True,exist_ok=True)
        result.save(dest)
        assert np.array_equal(np.array(Image.open(dest)),b)
    write_json(ROOT/'reports/help_label_corrections.json',dict(edits=checks,edit_count=len(checks),
        all_pixels_outside_six_label_boxes_preserved=True,alpha_mask_preserved=True,
        original_label_render_matched=True,font_sha256=c['font_sha256'],
        config_sha256=file_hash(cp),tool_sha256=file_hash(Path(__file__))))
    print('Corrected labels:',len(checks),flush=True)


if __name__=='__main__':
    main()
