#!/usr/bin/env python3
"""A common Photoshop canvas, with inverse game mesh layout at packing time.

This parser is deliberately pinned to the observed victory-condition mesh. It
does not pretend to decode arbitrary UPL animation files or their timelines.
"""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build/python_psd'))
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from scipy.ndimage import grey_dilation
from make_battle_lettering_work import layered_psd, checker

UPL = ROOT / 'extracted/original/raw/DMAP/dmap/map/bstart/bt_sjkn_std.upl'
ART = ROOT / 'localization/artwork/battle_conditions_user_v1'
WORK = ROOT / 'outputs/battle_lettering_aligned_v4/모든적격파'
SIZE = (1024, 512)
# Object boundaries verified against names, vertex counts and UV anchors below.
OBJECTS = [('sta_pl',2402),('sta_red',7301),('sta_glw',7617),
           ('stb_glw_quad',7933),('sta_sdw',8249),('stb_pl',10509),
           ('stb_red',15224),('stb_glw',15540),('stb_sdw',18096)]


def read_maps():
    data = UPL.read_bytes()
    if hashlib.sha256(data).hexdigest()!='a0aa4833b9212a5dc2a186bb6540ed4c522b52c91b4d7f49262ed7a8068d09bd':
        raise ValueError('The original battle layout changed; revalidate its maps')
    maps = {}
    for k,(name,start) in enumerate(OBJECTS):
        wire_name = name.replace('_quad','').encode()
        assert data[start:start+len(wire_name)+1] == wire_name+b'\0'
        end = OBJECTS[k+1][1] if k+1<len(OBJECTS) else 20800
        pos = start+len(wire_name)+13
        n = struct.unpack_from('<I',data,pos+24)[0]
        assert n in (4,44,48)
        vertices = np.array(list(struct.iter_unpack('<3f',data[pos+28:pos+28+12*n])))
        anchors = set()
        for match in re.finditer(b'\x95\x95\x95\xff',data[start:end]):
            offset = start+match.start()
            vertex,normal = struct.unpack_from('<II',data,offset-8)
            u,v = struct.unpack_from('<2f',data,offset+4)
            if vertex<4 and normal<n and 0<=u<=1 and -1<=v<=0:
                anchors.add((vertex,u*256-.5,(v+1)*128-.5,*vertices[vertex,:2]))
        anchors = np.array(sorted(anchors))
        assert anchors.shape==(4,5) and list(anchors[:,0])==[0,1,2,3]
        xy = np.c_[anchors[:,1:3],np.ones(4)]
        matrix = np.eye(3)
        matrix[:,:2] = np.linalg.lstsq(xy,anchors[:,3:],rcond=None)[0]
        assert np.max(np.abs(xy@matrix[:,:2]-anchors[:,3:]))<1e-4
        maps[name] = matrix
    return maps


def make_common_work():
    """Seed editable aligned rasters from the user's saved type-layer shapes."""
    assert not WORK.exists(), 'Never overwrite user editing work'
    WORK.mkdir(parents=True)
    psd = PSDImage.open(ART/'bt_tx05.psd')
    alpha = Image.new('L',SIZE)
    for layer in psd:
        if layer.visible and layer.kind=='type':
            ink = layer.topil().convert('RGBA').getchannel('A')
            canvas = Image.new('L',SIZE);canvas.paste(ink,layer.bbox[:2])
            alpha = Image.fromarray(np.maximum(np.array(alpha),np.array(canvas)))
    a = np.array(alpha)
    yy,xx = np.ogrid[-8:9,-8:9]
    expanded = grey_dilation(a,footprint=xx*xx+yy*yy<=64,mode='constant',cval=0)
    # User's red PSD had an 8px outside stroke in the compressed atlas. Preserve
    # that visible halo (~10.5px on this common canvas), not just the fill mask.
    ry,rx=np.ogrid[-11:12,-11:12]
    red_expanded=grey_dilation(a,footprint=rx*rx+ry*ry<=10.5**2,mode='constant',cval=0)
    def color(rgb,mask):
        im = Image.new('RGBA',SIZE,(*rgb,0));im.putalpha(Image.fromarray(mask));return im
    # The base artwork is preserved exactly. Only the effect shapes are unified.
    base = Image.open(ART/'bt_tx05_4x.png').convert('RGBA')
    variants = {5:base,6:color((242,36,2),red_expanded),
                7:color((241,142,4),np.maximum(expanded.astype(int)-a,0).astype('uint8')),
                # Original shadow covers the complete base silhouette, including
                # its white outside stroke, rather than only the type-layer ink.
                8:color((18,6,3),np.array(base.getchannel('A')))}
    for n,im in variants.items():
        layers=[('확인배경_내보내기제외',checker(SIZE),False),
                ('기준글자_내보내기제외',base,False),('한글효과_편집',im,True)]
        layered_psd(WORK/f'bt_tx{n:02}_공통좌표.psd',layers,im)
        im.save(WORK/f'bt_tx{n:02}_공통좌표.png')
    return variants


def read_common(path):
    """Composite visible user layers; reserved helper layers never get packed."""
    if path.suffix.lower()=='.png':
        result = Image.open(path).convert('RGBA')
    else:
        psd=PSDImage.open(path)
        result=psd.composite(layer_filter=lambda l:l.is_visible() and
                             not l.name.startswith(('확인배경_','기준글자_'))).convert('RGBA')
    if result.size!=SIZE:raise ValueError(f'Common canvas must be {SIZE}: {path}')
    return result


def pack_common(image,n,maps):
    if n==5:return image.resize((256,128),Image.Resampling.LANCZOS)
    suffix={6:'red',7:'glw',8:'sdw'}[n]
    result=Image.new('RGBA',SIZE)
    # Pixel-edge coordinates in 4x artwork -> native texel-center coordinates.
    h=np.array([[.25,0,0],[0,.25,0],[-.5,-.5,1]])
    for line,prefix in enumerate(('sta','stb')):
        base=maps[prefix+'_pl'];target=maps[prefix+'_'+suffix]
        # Pillow wants inverse mapping: destination texture -> common artwork.
        inverse=h@target@np.linalg.inv(base)@np.linalg.inv(h)
        coeff=tuple(inverse.T[:2,:].ravel())
        # Isolate rows BEFORE resampling: adjacent atlas rows must never bleed.
        row=Image.new('RGBA',SIZE)
        row.paste(image.crop((0,line*256,1024,(line+1)*256)),(0,line*256))
        box=row.getchannel('A').getbbox()
        if box:
            x0,y0,x1,y1=box
            corners=np.array([[x0,y0,1],[x1,y0,1],[x0,y1,1],[x1,y1,1]])@np.linalg.inv(inverse)
            if np.any(corners[:,:2]<0) or np.any(corners[:,:2]>np.array(SIZE)):
                raise ValueError(f'bt_tx{n:02} row {line+1} would be clipped by the game atlas; adjust the common layout')
        transformed=row.transform(SIZE,Image.Transform.AFFINE,coeff,Image.Resampling.BICUBIC)
        result.alpha_composite(transformed)
    return result.resize((256,128),Image.Resampling.LANCZOS)


def unpack_common(image,n,maps):
    """Diagnostic inverse layout; not a lossless edit source after resampling."""
    image=image.resize(SIZE,Image.Resampling.NEAREST)
    if n==5:return image
    suffix={6:'red',7:'glw',8:'sdw'}[n]
    result=Image.new('RGBA',SIZE)
    h=np.array([[.25,0,0],[0,.25,0],[-.5,-.5,1]])
    for line,prefix in enumerate(('sta','stb')):
        inverse=h@maps[prefix+'_pl']@np.linalg.inv(maps[prefix+'_'+suffix])@np.linalg.inv(h)
        rendered=image.transform(SIZE,Image.Transform.AFFINE,tuple(inverse.T[:2,:].ravel()),Image.Resampling.BICUBIC)
        box=(0,line*256,1024,(line+1)*256)
        result.paste(rendered.crop(box),(0,line*256))
    return result


def metadata(maps):
    return dict(upstream_upl_sha256=hashlib.sha256(UPL.read_bytes()).hexdigest(),
                canvas_size=list(SIZE),game_texture_size=[256,128],
                maps={name:m.tolist() for name,m in maps.items()},
                note='Bind-plane spatial registration only; original animation timing and 3D deformation are retained.')


if __name__=='__main__':
    maps=read_maps();make_common_work()
    (WORK/'layout.json').write_text(json.dumps(metadata(maps),indent=2)+'\n')
    print(WORK)
