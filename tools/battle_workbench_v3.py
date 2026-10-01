#!/usr/bin/env python3
"""Non-destructive common-coordinate authoring kit; export atlas PNGs, never ISO.

UPL transforms cover battle conditions. Capture pieces use UAD rectangles and
anchors as an authoring layout, without pretending to decode animation timing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build/python_psd'))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage
from make_battle_lettering_work import layered_psd, checker, LABEL
from battle_lettering_layout import read_maps
from build_heading_alignment import geometry, H, C
from ui_texture_codec import uad_rectangles

OUT = ROOT / 'outputs/battle_lettering_work_v3'
OLD = ROOT / 'outputs/battle_lettering_work_v2'
IMG = ROOT / 'extracted/original/images'
RAW = ROOT / 'extracted/original/raw'
HELPERS = ('원문_', '참고_', '가이드_', '확인배경_', '원본_', '기준글자_')
STYLE = ['기본글자', '빨간효과', '주황윤곽', '검은효과']


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def transform(im, size, inverse):
    inverse=np.asarray(inverse)
    # Integer translations/quarter-turns need no interpolation; retain source
    # alpha and low-alpha RGB exactly for the UAD authoring pieces.
    linear=inverse[:2,:2]
    exact=(np.allclose(inverse,np.round(inverse),atol=1e-8) and
           np.allclose(linear@linear.T,np.eye(2),atol=1e-8))
    if exact:inverse=np.round(inverse)
    return im.transform(tuple(size), Image.Transform.AFFINE,
                        tuple(inverse.T[:2, :].ravel()), Image.Resampling.NEAREST if exact else Image.Resampling.BICUBIC)


def piece(source, rect, forward, clip):
    return dict(source=source, rect=list(rect), forward=np.asarray(forward).tolist(), clip=list(clip))


def unpack(images, spec):
    result = Image.new('RGBA', tuple(spec['size']))
    for p in spec['pieces']:
        source = images[p['source']]
        box = tuple(v * 4 for v in p['rect'])
        isolated = Image.new('RGBA', source.size)
        isolated.paste(source.crop(box), box[:2])
        im = transform(isolated, result.size, np.linalg.inv(p['forward']))
        box = tuple(p['clip'])
        layer = Image.new('RGBA', result.size); layer.paste(im.crop(box), box[:2])
        result.alpha_composite(layer)
    return result


def artwork(path):
    """Use visible work layers; helper layers never become game artwork."""
    psd = PSDImage.open(path)
    image = psd.composite(layer_filter=lambda layer: layer.is_visible() and
                          not layer.name.startswith(HELPERS), force=True)
    return image.convert('RGBA')


def defeat_geometry():
    path = RAW / 'DMAP/dmap/map/bstart/bt_hjkn_std.upl'
    assert digest(path) == 'c93c61a68576c5296379cff5b1b2ba082d74568e1a255d1bfffb6216af3a5ca3'
    data = path.read_bytes(); result = {}
    rows = [('pl', 2218, 7117, 256), ('red', 7117, 7433, 256),
            ('glw', 7433, 7749, 128), ('sdw', 7749, 8377, 128)]
    for suffix, start, end, width in rows:
        name = 'sta_' + suffix
        assert data[start:start+len(name)+1] == name.encode() + b'\0'
        pos = start+len(name)+13; n = struct.unpack_from('<I', data, pos+24)[0]
        vertices = np.array(list(struct.iter_unpack('<3f', data[pos+28:pos+28+12*n])))
        anchors = set()
        for match in re.finditer(b'\x95\x95\x95\xff', data[start:end]):
            at = start+match.start(); i,j = struct.unpack_from('<II', data, at-8)
            u,v = struct.unpack_from('<2f', data, at+4)
            if i<4 and j<n and 0<=u<=1 and -1<=v<=0:
                anchors.add((i,u*width-.5,(v+1)*64-.5,*vertices[i,:2]))
        a = np.array(sorted(anchors)); assert a.shape == (4,5)
        xy = np.c_[a[:,1:3], np.ones(4)]; m = np.eye(3)
        m[:,:2] = np.linalg.lstsq(xy,a[:,3:],rcond=None)[0]
        assert np.max(abs(xy@m[:,:2]-a[:,3:])) < 1e-4
        lo=a[:,1:3].min(0);hi=a[:,1:3].max(0)
        rect=(max(0,round(lo[0])),max(0,round(lo[1])),min(width,round(hi[0])+1),min(64,round(hi[1])+1))
        result[suffix] = (m,rect)
    return result


def defeat_maps():
    return {key:value[0] for key,value in defeat_geometry().items()}


def condition_specs():
    specs=[]; victory=read_maps(); dg=defeat_geometry();defeat={key:value[0] for key,value in dg.items()}
    groups=[('03_모든적격파',5,'全ての敵を撃破せよ'),('04_주인공전투불능',9,'主人公の戦闘不能'),
            ('05_루나셰격파',13,'ルナーシェを撃破せよ'),('06_테이지전투불능',17,'テージの戦闘不能'),
            ('07_보스격파',21,'ボスを撃破せよ'),('08_발드왕격파',25,'バルド王を撃破せよ')]
    for group, first, text in groups:
        one = first in (9,17); size = (1024,256 if one else 512)
        for k,suffix in enumerate(('pl','red','glw','sdw')):
            n=first+k; source=f'DMAP/dmap/map/bstart/bt_tx{n:02}.tm2'
            with Image.open(IMG/(source+'.png')) as image:native=image.size
            pieces=[]
            for row in range(1 if one else 2):
                name=('sta','stb')[row]
                base=defeat['pl'] if one else victory[name+'_pl']
                target=defeat[suffix] if one else victory[name+'_'+suffix]
                forward=H@target@np.linalg.inv(base)@np.linalg.inv(H)
                stride=56 if not one and suffix=='red' else 64
                rect=dg[suffix][1] if one else (0,row*stride,native[0],(row+1)*stride)
                pieces.append(piece(source,rect,forward,(0,row*256,1024,(row+1)*256)))
            specs.append(dict(id=f'bt_tx{n:02}',group=group,name=f'{k+1:02}_{STYLE[k]}',size=size,
                              original_text=text,pieces=pieces,kind='condition',base=f'bt_tx{first:02}'))
    for prefix,group,text in [('s','01_승리조건','勝利条件'),('h','02_패배조건','敗北条件')]:
        maps=geometry(prefix);source='DMAP/dmap/map/bstart/bt_tx04.tm2'
        # Split midway between glyph centers; preserve separate animated quads.
        centers=[]
        for i in range(1,5):
            m,box=maps[f'w0{i}'];f=H@m@np.linalg.inv(C)@np.linalg.inv(H)
            centers.append((np.array([(box[0]+box[2])*2,(box[1]+box[3])*2,1])@f)[0])
        cuts=[0]+[round((a+b)/2) for a,b in zip(centers,centers[1:])]+[640]
        for k,key in enumerate(('base','red','glw','sdw')):
            pieces=[]
            for i,suffix in enumerate([f'w0{x}' for x in range(1,5)] if key=='base' else [key]):
                m,box=maps[suffix];f=H@m@np.linalg.inv(C)@np.linalg.inv(H)
                clip=(cuts[i],0,cuts[i+1],224) if key=='base' else (0,0,640,224)
                pieces.append(piece(source,box,f,clip))
            specs.append(dict(id=f'title_{prefix}_{key}',group=group,name=f'{k+1:02}_{STYLE[k]}',size=(640,224),
                              original_text=text,pieces=pieces,kind='heading',base=f'title_{prefix}_base'))
    return specs


def uad(name):
    path='STATUS/status/'+name+'.tm2'
    with Image.open(IMG/(path+'.png')) as im:size=im.size
    return path,uad_rectangles((RAW/path).with_suffix('.uad').read_bytes(),*size)['rectangles']


def uad_piece(name,index,slot,cell,rotation=0):
    source,rows=uad(name);r=rows[index];x,y,w,h=r['rect'];cx,cy=r['anchor']
    theta=np.deg2rad(rotation);c,s=np.cos(theta),np.sin(theta)
    move=np.array([[1,0,0],[0,1,0],[-4*(x+cx),-4*(y+cy),1.]])
    rot=np.array([[c,s,0],[-s,c,0],[0,0,1.]])
    put=np.array([[1,0,0],[0,1,0],[(slot+.5)*cell[0],cell[1]/2,1.]])
    p=piece(source,(x,y,x+w,y+h),move@rot@put,(slot*cell[0],0,(slot+1)*cell[0],cell[1]))
    p.update(uad_index=index,uad_anchor=r['anchor'],authoring_rotation=rotation)
    return p


def capture_specs():
    result=[]
    # Native O and K are sideways; reverse them only on the authoring canvas.
    pieces=[uad_piece('sys013',idx,i,(256,320),-90 if idx in (13,14) else 0)
            for i,idx in enumerate([13,12,11,10,14,9,8,7])]
    result.append(dict(id='overkill',group='09_오버킬',name='01_글자조각_정방향',size=(2048,320),
                       original_text='OVERKILL',pieces=pieces,kind='uad',base='overkill'))
    for key,indices in [('base',(2,3)),('red',(0,1))]:
        result.append(dict(id='bind_jp_'+key,group='10_구속',name=('01_구속_기본글자' if key=='base' else '02_구속_빨간효과'),
                           size=(1024,512),original_text='拘束',kind='uad',base='bind_jp_base',
                           pieces=[uad_piece('sys031',idx,i,(512,512)) for i,idx in enumerate(indices)]))
    for key,indices in [('base',(2,3,4,5)),('red',(8,9,10,11)),('dark',(6,7,12,13))]:
        number={'base':3,'red':4,'dark':5}[key]
        result.append(dict(id='bind_en_'+key,group='10_구속',name=f'{number:02}_BIND_'+{'base':'기본글자','red':'빨간글자','dark':'어두운글자'}[key],
                           size=(1024,256),original_text='BIND',kind='uad',base='bind_en_base',
                           pieces=[uad_piece('sys032',idx,i,(256,256)) for i,idx in enumerate(indices)]))
    result.append(dict(id='bind_en_blur',group='10_구속',name='06_BIND_번짐조각',size=(1024,256),
                       original_text='BIND',kind='uad',base='bind_en_base',pieces=[
                           uad_piece(name,idx,i,(256,256)) for i,(name,idx) in enumerate([('sys032',0),('sys032',1),('sys031',5),('sys031',4)])]))
    result.append(dict(id='capture',group='11_포획',name='01_포획',size=(512,128),original_text='CAPTURE',kind='uad',base='capture',
                       pieces=[uad_piece('sys018',0,0,(512,128))]))
    return result


def generate():
    assert not OUT.exists(), 'Never overwrite user editing work'
    OUT.mkdir(parents=True)
    specs=condition_specs()+capture_specs()
    sources=sorted({p['source'] for s in specs for p in s['pieces']})
    images={}
    for source in sources:
        with Image.open(IMG/(source+'.png')) as im:
            images[source]=im.convert('RGBA').resize((im.width*4,im.height*4),Image.Resampling.NEAREST)
    originals={s['id']:unpack(images,s) for s in specs}
    old_manifest=json.loads((OLD/'manifest.json').read_text()); edited={}; backups=[]
    indexed={v['psd']:v for g in old_manifest['groups'] for v in g['variants']}
    # Preserve original Photoshop type layers and all extra user copies separately.
    for p in OLD.rglob('*.psd'):
        relative=str(p.relative_to(OLD)); v=indexed.get(relative)
        if v is None or digest(p)!=v['sha256']:
            dest=OUT/'기존작업_원본PSD보존'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
            backups.append(dict(path=str(p.relative_to(ROOT)),backup=str(dest.relative_to(OUT)),sha256=digest(p)))
            if v:edited[v['source']]=artwork(p)
    # Keep the already accepted corrections for the completed victory lettering.
    for n in range(5,9):
        path=ROOT/f'outputs/battle_lettering_aligned_v4/모든적격파/bt_tx{n:02}_공통좌표.png'
        if path.exists():edited[f'common:bt_tx{n:02}']=Image.open(path).convert('RGBA')
    adopted=json.loads((ROOT/'localization/pipeline.json').read_text())['user_artwork_policy']['adopted_assets']
    heading_path=ROOT/adopted['dmap/map/bstart/bt_tx04.tm2']
    edited['DMAP/dmap/map/bstart/bt_tx04.tm2']=Image.open(heading_path).convert('RGBA').resize((1024,1024),Image.Resampling.NEAREST)
    old_common={}
    for s in specs:
        if s['group']=='04_주인공전투불능' and all(p['source'] in edited for p in s['pieces']):
            old_common[s['id']]=unpack(edited,s)
    if 'bt_tx09' in old_common:
        base=old_common['bt_tx09'];box=base.getchannel('A').getbbox()
        if 'bt_tx11' in old_common:
            original=old_common['bt_tx11'];bounds=original.getchannel('A').getbbox()
            aligned=Image.new('RGBA',base.size)
            aligned.paste(original.crop(bounds).resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS),box[:2])
            edited['common:bt_tx11']=aligned
        if 'bt_tx12' in old_common:
            shadow=Image.new('RGBA',base.size,(18,6,3,0));shadow.putalpha(base.getchannel('A'))
            edited['common:bt_tx12']=shadow
    rows=[];font=ImageFont.truetype(str(LABEL),22)
    jp_font=ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',22)
    for s in specs:
        folder=OUT/s['group'];folder.mkdir(exist_ok=True)
        original=originals[s['id']];base=originals[s['base']]
        size=tuple(s['size']);blank=Image.new('RGBA',size)
        existing=blank
        if 'common:'+s['id'] in edited:existing=edited['common:'+s['id']]
        elif all(p['source'] in edited for p in s['pieces']):existing=unpack(edited,s)
        has_edit=existing.getchannel('A').getbbox() is not None
        guide=Image.new('RGBA',size);draw=ImageDraw.Draw(guide)
        for p in s['pieces']:
            x0,y0,x1,y1=p['clip'];draw.rectangle((x0,y0,x1-1,y1-1),outline=(0,240,220,150),width=2)
        layers=[('확인배경_회색_내보내기제외',checker(size),False),
                ('원문_기본글자_같은좌표_내보내기제외',base,False),
                ('원문_해당효과_내보내기제외',original,not has_edit),
                ('가이드_조각구분_내보내기제외',guide,False),
                ('참고_보정전_기존한글_내보내기제외',old_common.get(s['id'],blank),False),
                ('기존한글작업_편집가능',existing,has_edit),('한글식자_여기에작업',blank,True)]
        psd=folder/(s['name']+'.psd');layered_psd(psd,layers,existing if has_edit else original)
        original.save(folder/(s['name']+'_원문.png'))
        if has_edit:existing.save(folder/(s['name']+'_기존한글.png'))
        # Record the source document and all geometry; packing never guesses names.
        s.update(psd=str(psd.relative_to(OUT)),sha256=digest(psd),has_existing_korean=has_edit,
                 original_png=str((folder/(s['name']+'_원문.png')).relative_to(OUT)))
        rows.append(s)
    for group in sorted({s['group'] for s in rows}):
        docs=[s for s in rows if s['group']==group]
        board=Image.new('RGB',(1040,80+180*((len(docs)+1)//2)),(48,54,62));d=ImageDraw.Draw(board)
        d.text((20,20),group,font=font,fill='white')
        d.text((410,20),docs[0]['original_text'],font=jp_font,fill='white')
        for i,s in enumerate(docs):
            x=20+(i%2)*520;y=80+(i//2)*180
            d.text((x,y),s['name'],font=font,fill='white')
            im=originals[s['id']].copy();im.thumbnail((490,130),Image.Resampling.LANCZOS);board.paste(im,(x,y+32),im)
        board.save(OUT/group/'원문_형태비교.jpg',quality=95)
    # Untouched raw assets and atlas PNGs include every one of the 29 v2 sources.
    raw_files=[]
    for p in (OLD/'원본자료').rglob('*'):
        if p.is_file():
            dest=OUT/'원본자료'/p.relative_to(OLD/'원본자료');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
            raw_files.append(dict(path=str(dest.relative_to(OUT)),sha256=digest(p)))
    for source in sources:
        dest=OUT/'원본자료/atlas_png'/(source+'.png');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(IMG/(source+'.png'),dest)
    manifest=dict(version=3,documents=rows,source_textures=sources,source_texture_count=len(sources),
                  psd_count=len(rows),user_backups=backups,raw_files=raw_files,
                  iso_modified=False,translation_performed=False,
                  capture_note='UAD anchor-based authoring slots; game animation timing/scaling not decoded or runtime verified.')
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(documents=len(rows),source_textures=len(sources),backups=len(backups),output=str(OUT)),ensure_ascii=False))


def export(work, output):
    """Export only documents containing artwork; preserve all other atlas pixels."""
    assert not output.exists(), 'Refuse to overwrite an export'
    m=json.loads((work/'manifest.json').read_text());atlases={};report=[]
    for s in m['documents']:
        im=artwork(work/s['psd'])
        assert im.size==tuple(s['size']),f"Canvas size changed: {s['psd']}"
        if im.getchannel('A').getbbox() is None:continue
        for p in s['pieces']:
            source=p['source']
            if source not in atlases:
                # Current adopted baseline prevents replacing other title pieces.
                adopted=json.loads((ROOT/'localization/pipeline.json').read_text())['user_artwork_policy']['adopted_assets']
                key=source.split('/',1)[1];path=ROOT/adopted[key] if key in adopted else IMG/(source+'.png')
                atlases[source]=Image.open(path).convert('RGBA')
            target=atlases[source];large_size=tuple(v*4 for v in target.size)
            part=Image.new('RGBA',im.size);clip=tuple(p['clip']);part.paste(im.crop(clip),clip[:2])
            packed=transform(part,large_size,p['forward']);rect=tuple(p['rect']);box=tuple(v*4 for v in rect)
            # Reject significant artwork outside its destination UV rectangle.
            mask=np.array(packed.getchannel('A'));allowed=np.zeros(mask.shape,bool)
            allowed[box[1]:box[3],box[0]:box[2]]=True
            if np.any((mask>32)&~allowed):raise ValueError(f"Artwork exceeds game sprite bounds: {s['psd']}")
            tile=packed.crop(box).resize((rect[2]-rect[0],rect[3]-rect[1]),Image.Resampling.LANCZOS)
            target.paste(tile,rect[:2])
        if s.get('aliases'):
            sources={p['source'] for p in s['pieces']}
            assert len(sources)==1, 'Alias expansion requires a single source atlas'
            source=next(iter(sources))
            for alias in s['aliases']:
                assert digest(RAW/alias)==digest(RAW/source), 'Alias originals no longer match'
                atlases[alias]=atlases[source].copy()
        report.append(s['psd'])
    output.mkdir(parents=True)
    for source,im in atlases.items():
        path=output/(source+'.png');path.parent.mkdir(parents=True,exist_ok=True);im.save(path)
    (output/'report.json').write_text(json.dumps(dict(documents=report,atlas_png_count=len(atlases),iso_modified=False,
        note='Layout export only; game palette/alpha and runtime validation required before ISO insertion.'),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--generate',action='store_true');ap.add_argument('--work',type=Path,default=OUT)
    ap.add_argument('--export',type=Path);a=ap.parse_args()
    if a.generate:generate()
    elif a.export:export(a.work,a.export)
    else:ap.error('Use --generate or --export DIRECTORY')
