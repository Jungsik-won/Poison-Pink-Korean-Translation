#!/usr/bin/env python3
import struct

OPCODES = {
    0x00: 'SPECIAL', 0x01: 'REGIMM', 0x02: 'j', 0x03: 'jal', 0x04: 'beq', 0x05: 'bne', 0x06: 'blez', 0x07: 'bgtz',
    0x08: 'addi', 0x09: 'addiu', 0x0a: 'slti', 0x0b: 'sltiu', 0x0c: 'andi', 0x0d: 'ori', 0x0e: 'xori', 0x0f: 'lui',
    0x20: 'lb', 0x21: 'lh', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu', 0x27: 'lwu', 0x28: 'sb', 0x29: 'sh', 0x2b: 'sw',
    0x37: 'ld', 0x3f: 'sd'
}
SPECIAL = {
    0x00: 'sll', 0x02: 'srl', 0x03: 'sra', 0x04: 'sllv', 0x06: 'srlv', 0x07: 'srav',
    0x08: 'jr', 0x09: 'jalr', 0x20: 'add', 0x21: 'addu', 0x22: 'sub', 0x23: 'subu',
    0x24: 'and', 0x25: 'or', 0x26: 'xor', 0x27: 'nor', 0x2a: 'slt', 0x2b: 'sltu'
}
REGS = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
        's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']

def disasm(w, addr):
    op = (w >> 26) & 0x3f
    rs = (w >> 21) & 0x1f
    rt = (w >> 16) & 0x1f
    rd = (w >> 11) & 0x1f
    sh = (w >> 6) & 0x1f
    fn = w & 0x3f
    imm = w & 0xffff
    simm = imm if imm < 0x8000 else imm - 0x10000
    
    if op == 0:
        name = SPECIAL.get(fn, f'spec_{fn:02x}')
        if fn in (0, 2, 3):
            return f'{name:<6} ${REGS[rd]}, ${REGS[rt]}, {sh}'
        elif fn == 8:
            return f'{name:<6} ${REGS[rs]}'
        return f'{name:<6} ${REGS[rd]}, ${REGS[rs]}, ${REGS[rt]}'
    elif op == 0x0f:
        return f'lui    ${REGS[rt]}, 0x{imm:04x}'
    elif op in (0x08, 0x09):
        return f'{OPCODES[op]:<6} ${REGS[rt]}, ${REGS[rs]}, {simm}'
    elif op in (0x20, 0x21, 0x23, 0x24, 0x25, 0x27, 0x28, 0x29, 0x2b, 0x37, 0x3f):
        return f'{OPCODES[op]:<6} ${REGS[rt]}, {simm}(${REGS[rs]})'
    elif op in (0x04, 0x05):
        target = addr + 4 + (simm << 2)
        return f'{OPCODES[op]:<6} ${REGS[rs]}, ${REGS[rt]}, 0x{target:08x}'
    elif op in (2, 3):
        target = (addr & 0xf0000000) | ((w & 0x3ffffff) << 2)
        return f'{OPCODES[op]:<6} 0x{target:08x}'
    return f'op_{op:02x} rs={REGS[rs]}, rt={REGS[rt]}, imm=0x{imm:04x}'

with open('Poison Pink (Japan)/SLPS_258.54', 'rb') as f:
    f.seek(0x000d62f0)
    data = f.read(256)

for i in range(0, len(data), 4):
    w = struct.unpack('<I', data[i:i+4])[0]
    addr = 0x001d62f0 + i
    print(f"0x{addr:08x}: {w:08x}  {disasm(w, addr)}")

