#!/usr/bin/env python3
"""Check CRC-scoped PCSX2 compatibility before publishing a Poison Pink ISO.

Produces a sidecar, never patches an ISO or silently installs into a user profile.
CRC follows PCSX2 v2.6.3 ElfObject::GetCRC (XOR of little-endian u32 words).
"""
import argparse
import configparser
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'localization/runtime/pcsx2_compat.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pcsx2_crc(data):
    result = 0
    for (word,) in struct.iter_unpack('<I', data[:len(data) // 4 * 4]):
        result ^= word
    return f'{result:08X}'


def elf_segments(data):
    if data[:6] != b'\x7fELF\x01\x01' or len(data) < 52:
        raise ValueError('Expected little-endian ELF32')
    off = struct.unpack_from('<I', data, 28)[0]
    size, count = struct.unpack_from('<HH', data, 42)
    if size != 32 or off + count * size > len(data):
        raise ValueError('Invalid ELF program headers')
    segments = [struct.unpack_from('<8I', data, off + i * size) for i in range(count)]
    for s in segments:
        if s[0] == 1 and (s[1] + s[4] > len(data) or s[4] > s[5]):
            raise ValueError('Invalid ELF load segment')
    return [s for s in segments if s[0] == 1]


def virtual_offset(data, address, length=4):
    matches = [s[1] + address - s[2] for s in elf_segments(data)
               if s[2] <= address and address + length <= s[2] + s[4]]
    if len(matches) != 1:
        raise ValueError(f'Patch address not uniquely backed by ELF: {address:08X}')
    return matches[0]


def parse_patch(text):
    result = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('patch='):
            continue
        m = re.fullmatch(r'patch=1,EE,([0-9A-Fa-f]{8}),word,([0-9A-Fa-f]{8})(?:\s*//.*)?', line)
        if not m:
            raise ValueError('Unsupported active patch directive: ' + line)
        result.append((int(m[1], 16), int(m[2], 16)))
    if not result or len({a for a, _ in result}) != len(result):
        raise ValueError('Empty or duplicate patch addresses')
    return result


def patch_directives(text):
    return [value for line in text.splitlines()
            if (value := line.split('//', 1)[0].strip())]


def validate_elf(original, target, patch_text):
    """Reject changed targets, surrounding instructions and occupied code caves."""
    checks = []
    for address, value in parse_patch(patch_text):
        # Context protects adjacent instructions and the zero cave surrounding a
        # target, not just the one word that the patch would overwrite.
        start, length = address - 16, 36
        oldpos = virtual_offset(original, start, length)
        newpos = virtual_offset(target, start, length)
        before = original[oldpos:oldpos + length]
        if target[newpos:newpos + length] != before:
            raise ValueError(f'PCSX2 patch context changed at {address:08X}; review required')
        checks.append(dict(address=f'{address:08X}', value=f'{value:08X}',
                           original=original[oldpos + 16:oldpos + 20].hex(),
                           context_sha256=digest(before)))
    return checks


def inspect_iso(iso):
    # Local import avoids a cycle with overlay's publication guard.
    from iso_archive_stage import iso_inventory, exact
    spec = json.loads(SPEC.read_text())
    original = (ROOT / 'Poison Pink (Japan)' / spec['elf']).read_bytes()
    raw = (SPEC.parent / spec['patch_source']).read_bytes()
    if digest(original) != spec['original_elf_sha256'] or pcsx2_crc(original) != spec['original_crc']:
        raise ValueError('Original ELF baseline changed')
    if digest(raw) != spec['patch_source_sha256']:
        raise ValueError('Reviewed PCSX2 patch source changed')
    entries = {e['path']: e for e in iso_inventory(Path(iso))['files']}
    with Path(iso).open('rb') as fp:
        entry = entries[spec['elf']]
        fp.seek(entry['lba'] * 2048)
        target = exact(fp, entry['size'])
        cnf = entries['SYSTEM.CNF']
        fp.seek(cnf['lba'] * 2048)
        if spec['elf'].encode() not in exact(fp, cnf['size']):
            raise ValueError('Unexpected boot executable')
    checks = validate_elf(original, target, raw.decode('utf-8'))
    if len(checks) != spec['patch_count']:
        raise ValueError('Unexpected compatibility patch count')
    crc = pcsx2_crc(target)
    return dict(schema_version=1, serial=spec['serial'], elf_crc=crc,
                elf_sha256=digest(target), original_crc=spec['original_crc'],
                patch_filename=f"{spec['serial']}_{crc}.pnach",
                patch_source_sha256=digest(raw), provenance=spec['provenance'],
                patch_count=len(checks), checks=checks,
                requires_widescreen_patches=True, runtime_verified=False), raw


def publish_sidecar(iso, info, raw, iso_sha256=None):
    dest = Path(str(iso) + '.pcsx2')
    source_root = (ROOT / 'Poison Pink (Japan)').resolve()
    if dest.resolve() == source_root or source_root in dest.resolve().parents:
        raise ValueError('Sidecar output may not be inside the original game folder')
    manifest = dict(info, iso_filename=Path(iso).name, iso_sha256=iso_sha256)
    payloads = {
        'patches/' + info['patch_filename']: raw,
        'manifest.json': (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode(),
        'README.txt': ('PCSX2 2.6.3 / 16:9\npatches 폴더의 pnach를 PCSX2 데이터 폴더의 patches에 복사하고 '
                       '와이드스크린 패치를 켜세요.\nISO의 ELF 주소 검사를 통과한 보정 파일입니다. '
                       '게임 전체 실행 검증을 뜻하지 않습니다.\n이전 상태저장에는 잘못된 화면 배치가 '
                       '남을 수 있습니다. 새로 부팅 후 게임 내 메모리카드에서 불러오세요.\n').encode(),
    }
    if dest.exists():
        if any(not (dest / n).is_file() or (dest / n).read_bytes() != data for n, data in payloads.items()):
            raise ValueError('Existing PCSX2 sidecar differs: ' + str(dest))
        return dest, False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=dest.name + '.', dir=dest.parent))
    try:
        for name, data in payloads.items():
            p = tmp / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        os.rename(tmp, dest)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)
    return dest, True


def inspect_profile(profile, info, raw):
    profile = Path(profile)
    # PCSX2 serializes list entries (e.g. RecursivePaths) as duplicate keys.
    cfg = configparser.ConfigParser(interpolation=None, strict=False)
    cfg.optionxform = str
    cfg.read(profile / 'inis/PCSX2.ini')
    game_settings = list((profile / 'gamesettings').glob(info['serial'] + '*.ini'))
    for p in game_settings:
        if p.stem == info['serial'] + '_' + info['elf_crc']:
            cfg.read(p)
    findings = []
    conflicts = []
    for section in cfg.sections():
        if not re.fullmatch(r'Pad[1-8]', section):
            continue
        for button, binding in cfg.items(section):
            for action, shortcut in cfg.items('Hotkeys') if cfg.has_section('Hotkeys') else []:
                if binding.startswith('Keyboard/') and binding.strip() == shortcut.strip():
                    conflicts.append(dict(pad=section, button=button, hotkey=action, binding=binding))
    if conflicts:
        findings.append('Game inputs overlap emulator hotkeys')
    for key in ['EnablePatches', 'EnableWideScreenPatches', 'EnableGameFixes']:
        if not cfg.getboolean('EmuCore', key, fallback=True):
            findings.append(key + ' is disabled')
    folder = Path(cfg.get('Folders', 'Patches', fallback='patches'))
    folder = folder if folder.is_absolute() else profile / folder
    patch = folder / info['patch_filename']
    if not patch.exists():
        findings.append('CRC-matched patch missing')
    elif patch_directives(patch.read_text()) != patch_directives(raw.decode()):
        findings.append('Installed patch differs from reviewed patch')
    # Do not copy arbitrary old per-game settings into a new CRC automatically.
    for p in game_settings:
        if info['elf_crc'] not in p.stem:
            findings.append('Older per-game settings need review: ' + p.name)
    return dict(profile=str(profile), installed_patch=str(patch), findings=findings,
                game_settings=[str(p) for p in game_settings], input_conflicts=conflicts)


def read_state_ram(path):
    """Read EE RAM only; support PCSX2's Zstd ZIP without extracting any paths."""
    with zipfile.ZipFile(path) as z:
        member = z.getinfo('eeMemory.bin')
        if member.file_size != 32 * 1024 * 1024:
            raise ValueError('Unsupported EE RAM size')
        if member.compress_type != 93:
            return z.read(member)
        with Path(path).open('rb') as f:
            f.seek(member.header_offset)
            header = f.read(30)
            if header[:4] != b'PK\x03\x04':
                raise ValueError('Invalid local ZIP header')
            name_len, extra_len = struct.unpack_from('<HH', header, 26)
            f.seek(name_len + extra_len, 1)
            data = f.read(member.compress_size)
        library = ROOT / 'build/runtime/PCSX2-v2.6.3.app/Contents/Frameworks/libzstd.1.dylib'
        lib = ctypes.CDLL(str(library))
        lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
        lib.ZSTD_decompress.restype = ctypes.c_size_t
        out = ctypes.create_string_buffer(member.file_size)
        size = lib.ZSTD_decompress(out, len(out), data, len(data))
        if size != len(out) or zlib.crc32(out.raw) != member.CRC:
            raise ValueError('State RAM decompression/CRC failed')
        return out.raw


def inspect_states(folder, info, raw):
    results = []
    for path in sorted(Path(folder).glob(info['serial'] + '*.p2s')):
        row = dict(path=str(path))
        if '(' + info['elf_crc'] + ')' not in path.name:
            row['status'] = 'different_elf_crc_do_not_migrate'
        else:
            ram = read_state_ram(path)
            row['missing_patch_words'] = [f'{a:08X}' for a, v in parse_patch(raw.decode())
                                           if struct.unpack_from('<I', ram, a)[0] != v]
            state = struct.unpack_from('<I', ram, 0x62DAF0)[0]
            panel = struct.unpack_from('<f', ram, 0x62DCB4)[0]
            row['active_portrait_dialogue'] = state == 400
            row['cached_panel_y'] = panel
            row['status'] = ('needs_layout_recovery' if state == 400 and panel == 312.0 else
                             'unrecognized_dialogue_layout' if state == 400 and panel != 384.0 else
                             'missing_saved_patch' if row['missing_patch_words'] else
                             'checked_patch_and_known_layout_values')
        results.append(row)
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--iso', required=True, type=Path)
    p.add_argument('--profile', type=Path)
    p.add_argument('--package', action='store_true')
    p.add_argument('--states', type=Path, help='Read-only audit of saved patch/layout values')
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    info, raw = inspect_iso(args.iso)
    if args.package:
        h = hashlib.sha256()
        with args.iso.open('rb') as f:
            for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
                h.update(chunk)
        dest, _ = publish_sidecar(args.iso, info, raw, h.hexdigest())
        info['sidecar'] = str(dest)
    if args.profile:
        info['profile'] = inspect_profile(args.profile, info, raw)
    if args.states:
        info['states'] = inspect_states(args.states, info, raw)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: info[k] for k in ['elf_crc', 'patch_count', 'profile', 'sidecar'] if k in info}, ensure_ascii=False))
    bad_states = [s for s in info.get('states', []) if s['status'] != 'checked_patch_and_known_layout_values']
    return int(bool(info.get('profile', {}).get('findings') or bad_states))


if __name__ == '__main__':
    raise SystemExit(main())
