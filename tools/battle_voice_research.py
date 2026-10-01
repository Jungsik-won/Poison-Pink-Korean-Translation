"""Read-only ELF disassembly helpers for the battle subtitle investigation."""
import argparse, ast, struct
from pathlib import Path
from runtime_compat import virtual_offset

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / 'tools/disasm_font_init.py').read_text())
tree.body = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign))]
ns = {}
exec(compile(tree, '<existing disassembler>', 'exec'), ns)

def dump(data, start, end):
    for address in range(start, end, 4):
        word = struct.unpack_from('<I', data, virtual_offset(data, address))[0]
        line = ns['disasm'](word, address)
        if word >> 26 == 0 and word & 63 == 45:
            regs = ns['REGS']; line = 'daddu $%s, $%s, $%s' % (regs[word >> 11 & 31], regs[word >> 21 & 31], regs[word >> 16 & 31])
        print('%08x %08x %s' % (address, word, line))

def calls(data, target):
    word = 0x0c000000 | target >> 2
    for off in range(0x1000, 0x30ed10, 4):
        if struct.unpack_from('<I', data, off)[0] == word:
            print('CALL', hex(off + 0xff000))
            dump(data, off + 0xff000 - 24, off + 0xff000 + 12)

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('start', type=lambda x: int(x, 0)); p.add_argument('end', nargs='?', type=lambda x: int(x, 0)); p.add_argument('--calls', action='store_true')
    args = p.parse_args(); data = (ROOT / 'build/iso_dialogue_fix_v1/SLPS_258.54').read_bytes()
    if args.calls: calls(data, args.start)
    else: dump(data, args.start, args.end or args.start + 256)
