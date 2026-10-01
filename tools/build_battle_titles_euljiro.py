#!/usr/bin/env python3
"""Prepare complete stage/condition lettering, with shared effect masks.

Stages all work separately before replacing any PSD in the user's v3 kit.
Original mesh/UV transforms, palettes, bit depths and file lengths are retained.
"""
import json
from pathlib import Path
import sys
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build/python_psd'))
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
from scipy.ndimage import grey_dilation
from battle_workbench_v3 import OUT,RAW,IMG,unpack,transform,artwork,export,digest
from make_battle_lettering_work import layered_psd,LABEL
from ui_texture_codec import parse,serialize,preview_rgba,unpack_indices
from build_battle_conditions_psd import compile_texture

BUILD=ROOT/'build/battle_titles_euljiro_v1'
WORK=BUILD/'work'


def dilation(mask,radius):
    y,x=np.ogrid[-radius:radius+1,-radius:radius+1]
    return Image.fromarray(grey_dilation(np.array(mask),footprint=x*x+y*y<=radius*radius,mode='constant',cval=0))


def colored(rgb,mask):
    im=Image.new('RGBA',mask.size,(*rgb,0));im.putalpha(mask);return im


def reference(s):
    images={}
    for p in s['pieces']:
        src=p['source'];im=Image.open(IMG/(src+'.png')).convert('RGBA')
        images[src]=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST)
    return unpack(images,s)


def allowed(s):
    """Mask of common pixels actually represented by all source UV pieces."""
    result=Image.new('RGBA',tuple(s['size']))
    for p in s['pieces']:
        m=parse((RAW/p['source']).read_bytes())
        im=Image.new('RGBA',(m['width']*4,m['height']*4))
        x,y,r,b=(v*4 for v in p['rect'])
        im.paste((255,255,255,255),(x,y,r,b))
        common=transform(im,result.size,np.linalg.inv(p['forward']))
        box=tuple(p['clip']);clip=Image.new('RGBA',result.size)
        clip.paste(common.crop(box),box[:2]);result.alpha_composite(clip)
    return result.getchannel('A').point(lambda v:255 if v==255 else 0)


def fit_mask(lines,size,rects,fontpath,margin,maxsize,align='center'):
    """One font size per phrase, no independent stretching of letters."""
    fs=maxsize
    while True:
        font=ImageFont.truetype(str(fontpath),fs)
        boxes=[font.getbbox(line) for line in lines]
        if all(b[2]-b[0]<=r[2]-r[0]-margin*2 and b[3]-b[1]<=r[3]-r[1]-margin*2
               for b,r in zip(boxes,rects)):break
        fs-=1
        assert fs>40,(lines,rects)
    mask=Image.new('L',size);draw=ImageDraw.Draw(mask);placements=[]
    # Equal baselines for heading characters. No per-glyph height centering.
    top=min(b[1] for b in boxes);bottom=max(b[3] for b in boxes)
    for line,b,r in zip(lines,boxes,rects):
        left=r[0]+margin if align=='left' else (r[0]+r[2]-(b[2]-b[0]))//2
        y=(r[1]+r[3]-(bottom-top))//2-top if len(lines)==4 and size[0]==640 else (r[1]+r[3]-(b[3]-b[1]))//2-b[1]
        x=left-b[0];draw.text((x,y),line,font=font,fill=255)
        placements.append(dict(text=line,origin_4x=[x,y]))
    return mask,dict(font_size_native=fs/4,placements=placements)


def effects(mask):
    full=dilation(mask,8)
    base=Image.alpha_composite(colored((255,255,255),full),colored((18,6,3),mask))
    base.putalpha(full)
    red=colored((242,36,2),dilation(full,4).filter(ImageFilter.GaussianBlur(1)))
    glow=colored((241,142,4),ImageChops.subtract(full,mask))
    shadow=colored((18,6,3),full)
    np.testing.assert_array_equal(np.array(base)[:,:,3],np.array(shadow)[:,:,3])
    return [base,red,glow,shadow]


def emphasis_mask(text,size,rects,fontpath,original_line_bounds):
    """Match original line widths with optical gaps, retaining 100/64% type.

    Place actual glyph ink boxes rather than font advances: the Euljiro
    overhangs and the 2px outline otherwise make adjacent letters touch.
    """
    first,last=text.split('\n')
    if first=='모든 적을':spans=[[('모든',1),(' 적을',.64)]]
    else:
        assert first[-1] in '을를'
        spans=[[(first[:-1],1),(first[-1],.64)]]
    assert last=='격파하라'
    spans.append([('격파',1),('하라',.64)])
    targets=[]
    for original,rect in zip(original_line_bounds,rects):
        width=min(original[2]-original[0],rect[2]-rect[0]-24)
        left=max(rect[0]+12,min(original[0],rect[2]-12-width))
        targets.append((left,width))
    fs=240
    while True:
        rows=[]
        for line in spans:
            runs=[];had_space=False
            for span_index,(word,scale) in enumerate(line):
                font=ImageFont.truetype(str(fontpath),round(fs*scale))
                for char in word:
                    if char.isspace():had_space=True;continue
                    glyph=Image.new('L',(fs*3,fs*3))
                    ImageDraw.Draw(glyph).text((fs,fs*2),char,font=font,fill=255,anchor='ls')
                    box=glyph.getbbox();assert box
                    runs.append(dict(char=char,font_size_native=font.size/4,scale=scale,span=span_index,
                                     glyph=glyph.crop(box),top=box[1]-fs*2,bottom=box[3]-fs*2,
                                     gap_weight=1.5 if had_space else (1.2 if runs and runs[-1]['span']!=span_index else 1.0)))
                    had_space=False
            bounds=(0,min(r['top'] for r in runs),sum(r['glyph'].width for r in runs),max(r['bottom'] for r in runs))
            rows.append((runs,bounds))
        # Each outline extends 8 high-res pixels. Require a further 3 native
        # pixels between outlines, and leave room for the larger red halo.
        if all(b[2]+16+28*(len(runs)-1)<=target[1] and b[3]-b[1]<=rect[3]-rect[1]-40
               for (runs,b),rect,target in zip(rows,rects,targets)):break
        fs-=1;assert fs>40
    mask=Image.new('L',size);placements=[];row_metrics=[]
    for row_index,((runs,b),rect,(left,width)) in enumerate(zip(rows,rects,targets)):
        baseline=(rect[1]+rect[3]-(b[3]-b[1]))/2-b[1]
        available=width-16-b[2];weights=sum(r['gap_weight'] for r in runs[1:])
        pen=left+8;glyphs=[];gaps=[];previous_right=None
        for i,run in enumerate(runs):
            if i:pen+=available*run['gap_weight']/weights
            x=round(pen);y=round(baseline)+run['top'];mask.paste(run['glyph'],(x,y))
            if previous_right is not None:gaps.append((x-previous_right-16)/4)
            glyphs.append(dict(char=run['char'],ink_box_4x=[x,y,x+run['glyph'].width,y+run['glyph'].height],scale=run['scale']))
            if i==0 or run['span']!=runs[i-1]['span']:
                word,scale=spans[row_index][run['span']]
                placements.append(dict(text=word,font_size_native=run['font_size_native'],scale=scale,
                                       baseline_origin_4x=[x,round(baseline)]))
            previous_right=x+run['glyph'].width;pen+=run['glyph'].width
        assert min(gaps)>=3
        row_metrics.append(dict(original_bounds_4x=original_line_bounds[row_index],
                                target_outline_left_native=left/4,target_outline_width_native=width/4,
                                outline_gaps_native=gaps,glyphs=glyphs))
    return mask,dict(font_size_native=fs/4,secondary_scale=.64,placements=placements,
                     spacing_reference='original base texture in common coordinates',layout_rows=row_metrics)


def stage_image(text,s,fontpath):
    size=tuple(s['size']);orig=reference(s);bounds=orig.getchannel('A').getbbox()
    # Stage title meshes use a left anchor, not a centered whole strip.
    left=max(0,bounds[0]-16)
    mask,info=fit_mask([text],size,[(left,0,size[0],size[1])],fontpath,20,round(size[1]*.93),'left')
    outer=dilation(mask,12);inner=dilation(mask,6)
    result=colored((248,161,20),outer.filter(ImageFilter.GaussianBlur(3)))
    result.alpha_composite(colored((248,174,35),outer))
    result.alpha_composite(colored((255,253,184),inner))
    result.alpha_composite(colored((18,6,3),mask))
    return result,info


def group_images(text,group,fontpath):
    base=group[0];size=tuple(base['size'])
    valid=Image.new('L',size,255)
    for s in group:valid=ImageChops.darker(valid,allowed(s))
    if base['kind']=='heading':
        assert len(text)==4
        lines=list(text);clips=[p['clip'] for p in base['pieces']]
    else:
        lines=text.split('\n');clips=[p['clip'] for p in base['pieces']]
    assert len(lines)==len(clips)
    rects=[]
    for clip in clips:
        box=valid.crop(tuple(clip)).getbbox();assert box
        rects.append((box[0]+clip[0],box[1]+clip[1],box[2]+clip[0],box[3]+clip[1]))
    if base['kind']=='condition' and len(lines)==2:
        original=reference(base);original_line_bounds=[]
        for clip in clips:
            box=original.crop(tuple(clip)).getchannel('A').getbbox();assert box
            original_line_bounds.append([box[0]+clip[0],box[1]+clip[1],box[2]+clip[0],box[3]+clip[1]])
        mask,info=emphasis_mask(text,size,rects,fontpath,original_line_bounds)
    else:
        margin=8 if base['kind']=='heading' else 16
        mask,info=fit_mask(lines,size,rects,fontpath,margin,min(size[1],256)-16)
        if base['kind']=='heading':
            # Korean glyphs need the original on-screen height, not the narrow
            # atlas cell's padding. Keep width inside each animated glyph cell.
            original_box=reference(base).getchannel('A').getbbox()
            ink=mask.getbbox();target_height=original_box[3]-original_box[1]-16
            strip=mask.crop(ink).resize((ink[2]-ink[0],target_height),Image.Resampling.LANCZOS)
            mask=Image.new('L',size);mask.paste(strip,(ink[0],original_box[1]+8))
            info.update(original_outline_height_native=(original_box[3]-original_box[1])/4,
                        heading_vertical_fit=target_height/(ink[3]-ink[1]))
    variants=effects(mask)
    for im in variants:
        assert not np.any((np.array(im)[:,:,3]>8)&(np.array(valid)==0)), 'Effect exceeds shared safe bounds'
    info['safe_rectangles_4x']=rects
    return variants,info


def bounded_compile(raw,target,rects):
    candidate,checks=compile_texture(raw,target,allow_original_alpha_floor=True)
    model=parse(raw);w,h=model['width'],model['height']
    old=np.frombuffer(unpack_indices(model),np.uint8).reshape(h,w)
    new=np.frombuffer(unpack_indices(parse(candidate)),np.uint8).reshape(h,w)
    mask=np.zeros((h,w),bool)
    for x,y,r,b in rects:mask[y:b,x:r]=True
    result=old.copy();result[mask]=new[mask];flat=result.flatten()
    model['indices']=flat.tobytes() if model['bpp']==8 else bytes(int(flat[i])|int(flat[i+1])<<4 for i in range(0,len(flat),2))
    compiled=serialize(model)
    assert compiled[:64]==raw[:64] and compiled[64+len(model['indices']):]==raw[64+len(model['indices']):]
    assert len(compiled)==len(raw) and serialize(parse(compiled))==compiled
    np.testing.assert_array_equal(result[~mask],old[~mask])
    checks.update(outside_uv_indices_preserved=True,changed_bytes=sum(a!=b for a,b in zip(raw,compiled)))
    return compiled,checks


def main():
    assert not BUILD.exists(),'Never overwrite staged or reviewed work'
    config=json.loads((ROOT/'localization/battle_titles_euljiro.json').read_text())
    fontpath=Path(config['font']);translations={r['id']:r for r in config['rows']}
    manifest=json.loads((OUT/'manifest.json').read_text())
    docs=[dict(s) for s in manifest['documents'] if s['kind'] in ('stage_title','heading','condition')]
    assert len(docs)==86
    before={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*.psd')}
    fontcheck=ImageFont.truetype(str(fontpath),96);missing=bytes(fontcheck.getmask(chr(0x10FFFF)))
    assert all(bytes(fontcheck.getmask(c))!=missing for r in translations.values() for c in r['target'] if not c.isspace())
    groups={};rendered={};typography={}
    for s in docs:
        if s['kind']=='stage_title':
            im,info=stage_image(translations[s['id']]['target'],s,fontpath)
            rendered[s['id']]=im;typography[s['id']]=info
        else:groups.setdefault(s['base'],[]).append(s)
    for base,group in groups.items():
        assert len(group)==4
        variants,info=group_images(translations[base]['target'],group,fontpath)
        for s,im in zip(group,variants):rendered[s['id']]=im;typography[s['id']]=info
    WORK.mkdir(parents=True)
    for s in docs:
        ident=s['id'];im=rendered[ident];row=translations[ident if s['kind']=='stage_title' else s['base']]
        dest=WORK/s['psd'];dest.parent.mkdir(parents=True,exist_ok=True)
        previous=artwork(OUT/s['psd'])
        layers=[('원문_해당형태_내보내기제외',reference(s),False)]
        if previous.getchannel('A').getbbox():layers.append(('참고_이전작업_내보내기제외',previous,False))
        layers.append(('을지로체_한글식자',im,True))
        layered_psd(dest,layers,im)
        decoded=artwork(dest);a=np.array(decoded).astype(int);b=np.array(im).astype(int)
        assert np.max(abs(a[:,:,3]-b[:,:,3]))<=1
        assert np.max(abs(a[:,:,:3]-b[:,:,:3])[b[:,:,3]>0])<=1
        png=dest.with_suffix('.png');im.save(png)
        s.update(original_text=row['source'],translated_text=row['target'],has_existing_korean=True,
                 sha256=digest(dest),lettering_font='BMEULJIROTTF.ttf')
        print(ident,flush=True)
    work_manifest=dict(version=3,documents=docs)
    (WORK/'manifest.json').write_text(json.dumps(work_manifest,ensure_ascii=False,indent=2)+'\n')
    export(WORK,BUILD/'atlas_png')
    finish(docs,before,typography,fontpath)


def finish(docs,before,typography,fontpath):
    config=json.loads((ROOT/'localization/battle_titles_euljiro.json').read_text())
    translations={r['id']:r for r in config['rows']}
    groups={}
    for s in docs:
        assert digest(WORK/s['psd'])==s['sha256'],'Staged PSD changed'
        if s['kind']!='stage_title':groups.setdefault(s['base'],[]).append(s)
    sources={}
    for s in docs:
        for p in s['pieces']:sources.setdefault(p['source'],[]).append(p['rect'])
        for alias in s.get('aliases',[]):sources[alias]=[p['rect'] for p in s['pieces']]
    assert len(sources)==137
    textures=[];decoded_atlases={}
    for source,rects in sorted(sources.items()):
        raw=(RAW/source).read_bytes();target=Image.open(BUILD/'atlas_png'/(source+'.png')).convert('RGBA')
        compiled,checks=bounded_compile(raw,target,rects)
        p=BUILD/'textures'/source;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(compiled)
        model=parse(compiled);preview=Image.frombytes('RGBA',(model['width'],model['height']),preview_rgba(model))
        decoded_atlases[source]=preview.resize((preview.width*4,preview.height*4),Image.Resampling.NEAREST)
        textures.append(dict(source=source,source_sha256=digest(RAW/source),compiled_sha256=digest(p),checks=checks))
    # Post-palette mesh reconstruction measures actual stored effect alignment.
    reconstructed={s['id']:unpack(decoded_atlases,s) for s in docs};metrics=[]
    for base,group in groups.items():
        a=np.array(reconstructed[base])[:,:,3]>127
        b=np.array(reconstructed[group[3]['id']])[:,:,3]>127
        overlap=float(np.count_nonzero(a&b)/np.count_nonzero(a|b))
        coverage=float(np.count_nonzero(a&b)/np.count_nonzero(a))
        assert overlap>.70 and coverage>.80,(base,overlap,coverage)
        metrics.append(dict(base=base,shadow_iou=overlap,shadow_covers_base=coverage,
                            authored_shadow_alpha_exact=True))
    preview_dir=BUILD/'preview';preview_dir.mkdir(exist_ok=True)
    for ident,im in reconstructed.items():im.save(preview_dir/(ident+'.png'))
    label=ImageFont.truetype(str(LABEL),24)
    stage=[s for s in docs if s['kind']=='stage_title']
    for start in range(0,len(stage),9):
        board=Image.new('RGB',(1220,1040),(42,48,54));draw=ImageDraw.Draw(board)
        draw.text((20,14),'계층 · 장소명 / 을지로체 / 게임용 팔레트 변환 후',font=label,fill='white')
        for n,s in enumerate(stage[start:start+9]):
            y=58+n*108;draw.text((22,y),s['id'],font=label,fill=(174,188,203))
            im=reconstructed[s['id']].copy();im.thumbnail((1170,76),Image.Resampling.LANCZOS);board.paste(im,(24,y+26),im)
        board.save(preview_dir/f'계층장소명_을지로체_{start//9+1:02}.jpg',quality=94)
    for base,group in groups.items():
        board=Image.new('RGB',(1100,660),(48,57,65));draw=ImageDraw.Draw(board)
        draw.text((20,16),translations[base]['target'].replace('\n',' '),font=label,fill='white')
        for n,s in enumerate(group):
            x=20+(n%2)*550;y=64+(n//2)*295
            draw.text((x,y),s['name'],font=label,fill='white')
            im=reconstructed[s['id']].copy();im.thumbnail((510,250),Image.Resampling.LANCZOS);board.paste(im,(x,y+35),im)
        board.save(preview_dir/f'조건효과_을지로체_{base}.jpg',quality=95)
    for p,sha in before.items():assert digest(OUT/p)==sha,'User PSD changed during preparation'
    report=dict(font_path=str(fontpath),font_sha256=digest(fontpath),phrase_count=62,
                staged_psd_count=86,texture_count=137,originals=before,typography=typography,
                textures=textures,registration=metrics,iso_modified=False,runtime_verified=False,
                installed_in_v3=False,psd_compositing_rounding_tolerance=1)
    (BUILD/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('originals','typography','textures')},ensure_ascii=False))


def install():
    """Promote reviewed PSDs in place, keeping exact prior files in a ZIP."""
    report=json.loads((BUILD/'report.json').read_text())
    assert not report['installed_in_v3'],'Already installed'
    incoming=json.loads((WORK/'manifest.json').read_text())['documents']
    for name,sha in report['originals'].items():assert digest(OUT/name)==sha,'User PSD changed; preserve new edit'
    for s in incoming:assert digest(WORK/s['psd'])==s['sha256']
    backup=OUT/'을지로체_자동식자전_보존.zip';assert not backup.exists()
    names={'manifest.json','먼저읽기.md'}|{s['psd'] for s in incoming}
    names|={str(Path(s['psd']).with_suffix('.png')) for s in incoming if (OUT/Path(s['psd']).with_suffix('.png')).exists()}
    with zipfile.ZipFile(backup,'w',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(names):z.write(OUT/name,name)
    with zipfile.ZipFile(backup) as z:
        assert z.testzip() is None
        for name in names:assert z.read(name)==(OUT/name).read_bytes()
    manifest=json.loads((OUT/'manifest.json').read_text());lookup={s['id']:s for s in incoming}
    for s in incoming:
        target=OUT/s['psd'];tmp=target.with_suffix('.psd.tmp');shutil.copy2(WORK/s['psd'],tmp);tmp.replace(target)
        shutil.copy2((WORK/s['psd']).with_suffix('.png'),target.with_suffix('.png'))
    for i,s in enumerate(manifest['documents']):
        if s['id'] in lookup:manifest['documents'][i]=lookup[s['id']]
    manifest['translation_performed']=True
    manifest['stage_condition_lettering']=dict(font='BMEULJIROTTF.ttf',phrases=62,psds=86,textures=137,
        original_backup=backup.name,iso_modified=False,runtime_verified=False,secondary_text_scale=.64,
        report='reports/battle_titles_euljiro_v1.json')
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    for p in (BUILD/'preview').glob('*.jpg'):shutil.copy2(p,OUT/p.name)
    im=Image.open(BUILD/'preview/bt_tx05.png').convert('RGBA');im.thumbnail((640,320),Image.Resampling.LANCZOS)
    board=Image.new('RGB',im.size,(48,57,65));board.paste(im,(0,0),im)
    board.save(OUT/'모든적격파_강조식자_미리보기.png')
    changed={s['psd'] for s in incoming}
    for name,sha in report['originals'].items():
        if name not in changed:assert digest(OUT/name)==sha
    report.update(installed_in_v3=True,original_backup=str(backup.relative_to(ROOT)),backup_sha256=digest(backup),
                  checks_passed=10,unmodified_other_psds=len(report['originals'])-len(changed))
    for p in [BUILD/'report.json',ROOT/'reports/battle_titles_euljiro_v1.json']:
        p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(installed_psds=len(incoming),backup=str(backup),unchanged_psds=report['unmodified_other_psds']),ensure_ascii=False))


if __name__=='__main__':
    if sys.argv[1:]==['--install-v3']:install()
    elif sys.argv[1:]==['--finish-prepared']:
        assert not (BUILD/'report.json').exists(),'Prepared report already exists'
        docs=json.loads((WORK/'manifest.json').read_text())['documents']
        before={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*.psd')}
        config=json.loads((ROOT/'localization/battle_titles_euljiro.json').read_text())
        finish(docs,before,{},Path(config['font']))
    else:main()
