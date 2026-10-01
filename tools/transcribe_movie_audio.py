import subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];b=root/'build/movie_subtitles_v1'
for i in [4,2,3,5,6,7,8,9,1,10,11,12,13,14,15]:
 t='s%02d'%i;out=b/'asr'/t
 if out.with_suffix('.json').exists():continue
 wav=b/'audio'/(t+'.wav')
 print('TRANSCRIBING',t,flush=True)
 with (b/'asr'/(t+'.log')).open('w') as f:
  subprocess.run(['whisper-cli','-m',str(b/'asr/ggml-model.bin'),'-f',str(wav),'-l','ja','-t','6','-bs','5','-bo','5','-ojf','-osrt','-of',str(out)],stdout=f,stderr=subprocess.STDOUT,check=True)
 print('DONE',t,flush=True)
