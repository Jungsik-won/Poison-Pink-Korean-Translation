#!/usr/bin/env python3
"""Register the two heading red sprites to their four existing glyph quads."""
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build/python_psd'))
import numpy as np
from PIL import Image,ImageFilter
from psd_tools import PSDImage
from scipy.ndimage import grey_dilation
from make_battle_lettering_work import layered_psd,checker
from build_battle_conditions_psd import compile_texture
from ui_texture_codec import parse,serialize,preview_rgba,unpack_indices
from localization_pipeline import sha,file_hash,hed_tree,write_json
from iso_archive_stage import iso_inventory,exact,overlay
import build_user_translation_import as verifier

BASE=ROOT/'build/battle_shadow_v1/Poison Pink (Japan) - Korean battle shadow fix v1.iso'
BASE_SHA='7cc52fc3027ed9ec51aa8ffd60ec29fc0864995f1613032bab72d6c67c8ee1b7'
OUT=ROOT/'build/battle_heading_v1'
OUTPUT=OUT/'Poison Pink (Japan) - Korean heading alignment v1.iso'
WORK=ROOT/'outputs/battle_headings_aligned_v1'
RECTS={'s':(136,80,216,136),'h':(136,136,209,192)}
LABEL={'s':'승리조건','h':'패배조건'}
UPLS={'s':('bt_sjkn_std.upl','a0aa4833b9212a5dc2a186bb6540ed4c522b52c91b4d7f49262ed7a8068d09bd'),
      'h':('bt_hjkn_std.upl','c93c61a68576c5296379cff5b1b2ba082d74568e1a255d1bfffb6216af3a5ca3')}
# Shared document = 160 x 56 game-plane units at 4x. Both titles share an origin.
SIZE=(640,224)
H=np.array([[.25,0,0],[0,.25,0],[-.5,-.5,1]])
C=np.array([[1.,0,0],[0,-1.,0],[-288.5845947265625,193.8981475830078,1]])


def geometry(prefix):
    fn,digest=UPLS[prefix]
    data=(ROOT/'extracted/original/raw/DMAP/dmap/map/bstart'/fn).read_bytes()
    assert sha(data)==digest
    starts=([20,334,648,1146,1460,1774,2088,2402] if prefix=='s' else
            [20,334,648,962,1276,1590,1904,2218])
    names=['glw','red','sdw','w01','w02','w03','w04']
    result={}
    for k,suffix in enumerate(names):
        name=prefix+'_'+suffix;start=starts[k];end=starts[k+1]
        assert data[start:start+len(name)+1]==name.encode()+b'\0'
        pos=start+len(name)+13;n=struct.unpack_from('<I',data,pos+24)[0]
        assert n in (4,8)
        vertices=np.array(list(struct.iter_unpack('<3f',data[pos+28:pos+28+12*n])))
        anchors=set()
        for m in re.finditer(b'\x95\x95\x95\xff',data[start:end]):
            at=start+m.start();vi,ni=struct.unpack_from('<II',data,at-8)
            u,v=struct.unpack_from('<2f',data,at+4)
            if vi<4 and ni<n and 0<=u<=1 and -1<=v<=0:
                anchors.add((vi,u*256-.5,(v+1)*256-.5,*vertices[vi,:2]))
        r=np.array(sorted(anchors));assert r.shape==(4,5)
        xy=np.c_[r[:,1:3],np.ones(4)];matrix=np.eye(3)
        matrix[:,:2]=np.linalg.lstsq(xy,r[:,3:],rcond=None)[0]
        assert np.max(abs(xy@matrix[:,:2]-r[:,3:]))<1e-4
        lo=r[:,1:3].min(0);hi=r[:,1:3].max(0)
        result[suffix]=(matrix,(round(lo[0]),round(lo[1]),round(hi[0])+1,round(hi[1])+1))
    return result


def transform(image,size,inverse):
    return image.transform(size,Image.Transform.AFFINE,tuple(inverse.T[:2,:].ravel()),Image.Resampling.BICUBIC)


def common_base(atlas,maps):
    result=Image.new('RGBA',SIZE)
    for i in range(1,5):
        matrix,box=maps[f'w0{i}'];box=tuple(x*4 for x in box)
        glyph=Image.new('RGBA',atlas.size);glyph.paste(atlas.crop(box),box[:2])
        result.alpha_composite(transform(glyph,SIZE,H@C@np.linalg.inv(matrix)@np.linalg.inv(H)))
    return result


def seed_work():
    assert not WORK.exists(), 'Do not overwrite user artwork'
    WORK.mkdir(parents=True)
    atlas=Image.open(ROOT/'localization/artwork/battle_conditions_user_v1/bt_tx04_4x.png').convert('RGBA')
    for prefix in ('s','h'):
        base=common_base(atlas,geometry(prefix))
        # Retain a red halo around the whole outlined glyph, centered on its shape.
        y,x=np.ogrid[-4:5,-4:5]
        alpha=Image.fromarray(grey_dilation(np.array(base.getchannel('A')),footprint=x*x+y*y<=16,
                                          mode='constant',cval=0)).filter(ImageFilter.GaussianBlur(2))
        red=Image.new('RGBA',SIZE,(242,36,2,0));red.putalpha(alpha)
        for kind,im in [('기준',base),('빨간효과',red)]:
            name=LABEL[prefix]+'_'+kind
            layered_psd(WORK/(name+'.psd'),[
                ('확인배경_내보내기제외',checker(SIZE),False),
                ('기준글자_내보내기제외',base,False),('작업_표시레이어',im,True)],im)
            im.save(WORK/(name+'.png'))


def read_red(prefix):
    path=WORK/(LABEL[prefix]+'_빨간효과.psd')
    psd=PSDImage.open(path)
    im=psd.composite(layer_filter=lambda l:l.is_visible() and not l.name.startswith(('확인배경_','기준글자_'))).convert('RGBA')
    assert im.size==SIZE
    return im


def prepare(old):
    model=parse(old);assert model['bpp']==8 and (model['width'],model['height'])==(256,256)
    before=np.frombuffer(unpack_indices(model),np.uint8).reshape(256,256)
    desired=Image.frombytes('RGBA',(256,256),preview_rgba(model))
    allowed=np.zeros((256,256),bool);metrics={}
    for prefix in ('s','h'):
        maps=geometry(prefix);red=read_red(prefix);matrix,_=maps['red']
        atlas=transform(red,(1024,1024),H@matrix@np.linalg.inv(C)@np.linalg.inv(H))
        box=RECTS[prefix];hi=tuple(v*4 for v in box)
        tile=atlas.crop(hi).resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
        desired.paste(tile,box[:2]);allowed[box[1]:box[3],box[0]:box[2]]=True
        # Inspect the two red sprites on the same work canvas, after game scaling.
        for tag,source in [('before',Image.frombytes('RGBA',(256,256),preview_rgba(model))),('after',desired)]:
            isolated=Image.new('RGBA',(256,256));isolated.paste(source.crop(box),box[:2])
            common=transform(isolated.resize((1024,1024),Image.Resampling.NEAREST),SIZE,
                             H@C@np.linalg.inv(matrix)@np.linalg.inv(H))
            common.save(OUT/f'{prefix}_{tag}_red_common.png')
            a=np.array(common)[:,:,3]>127;b=np.array(red)[:,:,3]>127
            metrics[f'{prefix}_{tag}_iou']=float(np.count_nonzero(a&b)/np.count_nonzero(a|b))
    encoded,conversion=compile_texture(old,desired)
    candidate=np.frombuffer(unpack_indices(parse(encoded)),np.uint8).reshape(256,256)
    final=before.copy();final[allowed]=candidate[allowed]
    model['indices']=final.tobytes();new=serialize(model)
    assert np.array_equal(final[~allowed],before[~allowed])
    assert new[:64]==old[:64] and new[64+65536:]==old[64+65536:]
    assert serialize(parse(new))==new and new!=old
    Image.frombytes('RGBA',(256,256),preview_rgba(model)).save(OUT/'bt_tx04_compiled.png')
    return new,dict(red_rectangles=RECTS,registration_metrics=metrics,conversion=conversion,
                    outside_red_rectangles_identical=True,header_palette_identical=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',action='store_true');ap.add_argument('--build',action='store_true');args=ap.parse_args()
    OUT.mkdir(exist_ok=True,parents=True)
    if args.seed:seed_work()
    inv=iso_inventory(BASE);entries={e['path']:e for e in inv['files']}
    with BASE.open('rb') as f:
        he=entries['DATA/DMAP.HED'];de=entries['DATA/DMAP.DAT'];f.seek(he['lba']*2048)
        members={e['path']:e for e in hed_tree(exact(f,he['size']))[0]};entry=members['dmap/map/bstart/bt_tx04.tm2']
        offset=de['lba']*2048+entry['offset'];f.seek(offset);old=exact(f,entry['size'])
    assert old==(ROOT/'build/battle_conditions_psd_v1/bt_tx04.tm2').read_bytes()
    new,checks=prepare(old);(OUT/'bt_tx04.tm2').write_bytes(new)
    report=dict(base_iso=str(BASE.relative_to(ROOT)),base_sha256=BASE_SHA,iso_path=str(OUTPUT.relative_to(ROOT)),
                iso_offset=offset,before_sha256=sha(old),after_sha256=sha(new),checks=checks,
                changed_bytes=sum(a!=b for a,b in zip(old,new)),runtime_verified=False,
                sources={p.name:file_hash(p) for p in WORK.glob('*.psd')},
                scope='Only two red heading rectangles; base glyphs, heading glow/shadow and all body effects retained')
    if args.build:
        assert not OUTPUT.exists()
        patches=[dict(offset=offset,data=new,expected_sha256=sha(old))]
        iso=overlay(BASE,OUTPUT,patches,BASE_SHA);assert iso_inventory(OUTPUT)==inv
        verifier.BASE_HASH=BASE_SHA
        report.update(iso=iso,entire_iso_diff=verifier.verify_stream(BASE,OUTPUT,patches,iso['output_sha256']))
    write_json(OUT/('manifest.json' if args.build else 'prepare.json'),report)
    print(json.dumps(report if not args.build else dict(iso=report['iso'],checks=checks),ensure_ascii=False))


if __name__=='__main__':main()
