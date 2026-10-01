import unittest
from build_system_messages import pack_literal

M={'가':dict(code_hex='889f'),'나':dict(code_hex='88a0')}

class SystemMessageTests(unittest.TestCase):
    def test_packed_line_keeps_next_line_position(self):
        source='保存中';raw=b'\0'+source.encode('cp932')+b'\0NEXT\0'
        result=pack_literal(raw,1,source,'가',6,M,True)
        combined=raw[:1]+result+raw[8:]
        self.assertEqual(combined.index(b'NEXT'),raw.index(b'NEXT'))
        self.assertEqual([i for i,x in enumerate(combined) if x==0],[i for i,x in enumerate(raw) if x==0])
        self.assertEqual(result,b'\x88\x9f    \0')

    def test_overlong_line_rejected(self):
        with self.assertRaises(ValueError):pack_literal(('\0保存\0').encode('cp932'),1,'保存','가나가',4,M,True)

    def test_placeholder_change_rejected(self):
        with self.assertRaises(AssertionError):pack_literal(b'\0%s\0',1,'%s','%d',2,M,True)

    def test_button_control_change_rejected(self):
        with self.assertRaises(AssertionError):pack_literal(b'\0@ 0OK\0',1,'@ 0OK','@ 1OK',5,M,True)

    def test_newline_count_rejected(self):
        with self.assertRaises(AssertionError):pack_literal(b'\0A\nB\0',1,'A\nB','AB',3,M,True)

    def test_short_standalone_terminated(self):
        self.assertEqual(pack_literal(('\0保存\0\0\0\0').encode('cp932'),1,'保存','가',7,M,False),b'\x88\x9f'+bytes(6))

if __name__=='__main__':unittest.main()
