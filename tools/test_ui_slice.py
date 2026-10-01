import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from test_ui_texture_codec import sample
from ui_texture_codec import parse,sha,rect_indices
from ui_slice import compile_asset,verify_overlay


class SliceTests(unittest.TestCase):
    def test_alpha_import_preserves_original_palette_and_rejects_flattening(self):
        raw=sample(8);m=parse(raw);rect=[1,1,3,2]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'alpha.png';Image.new('RGBA',(8,4),(255,255,255,0)).save(p)
            a=dict(source_sha256=sha(raw),author_image_sha256=sha(p.read_bytes()),import_mode='rgba_palette',records=[dict(
                id='alpha',rect=rect,source_rect_sha256=sha(rect_indices(m,rect)),target='검증',status='reviewed',reviewer='test')])
            out,r=compile_asset(raw,a,p)
            self.assertEqual(parse(out)['palette'],m['palette'])
            self.assertEqual(parse(out)['header'],m['header'])
            self.assertTrue(r['outside_rectangles_preserved'])
            for i in rect_indices(parse(out),rect):self.assertEqual(m['palette'][i][3],0)
            Image.new('RGB',(8,4),'black').save(p);a['author_image_sha256']=sha(p.read_bytes())
            with self.assertRaises(ValueError):compile_asset(raw,a,p)

    def test_author_import_guards_and_preservation(self):
        raw=bytearray(sample(8))
        # Opaque original CLUT for an authored text tile.
        for i in range(256):raw[64+32+i*4+3]=128
        raw=bytes(raw);m=parse(raw);rect=[1,1,3,2]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'author.png';Image.new('RGB',(8,4),(42,42,2)).save(p)
            a=dict(source_sha256=sha(raw),author_image_sha256=sha(p.read_bytes()),records=[dict(
                id='test',rect=rect,source_rect_sha256=sha(rect_indices(m,rect)),target='검증',status='reviewed',reviewer='test')])
            out,report=compile_asset(raw,a,p)
            self.assertEqual(parse(out)['palette'],m['palette']);self.assertTrue(report['outside_rectangles_preserved'])
            override=Path(td)/'override.png';Image.new('RGB',(8,4),(42,42,1)).save(override)
            a['records'][0].update(author_image=str(override),author_image_sha256=sha(override.read_bytes()),author_rect=[0,0,3,2])
            changed,_=compile_asset(raw,a,p)
            self.assertNotEqual(rect_indices(parse(changed),rect),rect_indices(parse(out),rect))
            a['records'][0]['author_image_sha256']='bad'
            with self.assertRaises(ValueError):compile_asset(raw,a,p)
            for key in ('author_image','author_image_sha256','author_rect'):del a['records'][0][key]
            a['records'].append(dict(a['records'][0],id='overlap'))
            with self.assertRaises(ValueError):compile_asset(raw,a,p)
            a['records'].pop();a['records'][0]['status']='draft'
            with self.assertRaises(ValueError):compile_asset(raw,a,p)
            a['records'][0]['status']='reviewed';Image.new('RGB',(7,9)).save(p);a['author_image_sha256']=sha(p.read_bytes())
            with self.assertRaises(ValueError):compile_asset(raw,a,p)

    def test_full_overlay_detects_extra_byte_and_tail(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source';output=Path(td)/'output';old=b'abcdefgh';new=b'abXYefgh'
            source.write_bytes(old);output.write_bytes(new)
            patches=[dict(offset=2,data=b'XY',expected_sha256=sha(b'cd'))]
            self.assertEqual(verify_overlay(source,output,patches,sha(old),sha(new))['changed_bytes'],2)
            for bad in (b'abXYefgZ',new+b'!'):
                output.write_bytes(bad)
                with self.assertRaises(ValueError):verify_overlay(source,output,patches,sha(old),sha(bad))


if __name__=='__main__':unittest.main()
