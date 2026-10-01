"""Local ASR working transcripts; output requires listening review before use."""
import json, subprocess, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/battle_voice_subtitles_v1'

def main():
    rows = json.loads((OUT / 'inventory.json').read_text())
    clips = list({r['sha256']: r for r in rows}.values())
    folder = OUT / 'asr'; folder.mkdir(exist_ok=True)
    batches = []
    for n in range(0, len(clips), 24):
        tag = 'batch_%02d' % (n // 24); pcm = bytearray(); cues = []
        for r in clips[n:n+24]:
            with wave.open(str(ROOT / r['audio'])) as fp: body = fp.readframes(fp.getnframes())
            start = len(pcm) / 2 / 22050
            pcm.extend(body); end = len(pcm) / 2 / 22050
            cues.append(dict(tag=r['tag'], sha256=r['sha256'], start=start, end=end, audio=r['audio']))
            pcm.extend(bytes(22050 * 2))
        wav = folder / (tag + '.wav')
        with wave.open(str(wav), 'wb') as fp:
            fp.setnchannels(1); fp.setsampwidth(2); fp.setframerate(22050); fp.writeframes(pcm)
        batches.append(dict(tag=tag, cues=cues))
    (folder / 'batches.json').write_text(json.dumps(batches, ensure_ascii=False, indent=2) + '\n')
    for batch in batches:
        tag = batch['tag']; prefix = folder / tag
        if prefix.with_suffix('.json').exists(): continue
        print('TRANSCRIBING', tag, flush=True)
        with prefix.with_suffix('.log').open('w') as log:
            subprocess.run(['whisper-cli', '-m', str(ROOT / 'build/movie_subtitles_v1/asr/ggml-large-v3-turbo.bin'),
                '-l', 'ja', '-t', '6', '-mc', '0', '-ojf', '-osrt', '-f', str(prefix.with_suffix('.wav')),
                '-of', str(prefix)], stdout=log, stderr=subprocess.STDOUT, check=True)
        print('DONE', tag, flush=True)

if __name__ == '__main__': main()
