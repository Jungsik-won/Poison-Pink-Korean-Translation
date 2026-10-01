#!/usr/bin/env python3
"""Execute emitted MIPS hook words to check bounds, lookup and caption expiry."""
import json
import os
import struct
import unittest
from pathlib import Path
from build_battle_subtitles import assemble, signature, build_elf, ROOT


def signed(v, bits=32):
    v &= (1<<bits)-1
    return v-(1<<bits) if v>>(bits-1) else v


class Machine:
    def __init__(self, payload, meta):
        self.ram=bytearray(0x2000000);self.ram[meta['base']:meta['base']+len(payload)]=payload
        self.r=[0]*32;self.r[28]=0x555770;self.r[29]=0x1fff000;self.r[31]=0x123456
        self.r[16]=0xabcdef0123456789;self.lo=0;self.draw=[]
        self.store(0x54d79c,1000);self.store(0x5506ec,0x482fc4)
    def store(self,a,v):struct.pack_into('<I',self.ram,a,v&0xffffffff)
    def word(self,a):return struct.unpack_from('<I',self.ram,a)[0]
    def run(self,pc):
        pending=None
        for count in range(50000):
            if pc in (0x190118,0x1e0aa0):return pc
            ins=self.word(pc);op=ins>>26;rs=ins>>21&31;rt=ins>>16&31;rd=ins>>11&31;imm=ins&65535
            address=(self.r[rs]+signed(imm,16))&0xffffffff
            old=pending;pending=None
            if not ins:pass
            elif op==9:self.r[rt]=signed(self.r[rs]+signed(imm,16))&0xffffffffffffffff
            elif op==15:self.r[rt]=signed(imm<<16)&0xffffffffffffffff
            elif op==13:self.r[rt]=self.r[rs]|imm
            elif op==35:self.r[rt]=signed(self.word(address))&0xffffffffffffffff
            elif op==43:self.store(address,self.r[rt])
            elif op==36:self.r[rt]=self.ram[address]
            elif op==63:struct.pack_into('<Q',self.ram,address,self.r[rt]&0xffffffffffffffff)
            elif op==55:self.r[rt]=struct.unpack_from('<Q',self.ram,address)[0]
            elif op==11:self.r[rt]=int((self.r[rs]&0xffffffff)<(signed(imm,16)&0xffffffff))
            elif op in (4,5):
                if (self.r[rs]==self.r[rt])==(op==4):pending=pc+4+signed(imm,16)*4
            elif op in (2,3):
                target=(pc+4)&0xf0000000|(ins&0x3ffffff)<<2
                if op==3:self.r[31]=pc+8
                pending=target
            elif op==0:
                f=ins&63
                if f==38:self.r[rd]=self.r[rs]^self.r[rt]
                elif f==25:self.lo=(self.r[rs]&0xffffffff)*(self.r[rt]&0xffffffff)&0xffffffff
                elif f==18:self.r[rd]=signed(self.lo)&0xffffffffffffffff
                elif f==33:self.r[rd]=signed(self.r[rs]+self.r[rt])&0xffffffffffffffff
                elif f==35:self.r[rd]=signed(self.r[rs]-self.r[rt])&0xffffffffffffffff
                elif f==43:self.r[rd]=int((self.r[rs]&0xffffffff)<(self.r[rt]&0xffffffff))
                elif f==11:
                    if self.r[rt]:self.r[rd]=self.r[rs]
                else:raise AssertionError(hex(ins))
            else:raise AssertionError(hex(ins))
            self.r[0]=0;pc=old if old is not None else pc+4
            if pc==0x1d7348:
                self.draw.append(tuple(self.r[i] for i in (4,5,6,7)))
                # Model legal caller-clobbered registers; preserved s0 is required
                # for the second draw to load the correct subtitle pointer.
                ret=self.r[31]
                for i in (2,3,4,5,6,7,8,9,10,11,12,13,14,15):self.r[i]=0xdeadbeef
                pc=ret;pending=None
        raise AssertionError('Hook did not terminate')


class HookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = os.environ.get('BATTLE_SUBTITLE_CATALOG', 'localization/battle_voice_subtitles_v1.json')
        cls.rows=json.loads((ROOT/catalog).read_text())['rows']
        cls.payload,cls.meta=assemble(cls.rows)
    def voice(self,row=None,command=0x600,ptr=0x1000000,rate=22050):
        m=Machine(self.payload,self.meta);m.r[4]=command
        if row:
            bank=(ROOT/row['bank']).read_bytes();body=0x40+struct.unpack_from('<I',bank,8)[0]
            raw=bank[body+row['offset']:body+row['offset']+row['size']]
        else:raw=bytes(16)
        if 0<=ptr and ptr+len(raw)<=len(m.ram):m.ram[ptr:ptr+len(raw)]=raw
        m.store(0x447004,ptr);m.store(0x447008,len(raw));m.store(0x44700c,rate)
        m.run(self.meta['labels']['voice']);return m
    def test_every_voice_lookup_and_original_prologue(self):
        for row in self.rows:
            m=self.voice(row);ptr=m.word(self.meta['state'])
            self.assertEqual(bool(ptr),row['status']=='reviewed_translation',row['tag'])
            self.assertEqual(m.r[4],0x600);self.assertEqual(m.r[31],0x123456)
            self.assertEqual(m.r[29],0x1ffeff0);self.assertEqual(m.r[6],0x440000)
            if ptr:
                self.assertEqual(m.word(self.meta['state']+8),1000)
                self.assertGreater(m.word(self.meta['state']+4),1000)
    def test_non_voice_and_invalid_descriptors_are_ignored(self):
        for command,ptr,rate in [(0x500,0x1000000,22050),(0x600,0,22050),
            (0x600,0x2000000,22050),(0x600,0x1000000,48000)]:
            self.assertEqual(self.voice(command=command,ptr=ptr,rate=rate).word(self.meta['state']),0)
    def test_frame_draw_expiry_and_clock_reset(self):
        row=next(r for r in self.rows if r['status']=='reviewed_translation')
        for frame,draw in [(1001,True),(1241,False),(0,False)]:
            m=self.voice(row);sp=m.r[29];s0=m.r[16]
            m.store(0x54d79c,frame);m.run(self.meta['labels']['frame'])
            self.assertEqual(len(m.draw),2 if draw else 0)
            self.assertEqual(m.r[29],sp);self.assertEqual(m.r[16],s0)
            if draw:self.assertEqual(m.draw[0][3],m.draw[1][3])
            else:self.assertEqual(m.word(self.meta['state']),0)
    def test_new_segment_outside_original_bss_and_heap(self):
        old=(ROOT/'build/iso_dialogue_fix_v1/SLPS_258.54').read_bytes()
        new,patches=build_elf(old,self.payload,dict(self.meta))
        from runtime_compat import elf_segments
        segments=elf_segments(new)
        self.assertLessEqual(segments[0][2]+segments[0][5],segments[1][2])
        self.assertEqual(new[segments[1][1]:segments[1][1]+segments[1][4]],self.payload)


if __name__=='__main__':unittest.main()
