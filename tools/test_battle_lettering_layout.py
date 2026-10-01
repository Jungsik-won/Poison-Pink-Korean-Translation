import unittest
import numpy as np
from PIL import Image
from battle_lettering_layout import ROOT, WORK, SIZE, read_maps, read_common, pack_common, unpack_common
from ui_texture_codec import parse, preview_rgba


class BattleLayoutTests(unittest.TestCase):
    def test_original_extraction_did_not_crop_or_move_pixels(self):
        for n in range(5,9):
            name=f'DMAP/dmap/map/bstart/bt_tx{n:02}.tm2'
            model=parse((ROOT/'extracted/original/raw'/name).read_bytes())
            im=Image.open(ROOT/'extracted/original/images'/(name+'.png')).convert('RGBA')
            self.assertEqual(im.size,(256,128))
            self.assertEqual(im.tobytes(),preview_rgba(model))

    def test_red_mesh_expansion_and_separate_row_placement(self):
        maps=read_maps()
        self.assertAlmostEqual(maps['sta_red'][0,0]/maps['sta_pl'][0,0],1.314351,places=5)
        self.assertGreater(maps['stb_red'][2,0]-maps['stb_pl'][2,0],50)
        np.testing.assert_allclose(maps['sta_sdw'],maps['sta_pl'],atol=1e-5)

    def test_psd_helper_layers_are_excluded(self):
        for n in range(5,9):
            im=read_common(WORK/f'bt_tx{n:02}_공통좌표.psd')
            seed=Image.open(WORK/f'bt_tx{n:02}_공통좌표.png')
            self.assertEqual(im.size,SIZE)
            np.testing.assert_array_equal(np.array(im)[:,:,3],np.array(seed)[:,:,3])
            self.assertEqual(im.getpixel((1023,511))[3],0)

    def test_packed_effects_register_in_both_rows(self):
        maps=read_maps()
        for n,minimum in [(6,.90),(7,.75),(8,.90)]:
            source=read_common(WORK/f'bt_tx{n:02}_공통좌표.psd')
            packed=pack_common(source,n,maps)
            restored=unpack_common(packed,n,maps)
            a=np.array(source)[:,:,3]>127;b=np.array(restored)[:,:,3]>127
            for rows in (slice(0,256),slice(256,512)):
                iou=np.count_nonzero(a[rows]&b[rows])/np.count_nonzero(a[rows]|b[rows])
                self.assertGreater(iou,minimum,(n,rows,iou))

    def test_edit_that_would_be_cropped_is_rejected(self):
        im=Image.new('RGBA',SIZE)
        im.putpixel((0,300),(255,0,0,255))
        with self.assertRaisesRegex(ValueError,'would be clipped'):
            pack_common(im,6,read_maps())

    def test_shadow_includes_the_white_outline(self):
        base=read_common(WORK/'bt_tx05_공통좌표.psd')
        shadow=read_common(WORK/'bt_tx08_공통좌표.psd')
        np.testing.assert_array_equal(np.array(base)[:,:,3],np.array(shadow)[:,:,3])
        # The original game's shadow and complete base silhouette also match
        # almost exactly; this is not merely a convention of the new workbench.
        arrays=[]
        for n in (5,8):
            raw=(ROOT/f'extracted/original/raw/DMAP/dmap/map/bstart/bt_tx{n:02}.tm2').read_bytes()
            arrays.append(np.frombuffer(preview_rgba(parse(raw)),np.uint8).reshape(128,256,4)[:,:,3]>127)
        a,b=arrays
        self.assertGreater(np.count_nonzero(a&b)/np.count_nonzero(a|b),.995)


if __name__=='__main__':unittest.main()
