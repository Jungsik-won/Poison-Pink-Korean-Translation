import copy
import json
import tempfile
import unittest
from pathlib import Path

from localization_pipeline import ROOT, file_hash
from korean_sentence_probe import archive_member, FONT_SOURCE
from help_pages import number_tokens, render
from ui_slice import compile_asset
from ui_texture_codec import parse


class HelpPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads((ROOT / 'localization/help_pages.json').read_text())

    def test_all_gameplay_numbers_preserved(self):
        self.assertEqual(number_tokens('HP３３＋１０'), ['33', '10'])
        self.assertEqual(len(self.review['assets']), 14)
        for asset in self.review['assets']:
            for record in asset['records']:
                self.assertEqual(number_tokens(record['source']), number_tokens(record['target']))
        overkill = next(a for a in self.review['assets'] if a['path'].endswith('ev143.tm2'))
        text = '\n'.join(r['target'] for r in overkill['records'])
        self.assertIn('남은 HP', text)
        self.assertIn('더한', text)
        self.assertIn('33+10', text)

    def test_native_palette_and_picture_outside_allowlist_preserved(self):
        asset = self.review['assets'][0]
        _, raw = archive_member('DMAP', asset['path'])
        first, _ = render(raw, asset, FONT_SOURCE)
        second, _ = render(raw, asset, FONT_SOURCE)
        self.assertEqual(first.tobytes(), second.tobytes())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'page.png'
            first.save(path)
            compiled, result = compile_asset(raw, dict(asset, author_image_sha256=file_hash(path)), path)
        before, after = parse(raw), parse(compiled)
        self.assertEqual(len(raw), len(compiled))
        self.assertEqual(before['header'], after['header'])
        self.assertEqual(before['palette'], after['palette'])
        allowed = set()
        for r in asset['records']:
            x, y, w, h = r['rect']
            allowed.update(yy * before['width'] + xx for yy in range(y, y+h) for xx in range(x, x+w))
        changed = {i for i, (a, b) in enumerate(zip(before['indices'], after['indices'])) if a != b}
        self.assertTrue(changed)
        self.assertTrue(changed <= allowed)
        self.assertTrue(result['outside_rectangles_preserved'])

    def test_invalid_translations_and_regions_rejected(self):
        asset = self.review['assets'][0]
        _, raw = archive_member('DMAP', asset['path'])
        mutations = [
            lambda a: a['records'][0].update(target='제목 99'),
            lambda a: a['records'][0].update(font_size=200),
            lambda a: a['records'][0].update(source_rect_sha256='0'*64),
            lambda a: a['records'][0].update(status='draft'),
            lambda a: a['records'].insert(1, copy.deepcopy(a['records'][0])),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(asset)
            mutate(bad)
            with self.assertRaises(ValueError):
                render(raw, bad, FONT_SOURCE)


if __name__ == '__main__':
    unittest.main()
