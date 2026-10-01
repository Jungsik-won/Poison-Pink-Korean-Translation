"""Unpublished voice-trigger/frame hook experiment in a copied savestate."""
import struct
from battle_subtitle_probe import OUT, words, jal, patch_state

class Assembler:
    def __init__(self, base): self.base = base; self.code = []; self.labels = {}; self.fixups = []
    def emit(self, *ws): self.code.extend(ws)
    def label(self, name): self.labels[name] = self.base + len(self.code) * 4
    def branch(self, op, rs, rt, label):
        self.fixups.append((len(self.code), label)); self.emit(op << 26 | rs << 21 | rt << 16, 0)
    def load(self, reg, value): self.emit(0x3c000000 | reg << 16 | value >> 16, 0x34000000 | reg << 21 | reg << 16 | value & 65535)
    def finish(self):
        for i, label in self.fixups:
            delta = (self.labels[label] - (self.base + i * 4 + 4)) // 4
            assert -32768 <= delta < 32768; self.code[i] |= delta & 65535
        return words(*self.code)

def main():
    base = 0x523300; state = base + 0x1c0; coords = base + 0x1e0; color = base + 0x1f0; text = base + 0x1f4
    a = Assembler(base)
    a.label('voice'); a.emit(0x27bdfff0,0xffbf0008,0xffa40000,0x24090600)
    a.branch(5,4,9,'done'); a.load(8,0x447000)
    a.emit(0x8d0a0004,0x8d0b0008,0x240c0200,0x2d6f0200,0x016f600b) # movn count,size,less
    a.load(13,2166136261); a.load(14,16777619)
    a.label('hash'); a.emit(0x914f0000,0x01af6826,0x01ae0019,0x00006812,0x254a0001,0x258cffff)
    a.branch(5,12,0,'hash'); a.load(8,state)
    a.emit(0xad0d0000,0xad0b0004,0x8f89802c,0x25290078,0xad090008,0x8d09000c,0x25290001,0xad09000c)
    a.label('done'); a.emit(0xdfa40000,0xdfbf0008,0x27bd0010)
    # Relocated original prologue, followed by the untouched original body.
    a.emit(0x27bdfff0,0x3c060044,0x08000000 | 0x190118 >> 2,0)
    a.label('frame'); a.emit(0x27bdfff0,0xffbf0008); a.load(8,state)
    a.emit(0x8d090008,0x8f8a802c,0x0149582b)
    a.branch(4,11,0,'frame_done')
    a.emit(0x3c040055,0x8c8406ec); a.load(5,coords); a.load(6,color); a.load(7,text)
    a.emit(jal(0x1d7348),0)
    a.label('frame_done'); a.emit(0xdfbf0008,0x08000000 | 0x1e0aa0 >> 2,0x27bd0010)
    code = a.finish(); assert len(code) <= 0x1c0, len(code)
    blob = bytearray(0x210); blob[:len(code)] = code
    blob[0x1e0:0x1f0] = struct.pack('<4f',160,405,65535,.75)
    blob[0x1f0:0x1f4] = bytes([255,255,255,128])
    blob[0x1f4:0x208] = b'Battle voice active\0'
    patches=[(base,bytes(len(blob)),bytes(blob)),(0x190110,words(0x27bdfff0,0x3c060044),words(0x08000000 | base >> 2,0)),
             (0x1008d8,words(jal(0x1e0aa0)),words(jal(a.labels['frame'])))]
    patch_state(OUT/'user_slot1_original.p2s',OUT/'voice_hook_probe.p2s',patches)
    print('code bytes',len(code),'state',hex(state),'frame',hex(a.labels['frame']))

if __name__ == '__main__': main()
