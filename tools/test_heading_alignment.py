import unittest
import numpy as np
from PIL import Image
from build_heading_alignment import ROOT,OUT,WORK,RECTS,LABEL,geometry,read_red,SIZE
from ui_texture_codec import parse,unpack_indices


class HeadingAlignmentTests(unittest.TestCase):
    def test_both_red_quads_expand_horizontally_with_distinct_origins(self):
        s=geometry('s')['red'][0];h=geometry('h')['red'][0]
        self.assertAlmostEqual(s[0,0],160/79,places=5)
        self.assertAlmostEqual(s[0,0],h[0,0],places=5)
        self.assertGreater(abs(s[2,0]-h[2,0]),10)

    def test_only_red_rectangles_change(self):
        old=parse((ROOT/'build/battle_conditions_psd_v1/bt_tx04.tm2').read_bytes())
        new=parse((OUT/'bt_tx04.tm2').read_bytes())
        self.assertEqual(old['header'],new['header']);self.assertEqual(old['palette'],new['palette'])
        a=np.frombuffer(unpack_indices(old),np.uint8).reshape(256,256)
        b=np.frombuffer(unpack_indices(new),np.uint8).reshape(256,256)
        allowed=np.zeros((256,256),bool)
        for x,y,x1,y1 in RECTS.values():
            allowed[y:y1,x:x1]=True
            self.assertGreater(np.count_nonzero(a[y:y1,x:x1]!=b[y:y1,x:x1]),100)
        np.testing.assert_array_equal(a[~allowed],b[~allowed])

    def test_each_effect_matches_its_assembled_glyphs_after_game_scaling(self):
        for prefix in ('s','h'):
            desired=np.array(read_red(prefix))[:,:,3]>127
            after=np.array(Image.open(OUT/f'{prefix}_after_red_common.png'))[:,:,3]>127
            before=np.array(Image.open(OUT/f'{prefix}_before_red_common.png'))[:,:,3]>127
            def iou(a,b):return np.count_nonzero(a&b)/np.count_nonzero(a|b)
            self.assertGreater(iou(after,desired),.94)
            self.assertGreater(iou(after,desired)-iou(before,desired),.20)
            im=read_red(prefix);self.assertEqual(im.size,SIZE)
            self.assertEqual(im.getpixel((0,0))[3],0)


if __name__=='__main__':unittest.main()
