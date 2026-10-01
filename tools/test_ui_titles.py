import copy
import json
import struct
import unittest
from localization_pipeline import ROOT,sha
from ui_titles import patch_literals


class ElfTests(unittest.TestCase):
    def setUp(self):
        self.raw=(ROOT/'Poison Pink (Japan)/SLPS_258.54').read_bytes()
        self.review=json.loads((ROOT/'localization/ui_titles.json').read_text())
        chars=sorted({c for r in self.review['literals'] for c in r['target']})
        self.mapping={c:dict(code_hex=(0x989f+i).to_bytes(2,'big').hex()) for i,c in enumerate(chars)}

    def test_bounded_strings_preserve_addresses_and_instructions(self):
        out,checks=patch_literals(self.raw,self.review,self.mapping)
        self.assertEqual(len(out),len(self.raw));self.assertEqual(out[0x1000:0x30ed10],self.raw[0x1000:0x30ed10])
        for r,c in zip(self.review['literals'],checks):
            off=r['offset'];length=len(bytes.fromhex(r['raw_hex']))
            self.assertEqual(out[off+c['encoded_bytes']:off+length+1],bytes(length+1-c['encoded_bytes']))
            for p in r['pointer_offsets']:self.assertEqual(out[p:p+4],self.raw[p:p+4])

    def test_reject_expansion_wrong_pointer_unreviewed_overlap(self):
        for change in ('long','pointer','draft','overlap','source','direct'):
            r=copy.deepcopy(self.review)
            if change=='long':r['literals'][0]['target']*=4
            elif change=='pointer':r['literals'][0]['pointer_offsets']=[0]
            elif change=='draft':r['literals'][0]['status']='draft'
            elif change=='overlap':r['literals'].append(r['literals'][0])
            elif change=='direct':
                direct=next(row for row in r['literals'] if row.get('direct_reference'))
                direct['direct_reference']['offset']+=4
            else:r['elf_sha256']='bad'
            with self.assertRaises(ValueError):patch_literals(self.raw,r,self.mapping)


if __name__=='__main__':unittest.main()
