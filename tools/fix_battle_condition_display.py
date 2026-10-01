"""Fix heading scale and the defeat body's real 40px UV viewport; retain v3 work."""
import copy
import json
import shutil
import zipfile
from pathlib import Path
from build_battle_titles_euljiro import (ROOT,OUT,RAW,reference,group_images,bounded_compile,
    layered_psd,artwork,digest,export,parse,preview_rgba,unpack,Image,ImageDraw,ImageFont,LABEL,np)
from battle_workbench_v3 import condition_specs
from localization_pipeline import sha,hed_tree,write_json
from iso_archive_stage import iso_inventory,exact,overlay
import build_user_translation_import as verifier

B=ROOT/'build/battle_condition_display_v1'
BASE=ROOT/'build/movie_subtitles_v1/Poison Pink (Japan) - Korean movie subtitles v1.iso'
BASE_SHA='168d0d707f4f77c4163954912832d021a5b51e6cf93cd22cfe2f20cc40af642a'
ISO=B/'Poison Pink (Japan) - Korean movies and battle display v1.iso'
BASES=('title_s_base','title_h_base','bt_tx09','bt_tx17')

def prepare():
    work=B/'work';assert not work.exists()
    manifest=json.loads((OUT/'manifest.json').read_text())
    config=json.loads((ROOT/'localization/battle_titles_euljiro.json').read_text())
    texts={r['id']:r['target'] for r in config['rows']};font=Path(config['font'])
    before={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*.psd')}
    docs=[copy.deepcopy(s) for s in manifest['documents'] if s['base'] in BASES];assert len(docs)==16
    fixed={s['id']:s for s in condition_specs()}
    for s in docs:s['pieces']=fixed[s['id']]['pieces']
    work.mkdir(parents=True);metrics={};rendered={}
    for base in BASES:
        group=[s for s in docs if s['base']==base]
        images,info=group_images(texts[base],group,font)
        prior=artwork(OUT/group[0]['psd']);original=reference(group[0])
        info.update(before_bounds_4x=prior.getbbox(),original_bounds_4x=original.getbbox(),after_bounds_4x=images[0].getbbox())
        if base.startswith('title'):
            a=images[0].getbbox();o=original.getbbox();assert abs((a[3]-a[1])-(o[3]-o[1]))<=2
        else:
            # Old baseline extended to y49.5 native while mesh ends at ~39.2.
            assert images[0].getbbox()[3]<=148 and prior.getbbox()[3]>156
        metrics[base]=info
        for s,im in zip(group,images):
            dest=work/s['psd'];dest.parent.mkdir(parents=True,exist_ok=True)
            layered_psd(dest,[('원문_배치기준_내보내기제외',reference(s),False),
                             ('참고_보정전_내보내기제외',artwork(OUT/s['psd']),False),
                             ('을지로체_표시범위_크기보정',im,True)],im)
            decoded=artwork(dest)
            assert np.max(abs(np.array(decoded)[:,:,3].astype(int)-np.array(im)[:,:,3].astype(int)))<=1
            im.save(dest.with_suffix('.png'));rendered[s['id']]=im
            s.update(sha256=digest(dest),display_fix_report='reports/battle_condition_display_v1.json')
    (work/'manifest.json').write_text(json.dumps(dict(documents=docs),ensure_ascii=False,indent=2)+'\n')
    export(work,B/'atlas_png');sources={};decoded={};textures=[]
    for s in docs:
        for p in s['pieces']:sources.setdefault(p['source'],[]).append(p['rect'])
    assert len(sources)==9
    preview=B/'preview';preview.mkdir()
    for source,rects in sources.items():
        raw=(RAW/source).read_bytes();im=Image.open(B/'atlas_png'/(source+'.png')).convert('RGBA')
        data,checks=bounded_compile(raw,im,rects)
        dest=B/'textures'/source;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        m=parse(data);p=Image.frombytes('RGBA',(m['width'],m['height']),preview_rgba(m))
        decoded[source]=p.resize((p.width*4,p.height*4),Image.Resampling.NEAREST)
        textures.append(dict(source=source,compiled_sha256=digest(dest),checks=checks))
    common={s['id']:unpack(decoded,s) for s in docs};registration=[]
    for base in BASES:
        group=[s for s in docs if s['base']==base]
        a=np.array(common[base])[:,:,3]>127;b=np.array(common[group[3]['id']])[:,:,3]>127
        iou=float(np.count_nonzero(a&b)/np.count_nonzero(a|b));assert iou>.80,(base,iou)
        coverage=float(np.count_nonzero(a&b)/np.count_nonzero(a));assert coverage>.87,(base,coverage)
        registration.append(dict(base=base,shadow_iou=iou,shadow_coverage=coverage))
        for s in group:common[s['id']].save(preview/(s['id']+'.png'))
        canvas=Image.new('RGB',(1080,600),(46,55,61));draw=ImageDraw.Draw(canvas);label=ImageFont.truetype(str(LABEL),24)
        for y,title,im in [(15,'원문',reference(group[0])),(205,'이전 식자',artwork(OUT/group[0]['psd'])),(395,'수정 후 · 게임 표시 범위 기준',common[base])]:
            draw.text((20,y),title,font=label,fill='white')
            im=im.copy();im.thumbnail((1000,140),Image.Resampling.LANCZOS);canvas.paste(im,(25,y+35),im)
        canvas.save(preview/(base+'_comparison.png'))
    for name,h in before.items():assert digest(OUT/name)==h
    report=dict(original_psds=before,psds=16,textures=textures,typography=metrics,registration=registration,
                installed=False,runtime_verified=False,cause='Defeat UV samples about 40 of 64 rows; old layout centered in all 64. Heading ink height was 68-69 percent of original.',base_iso_sha256=BASE_SHA)
    write_json(B/'report.json',report)
    print(json.dumps(dict(prepared=16,textures=9,registration=registration,typography=metrics),ensure_ascii=False),flush=True)

def install():
    r=json.loads((B/'report.json').read_text());assert not r['installed']
    docs=json.loads((B/'work/manifest.json').read_text())['documents']
    for name,h in r['original_psds'].items():assert digest(OUT/name)==h
    names={'manifest.json','먼저읽기.md'}|{s['psd'] for s in docs}|{str(Path(s['psd']).with_suffix('.png')) for s in docs}
    backup=OUT/'표시범위_크기보정전_보존.zip';assert not backup.exists()
    with zipfile.ZipFile(backup,'w',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(names):z.write(OUT/name,name)
    with zipfile.ZipFile(backup) as z:
        assert z.testzip() is None
        for name in names:assert z.read(name)==(OUT/name).read_bytes()
    for s in docs:
        source=B/'work'/s['psd'];assert digest(source)==s['sha256']
        shutil.copy2(source,OUT/s['psd']);shutil.copy2(source.with_suffix('.png'),(OUT/s['psd']).with_suffix('.png'))
    m=json.loads((OUT/'manifest.json').read_text());lookup={s['id']:s for s in docs}
    m['documents']=[lookup.get(s['id'],s) for s in m['documents']]
    m['condition_display_fix']='reports/battle_condition_display_v1.json'
    (OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    for p in (B/'preview').glob('*comparison.png'):shutil.copy2(p,OUT/p.name)
    changed={s['psd'] for s in docs}
    for name,h in r['original_psds'].items():
        if name not in changed:assert digest(OUT/name)==h
    r.update(installed=True,backup=str(backup.relative_to(ROOT)),untouched_psds=len(r['original_psds'])-16)
    write_json(B/'report.json',r);write_json(ROOT/'reports/battle_condition_display_v1.json',r)
    print('Installed in existing v3; prior work backed up',flush=True)

def build():
    r=json.loads((B/'report.json').read_text());assert r['installed']
    inventory=iso_inventory(BASE);files={e['path']:e for e in inventory['files']};patches=[];entries=[]
    with BASE.open('rb') as f:
        he=files['DATA/DMAP.HED'];de=files['DATA/DMAP.DAT'];f.seek(he['lba']*2048)
        members={e['path']:e for e in hed_tree(exact(f,he['size']))[0]}
        for row in r['textures']:
            source=row['source'];e=members[source.split('/',1)[1]];data=(B/'textures'/source).read_bytes()
            assert sha(data)==row['compiled_sha256'] and len(data)==e['size']
            pos=de['lba']*2048+e['offset'];f.seek(pos);old=exact(f,e['size'])
            assert parse(old)['header']==parse(data)['header'] and parse(old)['palette']==parse(data)['palette']
            patches.append(dict(offset=pos,data=data,expected_sha256=sha(old)))
            entries.append(dict(source=source,offset=pos,size=len(data),before_sha256=sha(old),after_sha256=sha(data)))
    print('Writing final movie + battle display ISO',flush=True)
    result=overlay(BASE,ISO,patches,BASE_SHA);assert iso_inventory(ISO)==inventory
    verifier.BASE_HASH=BASE_SHA;verified=verifier.verify_stream(BASE,ISO,patches,result['output_sha256'])
    with ISO.open('rb') as f:
        for row in entries:f.seek(row['offset']);assert sha(exact(f,row['size']))==row['after_sha256']
    r.update(iso_path=str(ISO.relative_to(ROOT)),base_iso=str(BASE.relative_to(ROOT)),iso=result,whole_iso_verification=verified,replacements=entries,movie_subtitles_preserved=True)
    write_json(B/'report.json',r);write_json(ROOT/'reports/battle_condition_display_v1.json',r)
    (B/'SHA256SUMS.txt').write_text(result['output_sha256']+'  '+ISO.name+'\n')
    print(json.dumps(dict(iso=r['iso_path'],sha256=result['output_sha256'],verification=verified),ensure_ascii=False),flush=True)

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--install']:install()
    elif sys.argv[1:]==['--build']:build()
    else:prepare()
