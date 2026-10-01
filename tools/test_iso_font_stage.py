import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import iso_archive_stage as stage
from font_pair_probe import decode_glyph, encode_glyph, japanese_index, diagnostic_hangul
from localization_pipeline import sha


def both(value):
    return struct.pack('<I', value) + struct.pack('>I', value)


def iso_record(lba, size, name, directory=False):
    length = 33 + len(name) + (len(name) % 2 == 0)
    data = bytearray(length)
    data[0] = length
    data[2:10] = both(lba)
    data[10:18] = both(size)
    data[25] = 2 if directory else 0
    data[28:32] = b'\1\0\0\1'
    data[32] = len(name)
    data[33:33+len(name)] = name
    return data


class StageTests(unittest.TestCase):
    def test_overlay_preserves_padding_and_cross_chunk_ranges(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'a', Path(tmp)/'b'
            original = bytes(range(100))
            source.write_bytes(original)
            replacements = [dict(offset=3, data=b'abcdef', expected_sha256=sha(original[3:9])),
                            dict(offset=90, data=b'0123456789', expected_sha256=sha(original[90:]))]
            with patch.object(stage, 'CHUNK', 4):
                report = stage.overlay(source, output, replacements, sha(original))
            self.assertEqual(output.read_bytes(), original[:3]+b'abcdef'+original[9:90]+b'0123456789')
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(report['changed_bytes'], 16)

    def test_noop_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'a', Path(tmp)/'b'
            source.write_bytes(b'\0\0\x82abcPAD\xff')
            report = stage.overlay(source, output, [], sha(source.read_bytes()))
            self.assertEqual(report['source_sha256'], report['output_sha256'])
            self.assertEqual(report['changed_bytes'], 0)

    def test_hash_mismatch_never_publishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'a', Path(tmp)/'b'
            source.write_bytes(b'original')
            with self.assertRaises(ValueError):
                stage.overlay(source, output, [], 'wrong')
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(tmp).glob('*.partial')), [])

    def test_bad_region_hash_never_publishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'a', Path(tmp)/'b'
            source.write_bytes(b'original')
            with self.assertRaises(ValueError):
                stage.overlay(source, output, [dict(offset=0, data=b'no', expected_sha256='wrong')], sha(b'original'))
            self.assertFalse(output.exists())

    def test_overlap_bounds_and_existing_output_rejected(self):
        for replacements in ([dict(offset=0,data=b'ab'),dict(offset=1,data=b'b')],
                             [dict(offset=99,data=b'ab')], [dict(offset=-1,data=b'x')]):
            with self.assertRaises(ValueError):
                stage.validate_ranges(100, replacements)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'a';source.write_bytes(b'abc')
            with self.assertRaises(ValueError):
                stage.overlay(source, source, [], sha(b'abc'))

    def test_iso_extent_and_name_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=bytearray(20*2048)
            pvd=bytearray(2048);pvd[:7]=b'\x01CD001\x01';pvd[80:88]=both(20)
            pvd[128:132]=b'\0\x08\x08\0'
            root=iso_record(18,2048,b'\0',True);pvd[156:156+len(root)]=root
            data[16*2048:17*2048]=pvd
            records=root+iso_record(18,2048,b'\1',True)+iso_record(19,3,b'DI.;1')
            data[18*2048:18*2048+len(records)]=records;data[19*2048:19*2048+3]=b'abc'
            path=Path(tmp)/'test.iso';path.write_bytes(data)
            result=stage.iso_inventory(path)
            self.assertEqual(result['files'][0]['path'],'DI')
            self.assertEqual(result['files'][0]['lba'],19)
            data[16*2048+84]^=1;path.write_bytes(data)
            with self.assertRaises(ValueError):stage.iso_inventory(path)


class FontTests(unittest.TestCase):
    def test_pair_components_do_not_interfere(self):
        font=bytearray(288)
        even=[i%4 for i in range(576)]
        odd=[(i//24)%4 for i in range(576)]
        encode_glyph(font,0,even);encode_glyph(font,1,odd)
        self.assertEqual(decode_glyph(font,0),even)
        self.assertEqual(decode_glyph(font,1),odd)
        encode_glyph(font,1,diagnostic_hangul('가'))
        self.assertEqual(decode_glyph(font,0),even)

    def test_coordinates_match_known_bytes(self):
        font=bytearray(288);pixels=[0]*576
        pixels[0]=1;pixels[1]=2;pixels[24]=3
        encode_glyph(font,0,pixels)
        self.assertEqual(font[0],0x21)
        self.assertEqual(font[12],3)
        encode_glyph(font,1,pixels)
        self.assertEqual(font[0],0xa5)
        self.assertEqual(font[12],15)

    def test_code_ranges(self):
        self.assertEqual(japanese_index(0x8140),0)
        self.assertEqual(japanese_index(0x8180),64)
        self.assertEqual(japanese_index(0x8240),189)
        self.assertEqual(japanese_index(0x8365),415)
        self.assertEqual(japanese_index(0x93fa),3210)
        with self.assertRaises(ValueError):japanese_index(0x817f)

    def test_invalid_font_inputs(self):
        with self.assertRaises(ValueError):decode_glyph(bytes(288),2)
        with self.assertRaises(ValueError):encode_glyph(bytearray(288),0,[4]*576)


if __name__=='__main__':unittest.main()
