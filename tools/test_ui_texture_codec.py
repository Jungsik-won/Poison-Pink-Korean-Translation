import copy
import struct
import unittest
from ui_texture_codec import parse, serialize, sha, rect_indices, replace_rect, unpack_indices, uad_rectangles


def sample(bpp):
    w,h=8,4;colors=1<<bpp;im=bytes(range(w*h*bpp//8));header=bytearray(64)
    header[:8]=b'TIM2\x04\x00\x01\x00'
    struct.pack_into('<IIIHH',header,16,48+len(im)+colors*4,colors*4,len(im),48,colors)
    header[32:36]=bytes((0,1,3,4 if bpp==4 else 5))
    struct.pack_into('<HHQ',header,36,w,h,(20 if bpp==4 else 19)<<20)
    # Duplicate RGB, unequal raw alpha, including >128: preview must not replace raw CLUT.
    clut=bytes(v for i in range(colors) for v in (42,42,i%3,i%256))
    return bytes(header)+im+clut


class TextureTests(unittest.TestCase):
    def test_linear_palette_flag_retains_exact_color_order(self):
        raw=bytearray(sample(8));raw[34]=0x83;data=bytes(raw)
        model=parse(data);clut=data[-1024:]
        self.assertEqual(model['clut_storage'],'linear')
        self.assertEqual(model['palette'][8],clut[32:36])
        self.assertEqual(model['palette'][16],clut[64:68])
        self.assertEqual(serialize(model),data)
        raw[34]=3;permuted=parse(bytes(raw))
        self.assertEqual(permuted['palette'][8],clut[64:68])
        self.assertNotEqual(model['palette'][8],permuted['palette'][8])

    def test_raw_roundtrip_and_bounded_pixels(self):
        for bpp in (4,8):
            data=sample(bpp);m=parse(data)
            self.assertEqual(serialize(m),data)
            rect=[1,1,3,2];old=rect_indices(m,rect);new=bytes([7]*6)
            out=replace_rect(data,rect,new,sha(data),sha(old));n=parse(out)
            self.assertEqual(n['header'],m['header']);self.assertEqual(n['palette'],m['palette'])
            changed={i for i,(a,b) in enumerate(zip(unpack_indices(m),unpack_indices(n))) if a!=b}
            self.assertTrue(changed);self.assertTrue(changed <= {9,10,11,17,18,19})
            self.assertEqual(rect_indices(n,rect),new)
            self.assertEqual(replace_rect(data,rect,old,sha(data),sha(old)),data)

    def test_reject_corruption_and_unsafe_replacement(self):
        data=sample(8);m=parse(data);rect=[0,0,2,2];old=rect_indices(m,rect)
        for bad in (data[:-1],data+b'\0',b'BAD!'+data[4:]):
            with self.assertRaises(ValueError):parse(bad)
        for off,value in [(6,2),(28,49),(33,2),(35,3),(42,0)]:
            bad=bytearray(data);bad[off]=value
            with self.assertRaises(ValueError):parse(bytes(bad))
        for r,new,source,rs in [([-1,0,2,2],old,sha(data),sha(old)),(rect,b'X',sha(data),sha(old)),(rect,old,'bad',sha(old)),(rect,old,sha(data),'bad')]:
            with self.assertRaises(ValueError):replace_rect(data,r,new,source,rs)
        data4=sample(4);r=[0,0,1,1]
        with self.assertRaises(ValueError):replace_rect(data4,r,b'\xff',sha(data4),sha(rect_indices(parse(data4),r)))

    def test_uad_big_endian_bounds(self):
        b=bytearray(52);b[:4]=b'UAD\0';struct.pack_into('>4H',b,4,1,0,48,52)
        struct.pack_into('>6H',b,16,1,2,3,4,1,2)
        self.assertEqual(uad_rectangles(bytes(b),8,8)['rectangles'][0]['rect'],[1,2,3,4])
        with self.assertRaises(ValueError):uad_rectangles(bytes(b),3,3)
        b[9]=47
        with self.assertRaises(ValueError):uad_rectangles(bytes(b),8,8)


if __name__=='__main__':unittest.main()
