import json
import unittest
from PIL import Image,ImageDraw
import numpy as np
from build_battle_titles_euljiro import BUILD,WORK,ROOT,RAW,effects
from build_battle_conditions_psd import compile_texture
from ui_texture_codec import parse,unpack_indices


class LetteringTests(unittest.TestCase):
    def test_emphasis_is_shared_by_every_effect(self):
        report=json.loads((BUILD/'report.json').read_text())
        rows=[report['typography'][f'bt_tx{n:02}'] for n in range(5,9)]
        self.assertTrue(all(r==rows[0] for r in rows))
        spans=rows[0]['placements']
        self.assertEqual([r['text'] for r in spans],['모든',' 적을','격파','하라'])
        self.assertAlmostEqual(spans[1]['font_size_native']/spans[0]['font_size_native'],.64,delta=.01)
        self.assertEqual(spans[0]['baseline_origin_4x'][1],spans[1]['baseline_origin_4x'][1])

    def test_shadow_includes_outline(self):
        mask=Image.new('L',(128,128));ImageDraw.Draw(mask).rectangle((40,40,80,80),fill=255)
        base,red,glow,shadow=effects(mask)
        np.testing.assert_array_equal(np.array(base)[:,:,3],np.array(shadow)[:,:,3])
        self.assertEqual(shadow.getpixel((34,60))[3],255)
        self.assertEqual(mask.getpixel((34,60)),0)

    def test_legacy_alpha_floor_is_opt_in(self):
        raw=(RAW/'DMAP/dmap/map/bstart/bt_nm_050040.tm2').read_bytes()
        image=Image.new('RGBA',(256,128));ImageDraw.Draw(image).rectangle((50,30,150,80),fill=(255,253,184,255))
        with self.assertRaises(AssertionError):compile_texture(raw,image)
        compiled,checks=compile_texture(raw,image,allow_original_alpha_floor=True)
        self.assertEqual(checks['minimum_background_preview_alpha'],2)
        before=parse(raw);after=parse(compiled)
        self.assertEqual(before['header'],after['header']);self.assertEqual(before['palette'],after['palette'])
        i=unpack_indices(after)[0];self.assertEqual(after['palette'][i][3],1)

    def test_all_aliases_compiled_identically(self):
        docs=json.loads((WORK/'manifest.json').read_text())['documents']
        stages=[s for s in docs if s['kind']=='stage_title'];self.assertEqual(len(stages),54)
        count=0
        for s in stages:
            src=s['pieces'][0]['source'];data=(BUILD/'textures'/src).read_bytes();count+=1
            for alias in s.get('aliases',[]):
                self.assertEqual(data,(BUILD/'textures'/alias).read_bytes());count+=1
        self.assertEqual(count,112)

    def test_final_stored_shadow_alignment(self):
        report=json.loads((BUILD/'report.json').read_text())
        self.assertEqual(len(report['textures']),137)
        self.assertEqual(len(report['registration']),8)
        for r in report['registration']:
            self.assertGreater(r['shadow_iou'],.93)
            self.assertGreater(r['shadow_covers_base'],.96)


if __name__=='__main__':unittest.main()
