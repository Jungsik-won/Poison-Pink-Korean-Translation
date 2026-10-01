"""Extract the indexed mono 22050 Hz battle AGS clips without changing game assets."""
import argparse, hashlib, json, struct, wave
from pathlib import Path
from remux_all_movies_with_sound import decode_block

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/battle_voice_subtitles_v1'

def parse_bank(path):
    data = path.read_bytes()
    reserved, table_size, body_offset, body_size = struct.unpack_from('<4I', data)
    if reserved != 0 or table_size % 8 or body_offset < table_size:
        raise ValueError('Unrecognized AGS header: ' + str(path))
    start = 0x40 + body_offset
    if start + body_size > len(data) or any(data[start + body_size:]):
        raise ValueError('AGS body/trailer boundary')
    rows = []
    for slot in range(table_size // 8):
        offset, size = struct.unpack_from('<II', data, 0x40 + slot * 8)
        if offset % 16 or size % 16 or offset + size > body_size:
            raise ValueError('Invalid clip boundary')
        clip = data[start + offset:start + offset + size]
        if any(clip[i] >> 4 > 4 or clip[i] & 15 > 12 or clip[i + 1] > 7 for i in range(0, size, 16)):
            raise ValueError('Invalid PS ADPCM frame')
        rows.append(dict(slot=slot, offset=offset, size=size, seconds=size / 16 * 28 / 22050,
                         sha256=hashlib.sha256(clip).hexdigest(), clip=clip))
    return rows

def extract(only=None):
    rows = []; seen = {}; audio = OUT / 'audio'; audio.mkdir(parents=True, exist_ok=True)
    banks = sorted((ROOT / 'extracted/original/raw/SOUND/sound/VOICE/jp').glob('kv*/*.ags'))
    for bank in banks:
        if only and bank.parent.name + '/' + bank.stem != only: continue
        clips = parse_bank(bank)
        for r in clips:
            clip = r.pop('clip'); key = r['sha256']; tag = '%s_%s_%02d' % (bank.parent.name, bank.stem, r['slot'])
            r.update(bank=str(bank.relative_to(ROOT)), voice_set=int(bank.parent.name[2:]), character=int(bank.stem), tag=tag)
            if key not in seen:
                wav = audio / (tag + '.wav'); samples = []; hist = [0., 0.]
                for off in range(0, len(clip), 16): samples.extend(decode_block(clip[off:off + 16], hist))
                with wave.open(str(wav), 'wb') as fp:
                    fp.setnchannels(1); fp.setsampwidth(2); fp.setframerate(22050)
                    fp.writeframes(struct.pack('<%dh' % len(samples), *samples))
                seen[key] = str(wav.relative_to(ROOT))
            r['audio'] = seen[key]; rows.append(r)
    target = OUT / ('inventory.json' if not only else 'sample_inventory.json')
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(banks=len(set(r['bank'] for r in rows)), slots=len(rows), unique_clips=len(seen), inventory=str(target))))

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--only'); extract(p.parse_args().only)
