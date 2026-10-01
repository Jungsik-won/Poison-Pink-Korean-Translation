import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image
from battle_workbench_v3 import (OUT, OLD, IMG, ROOT, artwork, condition_specs,
                                 capture_specs, unpack, transform, digest, layered_psd)


class WorkbenchTests(unittest.TestCase):
    def test_every_v2_texture_is_represented(self):
        old=json.loads((OLD/'manifest.json').read_text())
        expected={v['source'] for g in old['groups'] for v in g['variants']}
        specs=condition_specs()+capture_specs()
        self.assertEqual(expected,{p['source'] for s in specs for p in s['pieces']})
        self.assertEqual(len(specs),40)

    def test_body_red_second_row_starts_at_56_not_64(self):
        for s in condition_specs():
            if s['id'] in ('bt_tx06','bt_tx14','bt_tx22','bt_tx26'):
                self.assertEqual(s['pieces'][0]['rect'],[0,0,256,56])
                self.assertEqual(s['pieces'][1]['rect'],[0,56,256,112])

    def test_defeat_body_uses_mesh_uv_height_not_texture_height(self):
        specs={s['id']:s for s in condition_specs()}
        for first in (9,17):
            expected=[(256,40),(200,40),(128,39),(128,40)]
            for offset,(width,height) in enumerate(expected):
                s=specs[f'bt_tx{first+offset:02}']
                self.assertEqual(s['pieces'][0]['rect'],[0,0,width,height])
                self.assertEqual(s['size'],(1024,256))

    def test_anchor_transform_inverse_preserves_capture_pixels(self):
        for s in capture_specs():
            sources={p['source'] for p in s['pieces']}
            images={name:Image.open(IMG/(name+'.png')).convert('RGBA') for name in sources}
            images={name:im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST) for name,im in images.items()}
            common=unpack(images,s)
            for p in s['pieces']:
                isolated=Image.new('RGBA',common.size);b=tuple(p['clip']);isolated.paste(common.crop(b),b[:2])
                recovered=transform(isolated,images[p['source']].size,p['forward'])
                box=tuple(v*4 for v in p['rect'])
                a=np.array(recovered.crop(box));b=np.array(images[p['source']].crop(box))
                # Ignore invisible RGB, which alpha compositing canonically zeros.
                np.testing.assert_array_equal(a[:,:,3],b[:,:,3],err_msg=s['id'])
                np.testing.assert_array_equal(a[:,:,:3][b[:,:,3]>0],b[:,:,:3][b[:,:,3]>0])

    def test_reference_layers_cannot_leak_into_export(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.psd';size=(16,16)
            blank=Image.new('RGBA',size);reference=Image.new('RGBA',size,(255,0,0,255))
            layers=[('원문_해당효과_내보내기제외',reference,True),('한글식자',blank,True)]
            layered_psd(path,layers,reference)
            self.assertIsNone(artwork(path).getchannel('A').getbbox())
            work=Image.new('RGBA',size);work.putpixel((8,8),(0,255,0,255))
            layered_psd(path,[('원문_기본',reference,True),('추가한_사용자레이어',work,True)],reference)
            self.assertEqual(artwork(path).getchannel('A').getbbox(),(8,8,9,9))

    def test_saved_psds_dimensions_and_backups(self):
        manifest=json.loads((OUT/'manifest.json').read_text())
        for entry in manifest['user_backups']:
            self.assertEqual(digest(ROOT/entry['path']),entry['sha256'])
            self.assertEqual(digest(OUT/entry['backup']),entry['sha256'])
        for s in manifest['documents']:
            result=artwork(OUT/s['psd'])
            self.assertEqual(result.size,tuple(s['size']))
            self.assertEqual(bool(result.getchannel('A').getbbox()),s['has_existing_korean'])

    def test_defeat_edit_shadow_covers_complete_base(self):
        folder=OUT/'04_주인공전투불능'
        base=artwork(folder/'01_기본글자.psd')
        shadow=artwork(folder/'04_검은효과.psd')
        np.testing.assert_array_equal(np.array(base)[:,:,3],np.array(shadow)[:,:,3])


if __name__=='__main__':unittest.main()
