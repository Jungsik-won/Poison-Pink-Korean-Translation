import copy
import struct
import unittest

from status_db_codec import parse, serialize, replace_text, nontext_signature, text_fields, digest


def table(record):
    return b'\x01\0' + record


def fixture(kind):
    # Independent wire examples; zeros after each NUL are real numeric values.
    if kind == 'PPITEM':
        return b''.join(table(b'\x01\0'+bytes(header-2)+b'N\0'+bytes(stats)+b'D\0')
                        for header, stats in [(4,21),(3,28),(3,45),(3,8)]) + table(bytes(6))
    if kind == 'PPSKILL':
        return table(b'\x01\0'+bytes(4)+b'N\0'+bytes(66)+b'D\0')
    return (table(b'\x01\0'+bytes(2)+b'N\0'+bytes(56))
            + table(b'\x01\0'+b'A\0'+bytes(10)+b'B\0'+bytes(18))
            + table(b'\x01\0\x02'+bytes(12))
            + table(bytes(30))
            + table(b'\x01\0'+b'\0N\0'*3)
            + table(b'\x01\0'+bytes(17)+b'D\0')
            + table(b'\x01\0'+bytes(8)))


class StatusDBTests(unittest.TestCase):
    def test_all_sections_zero_stats_and_roundtrip(self):
        for kind, counts in [('PPITEM',5),('PPSKILL',1),('PPPARAM',7)]:
            data = fixture(kind); parsed = parse(data, kind)
            self.assertEqual(len(parsed['sections']), counts)
            self.assertEqual([s['count'] for s in parsed['sections']], [1]*counts)
            self.assertEqual(serialize(parsed), data)
            self.assertEqual(parsed['sections'][-1]['offset'] + parsed['sections'][-1]['size'], len(data))

    def test_every_truncation_and_trailing_byte_rejected(self):
        for kind in ['PPITEM', 'PPSKILL', 'PPPARAM']:
            data = fixture(kind)
            for cut in range(len(data)):
                with self.assertRaises(ValueError):parse(data[:cut], kind)
            with self.assertRaises(ValueError):parse(data+b'\0', kind)

    def test_empty_sections_are_not_padding(self):
        for kind, count in [('PPITEM',5), ('PPSKILL',1), ('PPPARAM',7)]:
            data = bytes(count*2)
            self.assertEqual(serialize(parse(data, kind)), data)

    def test_text_resize_and_nontext_preservation(self):
        for kind in ['PPITEM', 'PPSKILL', 'PPPARAM']:
            data = fixture(kind); before = parse(data, kind)
            for text in [b'', b'X', 'テスト\n１２'.encode('cp932')]:
                changes = {key:(f['value'],text) for key,f in text_fields(before)}
                out = replace_text(data,kind,changes,digest(data)); after = parse(out,kind)
                self.assertEqual(nontext_signature(before),nontext_signature(after))
                self.assertTrue(all(f['value']==text for _,f in text_fields(after)))
                self.assertEqual(len(out)-len(data),sum(len(text)-len(f['value']) for _,f in text_fields(before)))

    def test_hash_key_source_nul_encoding_capacity_guards(self):
        kind='PPSKILL';data=fixture(kind);key=(0,0,'name')
        for replacements, hashed in [({key:(b'N',b'X')},'0'*64),
                ({(0,0,'stats_0'):(b'N',b'X')},digest(data)),
                ({key:(b'wrong',b'X')},digest(data)),({key:(b'N',b'x\0y')},digest(data)),
                ({key:(b'N',b'x'*17)},digest(data)),({key:(b'N',b'\x81')},digest(data))]:
            with self.assertRaises(ValueError):replace_text(data,kind,replacements,hashed)
        out=replace_text(data,kind,{key:(b'N',b'x'*16)},digest(data))
        self.assertEqual(dict(text_fields(parse(out,kind)))[key]['value'],b'x'*16)

    def test_declared_count_and_duplicate_id_rejected(self):
        data=fixture('PPSKILL')
        with self.assertRaises(ValueError):parse(b'\x02\0'+data[2:],'PPSKILL')
        with self.assertRaises(ValueError):parse(b'\x02\0'+data[2:]*2,'PPSKILL')
        with self.assertRaises(ValueError):parse(b'\0\0'+data[2:],'PPSKILL')

    def test_ignored_high_bytes_preserved_and_semantic_edits_detected(self):
        data=bytearray(fixture('PPSKILL'))
        data[9+15]=0xab  # name NUL is byte 9; loader skips NUL+15
        data[9+23]=0xcd  # high byte of first u16 cell; loader copies its low byte only
        parsed=parse(bytes(data),'PPSKILL')
        self.assertEqual(serialize(parsed),bytes(data))
        altered=copy.deepcopy(parsed)
        field=next(f for f in altered['sections'][0]['records'][0]['fields'] if f['name']=='stats_0')
        field['value'] ^= 1
        self.assertNotEqual(nontext_signature(parsed),nontext_signature(altered))

    def test_cp932_duplicate_codepoint_keeps_original_wire_bytes(self):
        data=fixture('PPSKILL').replace(b'N\0',b'\x87\x90\0',1)
        self.assertNotEqual(b'\x87\x90'.decode('cp932').encode('cp932'),b'\x87\x90')
        self.assertEqual(serialize(parse(data,'PPSKILL')),data)

    def test_schema_numeric_and_variable_count_limits(self):
        model=parse(fixture('PPPARAM'),'PPPARAM')
        for mutate in [lambda p:p['sections'][0].update(count=2),
                       lambda p:p['sections'][0]['records'][0]['fields'][0].update(value=-1),
                       lambda p:p['sections'][0]['records'][0]['fields'][0].update(name='wrong'),
                       lambda p:p['sections'][2]['records'][0]['fields'][1].update(value=16)]:
            p=copy.deepcopy(model);mutate(p)
            with self.assertRaises(ValueError):serialize(p)
        # Fixed 600-byte native table has only 25 * 24-byte destination cells.
        with self.assertRaises(ValueError):parse(bytes(6)+b'\x1a\0'+bytes(30*26)+bytes(6),'PPPARAM')


if __name__ == '__main__':unittest.main()
