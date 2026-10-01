#!/usr/bin/env python3
"""Audit original indexed textures; export a bounded UI/help inspection catalog."""
import collections
import re
from pathlib import Path
from PIL import Image, ImageDraw
from localization_pipeline import ROOT, hed_tree, file_hash, write_json, sha
from iso_archive_stage import SOURCE, source_sha
from ui_texture_codec import parse, serialize, preview_rgba, uad_rectangles

OUT=ROOT/'build/ui_audit'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    catalog=[];counts=collections.Counter();selected=[]
    for archive in ('STATUS','DMAP'):
        hed=SOURCE/'DATA'/(archive+'.HED');dat=SOURCE/'DATA'/(archive+'.DAT')
        if file_hash(hed)!=source_sha(hed) or file_hash(dat)!=source_sha(dat):raise ValueError('Original archive changed')
        files,_=hed_tree(hed.read_bytes());by_path={e['path']:e for e in files}
        with dat.open('rb') as fp:
            for e in files:
                if not e['path'].endswith('.tm2'):continue
                fp.seek(e['offset']);raw=fp.read(e['size']);model=parse(raw)
                if serialize(model)!=raw:raise ValueError('Texture roundtrip mismatch')
                counts['%s_%dbpp'%(archive,model['bpp'])]+=1
                row=dict(archive=archive,path=e['path'],offset=e['offset'],bytes=e['size'],
                         sha256=sha(raw),width=model['width'],height=model['height'],bpp=model['bpp'],
                         exact_roundtrip=True,preview_layout_verified=False)
                # Only these observed UI/help families are exported, not all character art.
                is_ui=archive=='STATUS' and bool(re.fullmatch(r'sys\d+\.tm2',e['name']))
                is_help=archive=='DMAP' and bool(re.fullmatch(r'ev(?:13[5-9]|14\d|15\d|16[0-2])\.tm2',e['name']))
                if is_ui or is_help:
                    p=OUT/(e['name']+'.png');Image.frombytes('RGBA',(model['width'],model['height']),preview_rgba(model)).save(p)
                    row['preview']=str(p.relative_to(ROOT));row['classification']='menu_atlas_candidate' if is_ui else 'help_image_candidate'
                    uad=by_path.get(e['path'][:-4]+'.uad')
                    if uad:
                        fp.seek(uad['offset']);uraw=fp.read(uad['size'])
                        try:row['uad']=uad_rectangles(uraw,model['width'],model['height'])
                        except ValueError as ex:row['uad_inspection_note']=str(ex)
                    selected.append(row)
                catalog.append(row)
    helps=[r for r in selected if r['classification']=='help_image_candidate']
    helps.sort(key=lambda r:r['path'])
    for batch in range((len(helps)+7)//8):
        sheet=Image.new('RGB',(1280,880),(35,35,35));draw=ImageDraw.Draw(sheet)
        for i,r in enumerate(helps[batch*8:(batch+1)*8]):
            im=Image.open(ROOT/r['preview']);im.thumbnail((320,400));x=(i%4)*320;y=(i//4)*440
            sheet.paste(im,(x,y+22),im);draw.text((x+5,y+3),r['path'],fill='white')
        sheet.save(OUT/('help-contact-%d.png'%batch))
    write_json(ROOT/'reports/ui_texture_audit.json',dict(schema_version=1,counts=dict(counts),
        total_textures=len(catalog),exact_roundtrip=True,catalog=catalog,
        limitations=['Only observed single-picture 4/8-bit indexed format; mipmaps/direct color rejected.',
                     '4-bit nibble roundtrip is verified; no claim of all previews matching runtime GS layout.',
                     'UAD rectangle prefix inspected; tail semantics remain uninterpreted.',
                     'Help classification is a candidate until each image is visually reviewed.']))
    print('TIM2 byte-exact roundtrip:',len(catalog),dict(counts),'exported UI/help:',len(selected))


if __name__=='__main__':main()
