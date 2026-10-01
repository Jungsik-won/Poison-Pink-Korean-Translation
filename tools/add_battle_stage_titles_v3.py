#!/usr/bin/env python3
"""Append stage/floor title PSDs to the existing v3 kit without rewriting edits."""
import json
import re
import shutil
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from battle_workbench_v3 import ROOT, OUT, IMG, RAW, digest, piece, unpack, transform
from make_battle_lettering_work import layered_psd, checker, LABEL
from ui_texture_codec import parse, preview_rgba

PREFIX='DMAP/dmap/map/bstart/'
MESH=RAW/PREFIX/'bt_name_std.upl'


def verify_layout():
    assert digest(MESH)=='01045e9183824d569dcf92ec8f097a555acebe6acb897c75a20d4ab35c1d0e1d'
    data=MESH.read_bytes();result={}
    for family,name,start,end,height,color in [
        ('bt_nm','name_plt',20,473,64,b'\x96\x96\x96\xff'),
        ('bt_ar','Plane01',473,977,48,b'\x95\x95\x95\xff')]:
        assert data[start:start+len(name)+1]==name.encode()+b'\0'
        pos=start+len(name)+13;n=struct.unpack_from('<I',data,pos+24)[0]
        assert n==6
        vertices=np.array(list(struct.iter_unpack('<3f',data[pos+28:pos+28+12*n])))
        anchors=set()
        for match in re.finditer(re.escape(color),data[start:end]):
            at=start+match.start();i,j=struct.unpack_from('<II',data,at-8)
            u,v=struct.unpack_from('<2f',data,at+4)
            assert i<6 and j<6
            anchors.add((i,u*256-.5,(v+1)*128-.5))
        assert len(anchors)==8
        for row,ids in enumerate(([0,1,3,4],[1,2,4,5])):
            # Each half is the same world width; their shared vertex stitches
            # the two stored rows into a single horizontal strip.
            assert abs((vertices[1,0]-vertices[0,0])-(vertices[2,0]-vertices[1,0]))<1e-4
            values=[v for i,u,v in anchors if i in ids and row*height-.5<=v<=(row+1)*height-.5]
            assert values and max(values)-min(values)>height-1.1
        result[family]=dict(mesh='bt_name_std.upl',object=name,row_height=height,
                            anchors=sorted(anchors),vertices=vertices.tolist())
    return result


def main():
    manifest_path=OUT/'manifest.json';manifest=json.loads(manifest_path.read_text())
    assert manifest['version']==3 and not manifest.get('stage_title_extension')
    # Snapshot actual current edits rather than assuming original generated hashes.
    previous={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*.psd')}
    mesh=verify_layout();specs=[];groups=[];copied=[]
    for family,label,number,height in [('bt_ar','계층명',12,48),('bt_nm','장소명',13,64)]:
        grouped={}
        for p in sorted((RAW/PREFIX).glob(family+'*.tm2')):
            grouped.setdefault(digest(p),[]).append(p)
        for same in grouped.values():
            representative=same[0];source=PREFIX+representative.name;ident=representative.stem
            path=OUT/f'{number}_{label}_{ident}.psd';assert not path.exists()
            size=(2048,height*4);pieces=[]
            for row in range(2):
                # Source high-res atlas pixels -> unfolded high-res strip pixels.
                forward=np.array([[1.,0,0],[0,1.,0],[row*1024,-row*height*4,1.]])
                pieces.append(piece(source,(0,row*height,256,(row+1)*height),forward,
                                    (row*1024,0,(row+1)*1024,height*4)))
            spec=dict(id=ident,group=f'{number}_{label}',name=path.stem,size=size,
                      original_text='원문은 PSD 원문 레이어 및 계층·장소명_원문목록 JPG 참고',
                      pieces=pieces,kind='stage_title',base=ident,psd=path.name,
                      has_existing_korean=False,aliases=[PREFIX+p.name for p in same[1:]])
            atlas=Image.open(IMG/(source+'.png')).convert('RGBA')
            assert atlas.size==(256,128)
            assert atlas.tobytes()==preview_rgba(parse(representative.read_bytes()))
            enlarged=atlas.resize((1024,512),Image.Resampling.NEAREST)
            original=unpack({source:enlarged},spec)
            # Exact extraction/inverse reassembly for every stored row, including
            # invisible RGB independently preserved in the original atlas copy.
            for p in pieces:
                row=Image.new('RGBA',size);box=tuple(p['clip']);row.paste(original.crop(box),box[:2])
                recovered=transform(row,enlarged.size,p['forward']);box=tuple(x*4 for x in p['rect'])
                a=np.array(recovered.crop(box));b=np.array(enlarged.crop(box))
                np.testing.assert_array_equal(a[:,:,3],b[:,:,3])
                np.testing.assert_array_equal(a[:,:,:3][b[:,:,3]>0],b[:,:,:3][b[:,:,3]>0])
            if height==48:
                assert atlas.getchannel('A').crop((0,96,256,128)).getbbox() is None
            blank=Image.new('RGBA',size);guide=Image.new('RGBA',size);d=ImageDraw.Draw(guide)
            d.line((1024,0,1024,size[1]-1),fill=(0,240,220,170),width=2)
            layered_psd(path,[('확인배경_회색_내보내기제외',checker(size),False),
                              ('원문_한줄로펼친원본_내보내기제외',original,True),
                              ('가이드_저장분할선_글자지나가도됨',guide,False),
                              ('한글식자_여기에작업',blank,True)],original)
            png=path.with_name(path.stem+'_원문.png');original.save(png)
            spec.update(sha256=digest(path),original_png=png.name,source_sha256=digest(representative))
            specs.append(spec);groups.append((label,ident,len(same),original))
            for p in same:
                for src,dest in [(p,OUT/'원본자료'/PREFIX/p.name),
                    (IMG/(PREFIX+p.name+'.png'),OUT/'원본자료/atlas_png'/(PREFIX+p.name+'.png'))]:
                    if dest.exists():assert digest(src)==digest(dest)
                    else:shutil.copy2(src,dest)
                    copied.append(dict(path=str(dest.relative_to(OUT)),sha256=digest(src)))
    font=ImageFont.truetype(str(LABEL),24);pages=[]
    for start in range(0,len(groups),9):
        board=Image.new('RGB',(1280,90+9*115),(48,54,62));draw=ImageDraw.Draw(board)
        draw.text((24,20),f'계층·장소명 원문 목록  {start//9+1}/{(len(groups)+8)//9}',font=font,fill='white')
        for i,(label,ident,count,im) in enumerate(groups[start:start+9]):
            y=85+i*115;draw.text((24,y),f'{label} / {ident} / 적용 파일 {count}개',font=font,fill=(210,215,225))
            ref=im.copy();ref.thumbnail((1180,76),Image.Resampling.LANCZOS)
            board.paste(ref,(30,y+30),ref)
        pages.append(board)
        board.save(OUT/f'계층·장소명_원문목록_{start//9+1:02}.jpg',quality=94)
    # PNG/JPG contact sheets are the primary visual artifact; no PDF dependency.
    for s in specs:s['original_text']='원문은 PSD 원문 레이어 및 계층·장소명_원문목록 JPG 참고'
    manifest['documents'].extend(specs)
    manifest['source_textures']=sorted(set(manifest['source_textures'])|{p['source'] for s in specs for p in s['pieces']}|{a for s in specs for a in s['aliases']})
    manifest['psd_count']=len(manifest['documents']);manifest['source_texture_count']=len(manifest['source_textures'])
    manifest['raw_files'].extend(copied)
    manifest['stage_title_extension']=dict(date='2026-09-20',new_psds=len(specs),source_files=112,
        unique_floor_titles=10,unique_location_titles=44,layout=mesh,
        preserves_existing_psds=previous,iso_modified=False,translation_performed=False)
    for name,sha in previous.items():assert digest(OUT/name)==sha
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'reports/battle_stage_titles_v3.json').write_text(json.dumps(manifest['stage_title_extension'],ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(new_psds=len(specs),total_psds=manifest['psd_count'],source_files=112,existing_psds_unchanged=len(previous)),ensure_ascii=False))


if __name__=='__main__':main()
