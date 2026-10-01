import struct
import unittest
from tutorial_slice import grow_font_archive,ALIGN
from localization_pipeline import hed_tree


def rec(off,size,name,stamp=0):return struct.pack('<II32sI',off,size,name.encode(),stamp)


class TutorialArchiveTests(unittest.TestCase):
    def fixture(self):
        hed=rec(2,5,'system')+rec(0,0,'--DirEnd--')+rec(0,1,'..')+rec(0,100,'kanji.dat',1)+rec(ALIGN,10,'kantable.dat',1)+rec(ALIGN*2,4,'tail.bin',1)+rec(0,0,'--DirEnd--')
        dat=b'F'*100+bytes(ALIGN-100)+b'T'*10+bytes(ALIGN-10)+b'LAST'+bytes(ALIGN-4)
        return hed,dat

    def test_growth_relocates_following_members_and_preserves_payloads(self):
        hed,dat=self.fixture();font=b'F'*100+b'K'*39900
        h,d,shift=grow_font_archive(hed,dat,font,b'N'*10)
        self.assertEqual(shift,ALIGN*2)
        entries,_=hed_tree(h)
        self.assertEqual(entries[0]['size'],40000)
        self.assertEqual(entries[1]['offset'],ALIGN*3)
        self.assertEqual(d[:40000],font)
        self.assertEqual(d[ALIGN*3:ALIGN*3+10],b'N'*10)
        self.assertEqual(d[ALIGN*4:ALIGN*4+4],b'LAST')
        self.assertEqual(len(d),len(dat)+shift)

    def test_changed_original_font_or_nonzero_padding_rejected(self):
        hed,dat=self.fixture()
        with self.assertRaises(ValueError):grow_font_archive(hed,dat,b'X'*200,b'N'*10)
        bad=bytearray(dat);bad[120]=1
        with self.assertRaises(ValueError):grow_font_archive(hed,bytes(bad),b'F'*100+b'K'*39900,b'N'*10)
        with self.assertRaises(ValueError):grow_font_archive(hed,dat,b'F'*100+b'K'*39900,b'N'*9)


if __name__=='__main__':unittest.main()
