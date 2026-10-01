#!/usr/bin/env python3
import struct
from disasm_font_init import disasm

with open('Poison Pink (Japan)/SLPS_258.54', 'rb') as f:
    elf_data = f.read()

# Register 28 is $gp
# -20280 is 0xb0c8 (language)
# -20276 is 0xb0cc (language == 6 flag)
target_vars = {
    0xb0c8: "language",
    0xb0cc: "is_korean_flag"
}

print("Tracing language variables in ELF:")
for imm, name in target_vars.items():
    print(f"\n=== References to {name} (-{65536-imm}($gp) / 0x{imm:04x}) ===")
    for off in range(0, 0x00327a00, 4):
        instr = struct.unpack('<I', elf_data[off:off+4])[0]
        if (instr & 0xffff) == imm and ((instr >> 21) & 0x1f) == 28:
            vaddr = off + 0x00100000
            print(f"0x{vaddr:08x}: {instr:08x}  {disasm(instr, vaddr)}")
            # Also print surrounding 3 instructions
            for j in range(1, 4):
                next_w = struct.unpack('<I', elf_data[off+j*4:off+(j+1)*4])[0]
                nvaddr = vaddr + j*4
                print(f"  +0x{j*4:x} (0x{nvaddr:08x}): {next_w:08x}  {disasm(next_w, nvaddr)}")

