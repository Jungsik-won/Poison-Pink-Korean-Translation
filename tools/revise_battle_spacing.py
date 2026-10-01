#!/usr/bin/env python3
"""Revise four victory phrases against original line widths; preserve v3 edits."""
import json
import shutil
import zipfile
from pathlib import Path
from build_battle_titles_euljiro import (
    ROOT,OUT,RAW,reference,group_images,bounded_compile,layered_psd,artwork,
    digest,export,parse,preview_rgba,unpack,Image,ImageDraw,ImageFont,LABEL,np)

BUILD=ROOT/'build/battle_spacing_euljiro_v2'
BASES=('bt_tx05','bt_tx13','bt_tx21','bt_tx25')


def main():
    work=BUILD/'work';assert not work.exists(),'Do not overwrite reviewed revision'
    manifest=json.loads((OUT/'manifest.json').read_text())
    config=json.loads((ROOT/'localization/battle_titles_euljiro.json').read_text())
    texts={r['id']:r['target'] for r in config['rows']};font=Path(config['font'])
    before={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*.psd')}
    docs=[dict(s) for s in manifest['documents'] if s['base'] in BASES]
    assert len(docs)==16
    work.mkdir(parents=True);metrics={};rendered={}
    for base in BASES:
        group=[s for s in docs if s['base']==base]
        variants,info=group_images(texts[base],group,font)
        prior=artwork(OUT/group[0]['psd']);old_widths=[]
        for p in group[0]['pieces']:
            box=prior.crop(tuple(p['clip'])).getchannel('A').getbbox();old_widths.append((box[2]-box[0])/4)
        info['prior_outline_width_native']=old_widths
        metrics[base]=info
        for s,im in zip(group,variants):
            target=work/s['psd'];target.parent.mkdir(parents=True,exist_ok=True)
            layered_psd(target,[('원문_배치기준_내보내기제외',reference(s),False),
                               ('참고_자간보정전_내보내기제외',artwork(OUT/s['psd']),False),
                               ('을지로체_원문폭_자간보정',im,True)],im)
            decoded=artwork(target);a=np.array(decoded).astype(int);b=np.array(im).astype(int)
            assert np.max(abs(a[:,:,3]-b[:,:,3]))<=1
            assert np.max(abs(a[:,:,:3]-b[:,:,:3])[b[:,:,3]>0])<=1
            im.save(target.with_suffix('.png'));rendered[s['id']]=im
            s.update(sha256=digest(target),spacing_reference='original_base_line_width',
                     spacing_report='reports/battle_spacing_euljiro_v2.json')
        for i,p in enumerate(group[0]['pieces']):
            box=variants[0].crop(tuple(p['clip'])).getchannel('A').getbbox()
            assert abs((box[2]-box[0])/4-info['layout_rows'][i]['target_outline_width_native'])<=.25
            assert min(info['layout_rows'][i]['outline_gaps_native'])>=3
        np.testing.assert_array_equal(np.array(variants[0])[:,:,3],np.array(variants[3])[:,:,3])
    (work/'manifest.json').write_text(json.dumps(dict(documents=docs),ensure_ascii=False,indent=2)+'\n')
    export(work,BUILD/'atlas_png');decoded={};textures=[]
    for s in docs:
        source=s['pieces'][0]['source'];raw=(RAW/source).read_bytes()
        image=Image.open(BUILD/'atlas_png'/(source+'.png')).convert('RGBA')
        compiled,checks=bounded_compile(raw,image,[p['rect'] for p in s['pieces']])
        target=BUILD/'textures'/source;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(compiled)
        model=parse(compiled);im=Image.frombytes('RGBA',image.size,preview_rgba(model))
        decoded[source]=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST)
        textures.append(dict(source=source,compiled_sha256=digest(target),checks=checks))
    commons={s['id']:unpack(decoded,s) for s in docs};registration=[]
    for base in BASES:
        group=[s for s in docs if s['base']==base]
        a=np.array(commons[base])[:,:,3]>127;b=np.array(commons[group[3]['id']])[:,:,3]>127
        iou=float(np.count_nonzero(a&b)/np.count_nonzero(a|b))
        assert iou>.93,(base,iou)
        registration.append(dict(base=base,shadow_iou=iou))
    preview=BUILD/'preview';preview.mkdir()
    label=ImageFont.truetype(str(LABEL),24)
    for base in BASES:
        group=[s for s in docs if s['base']==base]
        board=Image.new('RGB',(1100,660),(48,57,65));draw=ImageDraw.Draw(board)
        draw.text((20,16),texts[base].replace('\n',' ')+' · 원문 폭에 맞춘 자간',font=label,fill='white')
        for i,s in enumerate(group):
            x=20+(i%2)*550;y=64+(i//2)*295;draw.text((x,y),s['name'],font=label,fill='white')
            im=commons[s['id']].copy();im.thumbnail((510,250),Image.Resampling.LANCZOS);board.paste(im,(x,y+35),im)
        board.save(preview/f'조건효과_을지로체_{base}.jpg',quality=95)
    im=commons['bt_tx05'].resize((640,320),Image.Resampling.LANCZOS)
    board=Image.new('RGB',im.size,(48,57,65));board.paste(im,(0,0),im);board.save(preview/'모든적격파_강조식자_미리보기.png')
    group=[s for s in docs if s['base']=='bt_tx05'];base=group[0]
    board=Image.new('RGB',(1050,870),(48,57,65));draw=ImageDraw.Draw(board)
    for y,title,im in [(0,'일본어 원문',reference(base)),(290,'수정 전',artwork(OUT/base['psd'])),(580,'수정 후 · 원문 폭, 동일 글자 크기',commons['bt_tx05'])]:
        draw.text((20,y+8),title,font=label,fill='white');im=im.resize((500,250),Image.Resampling.LANCZOS)
        board.paste(im,(270,y+36),im)
    board.save(preview/'모든적격파_원문폭_비교.jpg',quality=95)
    for name,sha in before.items():assert digest(OUT/name)==sha,'User PSD changed during preparation'
    report=dict(font='BMEULJIROTTF.ttf',psds=16,textures=textures,typography=metrics,registration=registration,
                original_psds=before,iso_modified=False,runtime_verified=False,installed=False)
    (BUILD/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(prepared=16,registration=registration,first_phrase=metrics['bt_tx05']),ensure_ascii=False))


def install():
    report=json.loads((BUILD/'report.json').read_text());assert not report['installed']
    docs=json.loads((BUILD/'work/manifest.json').read_text())['documents']
    for name,sha in report['original_psds'].items():assert digest(OUT/name)==sha
    for s in docs:assert digest(BUILD/'work'/s['psd'])==s['sha256']
    backup=OUT/'을지로체_자간보정전_보존.zip';assert not backup.exists()
    names={'manifest.json','먼저읽기.md'}|{s['psd'] for s in docs}|{str(Path(s['psd']).with_suffix('.png')) for s in docs}
    with zipfile.ZipFile(backup,'w',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(names):z.write(OUT/name,name)
    with zipfile.ZipFile(backup) as z:
        assert z.testzip() is None
        for name in names:assert z.read(name)==(OUT/name).read_bytes()
    for s in docs:
        dest=OUT/s['psd'];tmp=dest.with_suffix('.psd.tmp')
        shutil.copy2(BUILD/'work'/s['psd'],tmp);tmp.replace(dest)
        shutil.copy2((BUILD/'work'/s['psd']).with_suffix('.png'),dest.with_suffix('.png'))
    m=json.loads((OUT/'manifest.json').read_text());lookup={s['id']:s for s in docs}
    m['documents']=[lookup.get(s['id'],s) for s in m['documents']]
    m['stage_condition_lettering']['spacing_revision']='reports/battle_spacing_euljiro_v2.json'
    (OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    for p in (BUILD/'preview').iterdir():shutil.copy2(p,OUT/p.name)
    changed={s['psd'] for s in docs}
    for name,sha in report['original_psds'].items():
        if name not in changed:assert digest(OUT/name)==sha
    report.update(installed=True,backup=str(backup.relative_to(ROOT)),untouched_psds=len(report['original_psds'])-16)
    for p in [BUILD/'report.json',ROOT/'reports/battle_spacing_euljiro_v2.json']:
        p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Installed 16 PSDs; preserved other',report['untouched_psds'])


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--install']:install()
    else:main()
