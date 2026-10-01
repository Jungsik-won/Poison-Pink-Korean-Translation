"""Workspace-only savestate renderer probe. Never changes user saves or release ISO."""
import ctypes, struct, zipfile, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/battle_voice_subtitles_v1'

def read_member(path, z, member):
    if member.compress_type != 93: return z.read(member)
    with path.open('rb') as fp:
        fp.seek(member.header_offset); h = fp.read(30)
        assert h[:4] == b'PK\x03\x04'
        name, extra = struct.unpack_from('<HH', h, 26); fp.seek(name + extra, 1)
        compressed = fp.read(member.compress_size)
    lib = ctypes.CDLL(str(ROOT / 'build/runtime/PCSX2-v2.6.3.app/Contents/Frameworks/libzstd.1.dylib'))
    lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_decompress.restype = ctypes.c_size_t
    buf = ctypes.create_string_buffer(member.file_size)
    assert lib.ZSTD_decompress(buf, len(buf), compressed, len(compressed)) == len(buf)
    assert zlib.crc32(buf.raw) == member.CRC
    return buf.raw

def patch_state(source, output, patches):
    if output.exists(): raise ValueError('Probe state already exists')
    with zipfile.ZipFile(source) as z, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as dst:
        for member in z.infolist():
            payload = read_member(source, z, member)
            if member.filename == 'eeMemory.bin':
                payload = bytearray(payload)
                for address, before, after in patches:
                    assert payload[address:address + len(before)] == before, hex(address)
                    payload[address:address + len(after)] = after
                payload = bytes(payload)
            dst.writestr(member.filename, payload)

def words(*items): return struct.pack('<%dI' % len(items), *items)
def jal(address): return 0x0c000000 | address >> 2

def main():
    cave = 0x523300; coordinates = cave + 0x100; color = cave + 0x110; text = cave + 0x120
    # Save caller return, draw one line through the existing game font renderer,
    # then perform the displaced end-of-frame operation with its original return.
    code = words(0x27bdfff0, 0xffbf0000, 0x3c040055, 0x8c8406ec,
        0x3c050052, 0x24a53400, 0x3c060052, 0x24c63410,
        0x3c070052, 0x24e73420, jal(0x1d7348), 0,
        0xdfbf0000, 0x08000000 | 0x1e0aa0 >> 2, 0x27bd0010)
    ram = (OUT / 'eeMemory.bin').read_bytes()
    patches = [(0x1008d8, words(jal(0x1e0aa0)), words(jal(cave))),
        (cave, bytes(len(code)), code),
        (coordinates, bytes(16), struct.pack('<4f', 130, 380, 65535, .85)),
        (color, bytes(4), bytes([255,255,255,128])),
        (text, bytes(32), b'Battle subtitle test\0' + bytes(11))]
    for addr, before, after in patches:
        assert ram[addr:addr+len(before)] == before, hex(addr)
    patch_state(OUT / 'user_slot1_original.p2s', OUT / 'renderer_probe.p2s', patches)
    print(OUT / 'renderer_probe.p2s')

if __name__ == '__main__': main()
