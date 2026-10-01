import copy
import json
import unittest
from pathlib import Path
from localization_pipeline import ROOT,hed_tree
from iso_archive_stage import iso_inventory,exact
from korean_sentence_probe import archive_member,FONT_SOURCE
from font_pair_probe import decode_glyph
from ui_font_artwork import render_asset
from ui_texture_codec import parse,preview_rgba
from ui_titles import patch_literals,extend_font


class RemainingTests(unittest.TestCase):
    def setUp(self):
        self.review=json.loads((ROOT/'localization/ui_remaining.json').read_text())

    def test_true_alpha_deterministic_bounded_font_artwork(self):
        a=next(a for a in self.review['assets'] if a['path']=='status/sys011.tm2')
        _,raw=archive_member('STATUS',a['path']);m=parse(raw)
        im,checks=render_asset(raw,a,FONT_SOURCE);again,_=render_asset(raw,a,FONT_SOURCE)
        self.assertEqual(im.tobytes(),again.tobytes());self.assertEqual(im.mode,'RGBA')
        alphas=list(im.getchannel('A').getdata());self.assertIn(0,alphas);self.assertIn(255,alphas)
        self.assertTrue(any(0<x<255 for x in alphas))
        before=preview_rgba(m);after=im.tobytes();allowed=set()
        for r in a['records']:
            x,y,w,h=r['rect'];allowed.update(yy*m['width']+xx for yy in range(y,y+h) for xx in range(x,x+w))
        for i in range(m['width']*m['height']):
            if i not in allowed:self.assertEqual(before[i*4:i*4+4],after[i*4:i*4+4])
        bad=copy.deepcopy(a);bad['records'][0]['render']['font_size']=200
        with self.assertRaises(ValueError):render_asset(raw,bad,FONT_SOURCE)

    def test_command_rodata_and_sdata_keep_existing_titles(self):
        raw=(ROOT/'build/ui_titles_v2/SLPS_258.54').read_bytes()
        chars=sorted({c for r in self.review['literals'] for c in r['target'] if ord(c)>127})
        mapping={c:dict(code_hex=(0x989f+i).to_bytes(2,'big').hex()) for i,c in enumerate(chars)}
        out,checks=patch_literals(raw,self.review,mapping)
        self.assertEqual(out[0x453468:0x4534b8],raw[0x453468:0x4534b8])
        self.assertEqual(out[0x1000:0x30ed10],raw[0x1000:0x30ed10])
        self.assertEqual(len(out),len(raw));self.assertEqual(len(checks),6)
        for change in ('capacity','section'):
            bad=copy.deepcopy(self.review)
            if change=='capacity':bad['literals'][2]['target']*=5
            else:bad['literals'][2]['section']='.text'
            with self.assertRaises(ValueError):patch_literals(raw,bad,mapping)

    def test_odd_extension_pads_pair_with_unmapped_blank_glyph(self):
        iso=ROOT/self.review['base_iso'];entries={e['path']:e for e in iso_inventory(iso)['files']}
        with iso.open('rb') as fp:
            def read(path):
                e=entries[path];fp.seek(e['lba']*2048);return exact(fp,e['size'])
            hed,dat=read('DATA/SYSTEM.HED'),read('DATA/SYSTEM.DAT')
        base=json.loads((ROOT/self.review['base_font_report']).read_text())
        self.assertNotIn('쌍',base['mapping'])
        newhed,newdat,mapping,info=extend_font(hed,dat,base,['쌍'])
        self.assertEqual(info['padding_glyphs'],1);self.assertEqual(info['added_glyphs'],2)
        self.assertEqual(len(mapping),len(base['mapping'])+1)
        entries,_=hed_tree(newhed);e=next(e for e in entries if e['path']=='system/kanji.dat')
        font=newdat[e['offset']:e['offset']+e['size']]
        self.assertTrue(any(decode_glyph(font,mapping['쌍']['glyph_id'])))
        self.assertFalse(any(decode_glyph(font,base['total_glyphs']+1)))


if __name__=='__main__':unittest.main()
