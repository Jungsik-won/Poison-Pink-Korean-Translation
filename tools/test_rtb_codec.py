import struct
import tempfile
import unittest
from pathlib import Path
from rtb_codec import parse,serialize,replace_strings,control_signature
from iso_archive_stage import plan_archive_replacements
from localization_pipeline import sha


def fixture(text=b'hello'):
    # Empty module tables followed by a module function: jz +2, string, ret.
    # Include an over-wide compact count to ensure exact wire preservation.
    header=b'\xfe\0\0'+b'\0'*4+struct.pack('<I',0)+b'\0'+bytes([0,1,3,64])
    code=b'\x6c'+struct.pack('<Ii',0,2)+b'\x33'+struct.pack('<I',0)+bytes([len(text)])+text+b'\x6e'+bytes(4)+b'\0'
    return header+code+struct.pack('<I',16)


class RTBTests(unittest.TestCase):
    def test_roundtrip_and_embedded_opcode_bytes(self):
        data=fixture(b'\x33\x01TAG\x03foo\x6b\0\0\0\0')
        p=parse(data)
        self.assertEqual(serialize(p),data)
        self.assertEqual(len(p['functions'][0]['instructions']),3)
        self.assertEqual(p['functions'][0]['branches'][0]['target'],2)
        self.assertEqual(p['fields'][0]['width'],3)

    def test_growth_shrink_and_255_preserve_jump_and_footer(self):
        data=fixture();p=parse(data);off=p['functions'][0]['instructions'][1]['offset']
        for new in (b'',b'x',b'longer than original',b'x'*255):
            out=replace_strings(data,{off:(b'hello',new)},sha(data))
            q=parse(out)
            self.assertEqual(control_signature(p),control_signature(q))
            self.assertEqual(len(out)-len(data),len(new)-5)
            self.assertEqual(q['global_slots'],16)
            self.assertEqual(q['functions'][0]['instructions'][1]['args'],[new.hex()])

    def test_source_location_and_length_guards(self):
        data=fixture();off=parse(data)['functions'][0]['instructions'][1]['offset']
        for mapping,digest in [({off:(b'hello',b'a')},'0'*64),({off+6:(b'hello',b'a')},sha(data)),
                               ({off:(b'wrong',b'a')},sha(data)),({off:(b'hello',b'x'*256)},sha(data))]:
            with self.assertRaises(ValueError):replace_strings(data,mapping,digest)

    def test_truncation_unknown_opcode_count_and_branch_rejected(self):
        data=fixture();p=parse(data);f=p['functions'][0];jump=f['instructions'][0]['offset']
        badop=bytearray(data);badop[jump]=0x28
        badbranch=bytearray(data);badbranch[jump+5:jump+9]=struct.pack('<i',3)
        badcount=bytearray(data);badcount[jump-2]=4
        for bad in (data[:-1],data+b'\0',bytes(badop),bytes(badbranch),bytes(badcount)):
            with self.assertRaises(ValueError):parse(bad)

    def test_all_truncations_rejected(self):
        data=fixture()
        for end in range(len(data)):
            with self.assertRaises(ValueError):parse(data[:end])

    def test_shrink_zeros_released_tail_and_preserves_next_member(self):
        def rec(off,size,name,stamp=0):return struct.pack('<II32sI',off,size,name.encode(),stamp)
        hed=rec(2,4,'root')+rec(0,0,'--DirEnd--')+rec(0,1,'..')+rec(0,4,'a',1)+rec(16,4,'b',1)+rec(0,0,'--DirEnd--')
        with tempfile.TemporaryDirectory() as tmp:
            dat=Path(tmp)/'a.dat';dat.write_bytes(b'AAAA'+bytes(12)+b'BBBB')
            _,patches,hpatches,changes=plan_archive_replacements(hed,dat,{'root/a':b'XY'},allow_shrink=True)
            self.assertEqual(patches[0]['data'],b'XY\0\0')
            self.assertEqual(hpatches[0]['data'],struct.pack('<I',2))
            self.assertEqual(changes[0]['released_zero_padding'],2)
            self.assertEqual(dat.read_bytes()[16:],b'BBBB')
            with self.assertRaises(ValueError):plan_archive_replacements(hed,dat,{'root/a':b''},allow_shrink=True)


if __name__=='__main__':unittest.main()
