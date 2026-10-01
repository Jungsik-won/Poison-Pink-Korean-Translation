#!/usr/bin/env python3
"""Decode the saved Photoshop composite and replace one pinned title texture."""
import io,json,shutil,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageCms
from localization_pipeline import ROOT,file_hash,sha,hed_tree,write_json
from iso_archive_stage import iso_inventory,exact,overlay
from title_artwork import compile_png
from ui_texture_codec import parse,preview_rgba
import build_user_translation_import as verifier

PSD=ROOT/'extracted/original/images/DMAP/dmap/title/tit_tx01.tm2.psd'
PSD_SHA='7c00cf80716f14cd2f3aff93c27f3192a2f39da6a9374c359f16ea7a2eccd95d'
BASE=ROOT/'build/system_messages_v1/Poison Pink (Japan) - Korean system v1.iso'
BASE_SHA='d78c7ae9fc1bf691f76e46e117802c83a131652b743ffd72b1d66603eab4ecbd'
OUT=ROOT/'build/title_psd_v1'
ASSET=ROOT/'localization/artwork/title_user_psd_v1'
REFERENCE='https://github.com/psd-tools/psd-tools/blob/main/src/psd_tools/api/pil_io.py'

def decode_merged(path):
    raw=path.read_bytes()
    assert raw[:6]==b'8BPS\0\1' and struct.unpack_from('>H',raw,12)[0]==4
    assert struct.unpack_from('>HH',raw,22)==(8,3), 'Requires 8-bit RGB PSD'
    p=26
    for _ in range(2):p+=4+struct.unpack_from('>I',raw,p)[0]
    count=struct.unpack_from('>h',raw,p+8)[0]
    assert count<0, 'Merged alpha must be marked by a negative layer count'
    with Image.open(path) as im:
        assert im.mode=='RGBA' and im.size==(512,256)
        profile=ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(im.info['icc_profile']))).strip()
        assert profile=='sRGB IEC61966-2.1', 'Unexpected profile; explicit conversion required'
        a=np.array(im,dtype=np.int32)
    # Photoshop's saved RGB preview is already composited against white. Undo
    # that association before interpreting it as straight RGBA (as psd-tools
    # convert_image_data_to_pil/_remove_white_background does). This decodes the
    # authored image; it does not remove white artwork or alter the alpha plane.
    result=a.copy();alpha=a[:,:,3:4];partial=(alpha[:,:,0]>0)&(alpha[:,:,0]<255)
    restored=np.clip((a[:,:,:3]+alpha-255)*255/np.maximum(alpha,1),0,255).astype(np.int32)
    result[partial,:3]=restored[partial]
    assert np.array_equal(result[:,:,3],a[:,:,3])
    assert np.array_equal(result[alpha[:,:,0]==255],a[alpha[:,:,0]==255])
    recomposited=np.rint((result[:,:,:3]*alpha+255*(255-alpha))/255).astype(np.int32)
    error=int(np.abs(recomposited-a[:,:,:3])[partial].max())
    assert error<=1, 'Decoded colors fail white-composite roundtrip'
    return Image.fromarray(result.astype(np.uint8)),dict(layer_count=abs(count),profile=profile,
        saved_merged_composite=True,white_matte_decoded=True,alpha_unchanged=True,
        composite_roundtrip_max_channel_error=error,reference=REFERENCE)

def main():
    output=OUT/'Poison Pink (Japan) - Korean system and title v2.iso'
    assert not output.exists() and file_hash(PSD)==PSD_SHA
    OUT.mkdir(exist_ok=True);ASSET.mkdir(parents=True,exist_ok=True)
    shutil.copy2(PSD,ASSET/'tit_tx01.tm2.psd')
    authored,decode_check=decode_merged(PSD);png=ASSET/'tit_tx01.png';authored.save(png)
    inv=iso_inventory(BASE);entries={e['path']:e for e in inv['files']}
    with BASE.open('rb') as f:
        h=entries['DATA/DMAP.HED'];d=entries['DATA/DMAP.DAT'];f.seek(h['lba']*2048)
        member=next(e for e in hed_tree(exact(f,h['size']))[0] if e['path']=='dmap/title/tit_tx01.tm2')
        offset=d['lba']*2048+member['offset'];f.seek(offset);old=exact(f,member['size'])
    new,conversion=compile_png(old,png);model=parse(new)
    after=Image.frombytes('RGBA',(512,256),preview_rgba(model));after.save(OUT/'tit_tx01.compiled.png')
    (OUT/'tit_tx01.tm2').write_bytes(new)
    a=np.array(authored);b=np.array(after);mask=np.all(a==255,axis=2)
    raw_palette=np.array([list(c) for c in model['palette']],dtype=np.uint8)
    stored=raw_palette[np.frombuffer(model['indices'],dtype=np.uint8)].reshape(256,512,4)
    previous=np.array(Image.open(ROOT/'localization/artwork/title_user_v1/tit_tx01.png').convert('RGBA'))
    assert np.all(b[mask]==255)
    assert np.all(stored[mask]==255), 'Clipped previews must not hide lower stored white alpha'
    white=dict(input_opaque_white_pixels=int(mask.sum()),preserved_exact_white_pixels=int(mask.sum()),
               start_row_white_pixels=int(mask[:24].sum()),previous_start_row_white_pixels=int(np.all(previous[:24]==255,axis=2).sum()))
    patches=[dict(offset=offset,data=new,expected_sha256=sha(old))]
    iso=overlay(BASE,output,patches,BASE_SHA);assert iso_inventory(output)==inv
    verifier.BASE_HASH=BASE_SHA
    diff=verifier.verify_stream(BASE,output,patches,iso['output_sha256'])
    with output.open('rb') as f:f.seek(offset);assert exact(f,len(new))==new
    report=dict(base_iso=str(BASE.relative_to(ROOT)),base_iso_sha256=BASE_SHA,iso_path=str(output.relative_to(ROOT)),
        source_psd=str(PSD.relative_to(ROOT)),source_psd_sha256=PSD_SHA,png=str(png.relative_to(ROOT)),png_sha256=file_hash(png),
        asset='dmap/title/tit_tx01.tm2',before_tim2_sha256=sha(old),after_tim2_sha256=sha(new),iso_offset=offset,
        decode=decode_check,conversion=conversion,white=white,iso=iso,entire_iso_diff=diff,
        all_other_assets_preserved=True,system_messages_and_text_preserved=True,runtime_verified=False,tool_sha256=file_hash(Path(__file__)))
    write_json(OUT/'manifest.json',report);write_json(ROOT/'reports/title_psd_v1.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
