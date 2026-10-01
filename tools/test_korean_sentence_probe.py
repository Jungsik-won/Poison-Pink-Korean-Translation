import struct
import tempfile
import unittest
from pathlib import Path

from iso_archive_stage import plan_archive_replacements
from korean_sentence_probe import encode_korean,decode_korean,patch_literal,choose_slots
from localization_pipeline import sha
from font_pair_probe import japanese_index


def record(off,size,name,stamp=0):
    return struct.pack('<II32sI',off,size,name.encode('ascii'),stamp)


class GrowthTests(unittest.TestCase):
    def setup_fixture(self,root):
        hed=(record(2,4,'root')+record(0,0,'--DirEnd--')+record(0,1,'..')+
             record(0,4,'a.bin',1)+record(16,4,'b.bin',1)+record(0,0,'--DirEnd--'))
        dat=Path(root)/'archive.dat';dat.write_bytes(b'AAAA'+bytes(12)+b'BBBB'+bytes(12))
        return hed,dat

    def test_growth_exactly_fits_padding(self):
        with tempfile.TemporaryDirectory() as root:
            hed,dat=self.setup_fixture(root)
            files,patches,hpatches,growth=plan_archive_replacements(hed,dat,{'root/a.bin':b'X'*16},True)
            self.assertEqual(growth[0]['consumed_zero_padding'],12)
            self.assertEqual(patches[0]['expected_sha256'],sha(b'AAAA'+bytes(12)))
            self.assertEqual(hpatches[0]['offset'],3*44+4)
            self.assertEqual(hpatches[0]['data'],struct.pack('<I',16))
            self.assertEqual(dat.read_bytes()[16:20],b'BBBB')

    def test_growth_rejected_by_default_and_at_next_member(self):
        with tempfile.TemporaryDirectory() as root:
            hed,dat=self.setup_fixture(root)
            with self.assertRaises(ValueError):plan_archive_replacements(hed,dat,{'root/a.bin':b'X'*5})
            with self.assertRaises(ValueError):plan_archive_replacements(hed,dat,{'root/a.bin':b'X'*17},True)
            with self.assertRaises(ValueError):plan_archive_replacements(hed,dat,{'root/a.bin':b'X'*3},True)

    def test_nonzero_padding_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            hed,dat=self.setup_fixture(root)
            b=bytearray(dat.read_bytes());b[6]=255;dat.write_bytes(b)
            with self.assertRaisesRegex(ValueError,'nonzero'):plan_archive_replacements(hed,dat,{'root/a.bin':b'X'*8},True)


class EncodingTests(unittest.TestCase):
    def test_custom_roundtrip_and_unknown_char(self):
        mapping={'가':{'code_hex':'88fa'},'나':{'code_hex':'8949'}}
        encoded=encode_korean('가 나!\n가',mapping)
        self.assertEqual(decode_korean(encoded,mapping),'가 나!\n가')
        with self.assertRaises(ValueError):encode_korean('각',mapping)
        with self.assertRaises(ValueError):encode_korean('\u1100\u1161',mapping)
        with self.assertRaises(ValueError):decode_korean(b'\x88',mapping)

    def test_slot_excludes_used_and_assigned(self):
        table=[0]*7560
        for code in (0x88fa,0x8949):table[japanese_index(code)]=-1
        self.assertEqual(choose_slots(table,{0x88fa},1),[(0x8949,japanese_index(0x8949))])
        with self.assertRaises(ValueError):choose_slots(table,{0x88fa,0x8949},1)


class LiteralTests(unittest.TestCase):
    def fixture(self):
        data=b'\xfe\0\0\x33\x01TAG\x04Test\x65\x01TAGtail'
        row=dict(member_sha256=sha(data),opcode_offset=3,payload_offset=9,length_offset=8,
                 source_byte_length=4,raw_hex=b'Test'.hex(),source_sha256=sha(b'Test'),tag_hex=b'TAG'.hex())
        return data,row

    def test_fixed_length_patch_preserves_all_other_bytes(self):
        data,row=self.fixture();out=patch_literal(data,row,b'ABCD')
        self.assertEqual(out,data[:9]+b'ABCD'+data[13:])
        self.assertEqual(len(out),len(data))

    def test_wrong_size_revision_and_tail_rejected(self):
        data,row=self.fixture()
        with self.assertRaises(ValueError):patch_literal(data,row,b'ABC')
        with self.assertRaises(ValueError):patch_literal(data+b'x',row,b'ABCD')
        altered=data[:13]+b'\x64'+data[14:];row['member_sha256']=sha(altered)
        with self.assertRaisesRegex(ValueError,'adjacent'):patch_literal(altered,row,b'ABCD')


if __name__=='__main__':unittest.main()
