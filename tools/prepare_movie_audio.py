import sys,json,hashlib,struct,subprocess
from pathlib import Path
from remux_all_movies_with_sound import ag_to_wav
root=Path(__file__).resolve().parents[1];out=root/'build/movie_subtitles_v1';rows=[]
for i in range(1,16):
 tag='s%02d'%i;base=root/'extracted/original/raw/MOVIE/movie'/tag
 ipu=base/(tag+'.ipu');ag=base/(tag+'.ag')
 header=ipu.open('rb').read(16);magic,size,w,h,frames=struct.unpack('<4sIHHI',header)
 assert magic==b'ipum';assert ag.stat().st_size%32768==0
 stereo=out/'audio'/(tag+'_stereo.wav');mono=out/'audio'/(tag+'.wav')
 if not stereo.exists():ag_to_wav(str(ag),str(stereo))
 if not mono.exists():subprocess.run(['/usr/local/bin/ffmpeg','-v','error','-i',str(stereo),'-ar','16000','-ac','1',str(mono)],check=True)
 r=dict(tag=tag,width=w,height=h,frames=frames,duration_ntsc=frames*1001/30000,audio_duration=ag.stat().st_size/32*28/44100,ipu_bytes=ipu.stat().st_size,header_bytes=size,ipu_sha256=hashlib.sha256(ipu.read_bytes()).hexdigest(),ag_sha256=hashlib.sha256(ag.read_bytes()).hexdigest())
 rows.append(r);print(r,flush=True)
(out/'original_inventory.json').write_text(json.dumps(rows,indent=2)+'\n')
