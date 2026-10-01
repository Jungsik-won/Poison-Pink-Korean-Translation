"""Overlay verified caption IPUs into dialogue revision v4, retaining original audio."""
import json,struct,zipfile
from pathlib import Path
from localization_pipeline import hed_tree,sha,file_hash,write_json
from iso_archive_stage import iso_inventory,exact,overlay
import build_user_translation_import as verifier
from build_movie_subtitle_assets import frames
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/semantic_revision_v4/Poison Pink (Japan) - Korean dialogue revision v4.iso'
BASE_SHA='648097edc8f2b19d8efb750e916d769aa8cd128c75323b9d379d08ed6003edc4'
B=ROOT/'build/movie_subtitles_v1'
OUTPUT=B/'Poison Pink (Japan) - Korean movie subtitles v1.iso'
def main():
 assets=json.loads((B/'asset_report.json').read_text());bytag={r['tag']:r for r in assets}
 cues=json.loads((ROOT/'extracted_movies/korean_reviewed_v1/cues.json').read_text());assert set(bytag)==set(cues)
 inv=iso_inventory(BASE);files={r['path']:r for r in inv['files']};he=files['DATA/MOVIE.HED'];de=files['DATA/MOVIE.DAT']
 patches=[];checks=[];all_original=[]
 with BASE.open('rb') as f:
  f.seek(he['lba']*2048);oldhed=exact(f,he['size']);newhed=bytearray(oldhed);members=hed_tree(oldhed)[0]
  for e in members:
   path=e['path'];pos=de['lba']*2048+e['offset'];f.seek(pos);old=exact(f,e['size'])
   src=ROOT/'extracted/original/raw/MOVIE'/path;assert old==src.read_bytes(),(path,'source baseline changed')
   all_original.append(dict(path=path,offset=pos,size=len(old),sha256=sha(old)))
   tag=Path(path).stem
   if not path.endswith('.ipu') or tag not in bytag:continue
   info=bytag[tag];new=(B/'textures'/(tag+'.ipu')).read_bytes()
   assert sha(new)==info['output_sha256'] and sha(old)==info['source_sha256']
   ass=ROOT/'extracted_movies/korean_reviewed_v1'/(tag+'_ko.ass');assert file_hash(ass)==info['ass_sha256']
   assert frames(new)[0]==frames(old)[0];assert len(new)<=len(old)
   patches.append(dict(offset=pos,data=new+bytes(len(old)-len(new)),expected_sha256=sha(old)))
   struct.pack_into('<I',newhed,e['index']*44+4,len(new))
   checks.append(dict(path=path,offset=pos,source_bytes=len(old),output_bytes=len(new),source_sha256=sha(old),output_sha256=sha(new)))
 newmembers=hed_tree(bytes(newhed))[0];sizes={r['path']:r['output_bytes'] for r in checks}
 assert newmembers==[dict(e,size=sizes.get(e['path'],e['size'])) for e in members]
 patches.append(dict(offset=he['lba']*2048,data=bytes(newhed),expected_sha256=sha(oldhed)))
 print('Writing ISO with',len(checks),'captioned movies',flush=True)
 result=overlay(BASE,OUTPUT,patches,BASE_SHA);assert iso_inventory(OUTPUT)==inv
 verifier.BASE_HASH=BASE_SHA
 verified=verifier.verify_stream(BASE,OUTPUT,patches,result['output_sha256'])
 with OUTPUT.open('rb') as f:
  for r in all_original:
   x=next((c for c in checks if c['path']==r['path']),None);f.seek(r['offset'])
   if x:assert sha(exact(f,x['output_bytes']))==x['output_sha256']
   else:assert sha(exact(f,r['size']))==r['sha256']
 report=dict(iso_path=str(OUTPUT.relative_to(ROOT)),iso=result,base_iso=str(BASE.relative_to(ROOT)),base_iso_sha256=BASE_SHA,whole_iso_verification=verified,changed_movies=checks,all_original_movie_members=all_original,original_audio_preserved=True,untouched_video_frames_preserved=True,untouched_videos_preserved=True,dialogue_revision_v4_preserved=True,runtime_verified=False,cue_count=sum(map(len,cues.values())),song_lyrics_applied=all(t in bytag for t in ['s10','s11','s12','s13','s14']))
 report.update(song_lyrics_fully_confirmed=False,translation_review_limits='extracted_movies/korean_reviewed_v1/청취_확인필요.json',credits_layout=dict(tag='s14',content_size=[576,432],frame_size=[640,480],position=[32,0],all_frames_reencoded=True))
 write_json(ROOT/'reports/movie_subtitles_v1.json',report)
 side=Path(str(OUTPUT)+'.pcsx2');manifest=json.loads((side/'manifest.json').read_text());assert manifest['iso_sha256']==result['output_sha256']
 with zipfile.ZipFile(B/'PCSX2_대화표시_호환패키지.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(side.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(side))
 (B/'SHA256SUMS.txt').write_text(result['output_sha256']+'  '+OUTPUT.name+'\n')
 print(json.dumps(dict(iso=report['iso_path'],sha256=result['output_sha256'],verification=verified,cues=report['cue_count']),ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
