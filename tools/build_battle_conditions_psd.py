#!/usr/bin/env python3
"""Import five pinned user PSDs, retaining authored glyph rasters and effect variants.

Local dependencies: build/python_psd (psd-tools 1.19.0, scipy, Pillow, numpy).
--prepare-only performs conversion and checks without writing an ISO.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'build/python_psd'))
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from scipy.ndimage import grey_dilation
from localization_pipeline import file_hash, sha, hed_tree, write_json
from iso_archive_stage import iso_inventory, exact, overlay
from ui_texture_codec import parse, serialize, preview_rgba, unpack_indices
from title_artwork import prefer_opaque_palette_entries
import build_user_translation_import as verifier

BASE = ROOT/'build/title_alpha_v1/Poison Pink (Japan) - Korean title alpha fix.iso'
BASE_SHA = '6abf192f3a386b4e1bbc781bba7d02d2e1bdfa04894640b2cda4b6be0aeb4a56'
OUT = ROOT/'build/battle_conditions_psd_v1'
ART = ROOT/'localization/artwork/battle_conditions_user_v1'
HASHES = {
    4: '5a0d47a722b86ed7326add64bd5545133fc4673ae5d197a9d9904d39a7041589',
    5: '5f7dd08b367146b75d3d222ae6d0926889ce6390c6eace650461de256c7a1797',
    6: '829e815c64b8cac327479c96558af1d434d3515f75528c98173cf4c6778e6394',
    7: '26fc3350045529c34fd47796d14b9551b82a2c8f905aaf0d080f474f3a006862',
    8: '63d717a9c4c88c3e13dc0c8519d94639940c1f4fea477975a7c6046b707e2e21',
}
# Verified original heading UV regions (native pixels). Do not rescale glyphs
# independently: user placement within each region is meaningful to animation.
HEADING_RECTS = [(0,0,136,40),(0,40,136,40),(0,80,136,40),(0,120,136,40),
    (136,80,80,56),(136,136,73,56),(136,40,40,40),(176,40,40,40),
    (216,40,40,40),(216,80,40,40),(216,120,40,40),(216,0,40,40),
    (136,0,40,40),(176,0,40,40)]


def snapshot(n):
    target = ART/f'bt_tx{n:02d}.psd'
    if not target.exists():
        kit = ROOT/'outputs/battle_lettering_work_v2'
        folder = kit/('01_승리패배_제목' if n == 4 else '03_모든적격파')
        matches = list(folder.glob('*(*)*.psd' if n == 4 else f'bt_tx{n:02d}*.psd'))
        assert len(matches) == 1
        assert file_hash(matches[0]) == HASHES[n], 'User source changed; review before importing'
        shutil.copy2(matches[0], target)
    assert file_hash(target) == HASHES[n]
    return target


def solid(size, color, alpha):
    im = Image.new('RGBA', size, tuple(color)+(0,))
    im.putalpha(alpha)
    return im


def render(n, path):
    psd = PSDImage.open(path)
    assert psd.size == (1024,1024 if n == 4 else 512)
    result = Image.new('RGBA', psd.size)
    glyph_mask = Image.new('L', psd.size)
    audit = []
    for layer in psd:
        row = dict(name=layer.name, visible=layer.visible, bbox=list(layer.bbox))
        audit.append(row)
        if not layer.visible or layer.name.startswith(('원본_', '확인배경_')):
            row['included'] = False
            continue
        assert not layer.is_group() and layer.opacity == 255 and layer.blend_mode.value == b'norm'
        ink = layer.topil().convert('RGBA')
        row['included'] = True
        if ink.getchannel('A').getbbox() is None:
            row['empty'] = True
            continue
        dx,dy = (-4,6) if n == 8 and layer.kind == 'type' else (0,0)
        row['translation_at_4x'] = [dx,dy]
        x,y = layer.left+dx,layer.top+dy
        assert x >= 0 and y >= 0 and x+ink.width <= psd.width and y+ink.height <= psd.height
        alpha = Image.new('L', psd.size)
        alpha.paste(ink.getchannel('A'), (x,y))
        if layer.kind == 'type':
            glyph_mask = Image.fromarray(np.maximum(np.array(glyph_mask),np.array(alpha)))
        canvas = Image.new('RGBA', psd.size)
        canvas.paste(ink, (x,y))
        strokes = []
        row['effects'] = []
        for effect in layer.effects:
            if not effect.enabled:
                continue
            assert effect.opacity == 100 and effect.blend_mode == b'Nrml'
            color = tuple(round(float(effect.color[k])) for k in (b'Rd  ',b'Grn ',b'Bl  '))
            kind = type(effect).__name__
            record = dict(type=kind,color=color)
            row['effects'].append(record)
            if kind == 'ColorOverlay':
                canvas = solid(psd.size, color, alpha)
            elif kind == 'Stroke':
                assert effect.position == b'OutF' and effect.fill_type == b'SClr'
                radius = int(effect.size)
                assert radius == effect.size == 8
                yy,xx = np.ogrid[-radius:radius+1,-radius:radius+1]
                expanded = grey_dilation(np.array(alpha),footprint=xx*xx+yy*yy <= radius*radius,
                                         mode='constant',cval=0)
                strokes.append(solid(psd.size,color,Image.fromarray(expanded)))
                record['outside_radius_at_4x'] = radius
            else:
                raise ValueError(f'Unsupported user effect: {kind}')
        # Rendering full-canvas strokes avoids psd-tools' layer-bbox clipping.
        composed = Image.new('RGBA',psd.size)
        for stroke in strokes:
            composed.alpha_composite(stroke)
        composed.alpha_composite(canvas)
        result.alpha_composite(composed)
    result.save(ART/f'bt_tx{n:02d}_4x.png')
    size = (psd.width//4,psd.height//4)
    if n == 4:
        mask = Image.new('L',psd.size)
        native = Image.new('RGBA',size)
        for x,y,w,h in HEADING_RECTS:
            box = (x*4,y*4,(x+w)*4,(y+h)*4)
            mask.paste(255,box)
            native.paste(result.crop(box).resize((w,h),Image.Resampling.LANCZOS),(x,y))
        assert not np.any((np.array(mask)==0) & (np.array(result)[:,:,3]>0)), 'Ink outside heading UVs'
    else:
        native = result.resize(size,Image.Resampling.LANCZOS)
    native.save(ART/f'bt_tx{n:02d}.png')
    return native, glyph_mask, audit


def compile_texture(raw, image, allow_original_alpha_floor=False):
    model = parse(raw)
    assert image.size == (model['width'],model['height'])
    target = np.array(image,dtype=np.int32).reshape(-1,4)
    palette = np.array([list(c[:3])+[min(c[3]*2,255)] for c in model['palette']],dtype=np.int32)
    def pm(a):
        a=a.copy();a[:,:3]=(a[:,:3]*a[:,3:4]+127)//255
        return a
    pal,values = pm(palette),pm(target)
    indices = np.empty(len(target),dtype=np.uint8)
    for start in range(0,len(target),1024):
        distances = ((values[start:start+1024,None,:]-pal[None,:,:])**2).sum(axis=2)
        indices[start:start+1024] = distances.argmin(axis=1)
    corrected = prefer_opaque_palette_entries(indices,target,model['palette'])
    ties = int(np.count_nonzero(corrected!=indices));indices=corrected
    model['indices'] = (indices.tobytes() if model['bpp']==8 else
        bytes(int(indices[i]) | int(indices[i+1])<<4 for i in range(0,len(indices),2)))
    result = serialize(model)
    assert result[:64] == raw[:64] and result[64+len(model['indices']):] == raw[64+len(model['indices']):]
    assert len(result) == len(raw) and serialize(parse(result)) == result and result != raw
    assert unpack_indices(parse(result)) == indices.tobytes()
    background_alpha=int(palette[:,3].min()) if allow_original_alpha_floor else 0
    assert np.all(palette[indices[target[:,3]==0],3]==background_alpha), 'Background must retain the original transparency floor'
    errors = pal[indices]-values
    return result,dict(bpp=model['bpp'],size=list(image.size),header_and_palette_preserved=True,
        byte_exact_roundtrip=True,opaque_alpha_ties_corrected=ties,
        minimum_background_preview_alpha=background_alpha,
        changed_bytes=sum(a!=b for a,b in zip(raw,result)),
        premultiplied_preview_rmse=float(np.sqrt(np.mean(errors.astype(np.float64)**2))),
        alpha_metric='Clipped preview; does not predict draw-time game opacity')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare-only',action='store_true');args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);ART.mkdir(parents=True,exist_ok=True)
    output=OUT/'Poison Pink (Japan) - Korean battle conditions v1.iso'
    assert args.prepare_only or not output.exists(), 'Never overwrite an existing ISO'
    inv=iso_inventory(BASE);entries={e['path']:e for e in inv['files']}
    patches=[];checks=[];masks={}
    with BASE.open('rb') as fp:
        he=entries['DATA/DMAP.HED'];de=entries['DATA/DMAP.DAT']
        fp.seek(he['lba']*2048);members={e['path']:e for e in hed_tree(exact(fp,he['size']))[0]}
        for n in range(4,9):
            psd=snapshot(n);png,mask,layers=render(n,psd);masks[n]=mask
            path=f'dmap/map/bstart/bt_tx{n:02d}.tm2';e=members[path]
            offset=de['lba']*2048+e['offset'];fp.seek(offset);raw=exact(fp,e['size'])
            assert raw==(ROOT/'extracted/original/raw/DMAP'/path).read_bytes()
            new,conversion=compile_texture(raw,png)
            (OUT/f'bt_tx{n:02d}.tm2').write_bytes(new)
            model=parse(new)
            Image.frombytes('RGBA',png.size,preview_rgba(model)).save(OUT/f'bt_tx{n:02d}_compiled.png')
            patches.append(dict(offset=offset,data=new,expected_sha256=sha(raw)))
            checks.append(dict(path=path,psd=str(psd.relative_to(ROOT)),psd_sha256=HASHES[n],
                png=str((ART/f'bt_tx{n:02d}.png').relative_to(ROOT)),
                png_sha256=file_hash(ART/f'bt_tx{n:02d}.png'),iso_offset=offset,
                before_sha256=sha(raw),after_sha256=sha(new),layers=layers,conversion=conversion))
    assert masks[5].tobytes()==masks[8].tobytes(), 'Main and shadow glyph masks must register exactly'
    report=dict(base_iso=str(BASE.relative_to(ROOT)),base_iso_sha256=BASE_SHA,
        iso_path=str(output.relative_to(ROOT)),assets=checks,
        checks=dict(heading_ink_inside_original_uv_regions=True,main_shadow_glyph_masks_identical=True,
            original_reference_layers_excluded=True,hidden_user_layers_remain_hidden=True),
        effect_renderer='Saved user glyph alpha; full-canvas circular dilation for 8px outside strokes; solid color overlays. Not a Photoshop-perfect rasterizer.',
        adjustments='bt_tx08 type layers translated (-4,+6) pixels at 4x to match bt_tx05; variant-specific original atlas layouts retained.',
        tool_sha256=file_hash(Path(__file__)),runtime_verified=False,
        limitations=['16-color effects use original palette approximation.',
            'Actual animation timing, overlap and draw-time alpha require game verification.'])
    if args.prepare_only:
        write_json(OUT/'prepare.json',report)
    else:
        iso=overlay(BASE,output,patches,BASE_SHA)
        assert iso_inventory(output)==inv
        verifier.BASE_HASH=BASE_SHA
        diff=verifier.verify_stream(BASE,output,patches,iso['output_sha256'])
        report.update(iso=iso,entire_iso_diff=diff,all_other_bytes_preserved=True)
        write_json(OUT/'manifest.json',report)
        write_json(ROOT/'reports/battle_conditions_psd_v1.json',report)
    print(json.dumps(dict(prepared=len(checks),built=not args.prepare_only,
        output=str(output),checks=report['checks'],conversions=[r['conversion'] for r in checks]),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
