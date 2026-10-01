#!/usr/bin/env python3
import os
import struct

def analyze_elf(path):
    with open(path, 'rb') as f:
        elf_header = f.read(52)
    
    magic, e_class, e_data, e_version = elf_header[:4], elf_header[4], elf_header[5], elf_header[6]
    print(f"ELF Magic: {magic.hex()} ({magic})")
    print(f"Class: {'32-bit' if e_class == 1 else '64-bit'}")
    print(f"Data: {'Little endian' if e_data == 1 else 'Big endian'}")
    print(f"Version: {e_version}")
    
    e_type, e_machine, e_version2, e_entry, e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack('<HHIIIIIHHHHHH', elf_header[16:52])
    
    print(f"Type: {e_type} (2=EXEC)")
    print(f"Machine: 0x{e_machine:04x} (MIPS)")
    print(f"Entry point: 0x{e_entry:08x}")
    print(f"Program header offset: 0x{e_phoff:x}, entries: {e_phnum}")
    print(f"Section header offset: 0x{e_shoff:x}, entries: {e_shnum}, shstrndx: {e_shstrndx}")
    
    # Read sections if available
    with open(path, 'rb') as f:
        f.seek(e_shoff)
        sh_data = f.read(e_shentsize * e_shnum)
        
        # shstrndx section
        if e_shstrndx < e_shnum:
            shstr_header = sh_data[e_shstrndx*e_shentsize:(e_shstrndx+1)*e_shentsize]
            shstr_offset = struct.unpack('<IIIIIIIIII', shstr_header)[4]
            f.seek(shstr_offset)
            shstrtab = f.read(struct.unpack('<IIIIIIIIII', shstr_header)[5])
        else:
            shstrtab = b''
            
        print("\nELF Sections:")
        for i in range(e_shnum):
            sh = sh_data[i*e_shentsize:(i+1)*e_shentsize]
            sh_name_idx, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = struct.unpack('<IIIIIIIIII', sh)
            name = shstrtab[sh_name_idx:].split(b'\x00')[0].decode('latin1', errors='replace')
            print(f"  [{i:2d}] {name:<20} Type: 0x{sh_type:08x} Addr: 0x{sh_addr:08x} Off: 0x{sh_offset:08x} Size: {sh_size:8d} (0x{sh_size:06x})")

if __name__ == '__main__':
    analyze_elf('Poison Pink (Japan)/SLPS_258.54')
