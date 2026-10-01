import tempfile,unittest
from pathlib import Path
from extract_all import ROOT,literal,safe_path,rgba
from korean_sentence_probe import archive_member
from ui_texture_codec import parse,preview_rgba
from extract_all import rtb_strings


class ExtractionTests(unittest.TestCase):
    def test_source_bytes_and_blank_targets_survive_cp932_views(self):
        row=literal(b'\x83\x65\x81[\x83W',id='x')
        self.assertEqual(row['target'],'');self.assertEqual(row['raw_hex'],'8365815b8357')
        bad=literal(b'\x81',id='bad')
        self.assertIsNone(bad['source']);self.assertTrue(bad['decode_error']);self.assertEqual(bad['raw_hex'],'81')

    def test_output_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            for name in ['../source','/source']:
                with self.assertRaises(ValueError):safe_path(out,name)
            self.assertEqual(safe_path(out,'DMAP/text.txt'),out/'DMAP/text.txt')

    def test_actual_rtb_literals_point_to_exact_source_bytes(self):
        _,raw=archive_member('DMAP','dmap/script/t00_0010.rtb')
        rows=list(rtb_strings(raw,'dmap/script/t00_0010.rtb','test'))
        self.assertTrue(rows)
        for r in rows:
            off=r['payload_offset'];value=bytes.fromhex(r['raw_hex'])
            self.assertEqual(raw[off:off+len(value)],value);self.assertEqual(r['target'],'')

    def test_fast_png_decoder_agrees_with_original_codec(self):
        for archive,path in [('DMAP','dmap/ev/ev136.tm2'),('STATUS','status/sys000.tm2')]:
            _,raw=archive_member(archive,path);m=parse(raw)
            self.assertEqual(rgba(m).tobytes(),preview_rgba(m))
