import copy
import json
import tempfile
from pathlib import Path
import unittest
import numpy as np
from PIL import Image, ImageDraw
from battle_workbench_v3 import OUT, IMG, digest, artwork, export, layered_psd
from add_battle_stage_titles_v3 import verify_layout


class StageTitleTests(unittest.TestCase):
    def test_mesh_layout_and_all_source_mappings(self):
        maps=verify_layout()
        self.assertEqual(maps['bt_ar']['row_height'],48)
        self.assertEqual(maps['bt_nm']['row_height'],64)
        m=json.loads((OUT/'manifest.json').read_text())
        docs=[s for s in m['documents'] if s['kind']=='stage_title']
        self.assertEqual(len(docs),54)
        sources={s['pieces'][0]['source'] for s in docs}|{a for s in docs for a in s['aliases']}
        self.assertEqual(len(sources),112)
        for path,sha in m['stage_title_extension']['preserves_existing_psds'].items():
            self.assertEqual(digest(OUT/path),sha)

    def test_all_new_references_are_excluded(self):
        m=json.loads((OUT/'manifest.json').read_text())
        for s in m['documents']:
            if s['kind']=='stage_title':
                self.assertIsNone(artwork(OUT/s['psd']).getchannel('A').getbbox())

    def test_center_crossing_art_is_split_and_propagated_to_aliases(self):
        m=json.loads((OUT/'manifest.json').read_text())
        s=copy.deepcopy(next(x for x in m['documents'] if x['id']=='bt_ar'))
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)/'work';work.mkdir();destination=Path(temp)/'export'
            im=Image.new('RGBA',s['size']);ImageDraw.Draw(im).rectangle((992,40,1055,119),fill=(250,20,20,255))
            ref=Image.new('RGBA',s['size'],(0,255,0,255))
            layered_psd(work/s['psd'],[('원문_내보내기제외',ref,True),('사용자추가글자',im,True)],ref)
            (work/'manifest.json').write_text(json.dumps({'documents':[s]}))
            export(work,destination)
            source=s['pieces'][0]['source'];a=Image.open(destination/(source+'.png')).convert('RGBA')
            for alias in s['aliases']:
                b=Image.open(destination/(alias+'.png')).convert('RGBA')
                self.assertEqual(a.tobytes(),b.tobytes())
            # Left part ends in upper atlas row, right part begins in lower row.
            self.assertGreater(a.getpixel((251,20))[3],240)
            self.assertGreater(a.getpixel((4,68))[3],240)
            self.assertEqual(a.getpixel((20,20))[3],0)
            original=Image.open(IMG/(source+'.png')).convert('RGBA')
            np.testing.assert_array_equal(np.array(a)[96:],np.array(original)[96:])


if __name__=='__main__':unittest.main()
