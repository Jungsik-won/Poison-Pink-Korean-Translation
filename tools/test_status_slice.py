import copy
import unittest
from status_slice import apply_review
from status_db_codec import parse, digest, nontext_signature
from test_status_db_codec import fixture


class StatusSliceTests(unittest.TestCase):
    def row(self):
        data=fixture('PPSKILL')
        return dict(id='test',kind='PPSKILL',section=0,record_index=0,record_id=1,field='name',
                    source='N',raw_hex=b'N'.hex(),source_sha256=digest(b'N'),member_sha256=digest(data),
                    target='Longer',status='reviewed',reviewer='test')

    def test_reviewed_change_preserves_all_numeric_fields(self):
        data=fixture('PPSKILL');out,checks=apply_review('PPSKILL',data,[self.row()],{})
        self.assertEqual(len(out)-len(data),5)
        self.assertEqual(nontext_signature(parse(data,'PPSKILL')),nontext_signature(parse(out,'PPSKILL')))
        self.assertEqual(checks[0]['after_bytes'],6)

    def test_review_source_id_duplicates_unmapped_and_capacity_guards(self):
        data=fixture('PPSKILL');base=self.row()
        for fields in [dict(status='draft'),dict(reviewer=''),dict(member_sha256='bad'),dict(record_id=2),
                       dict(source='different'),dict(source_sha256='bad'),dict(target='한'),dict(target='X'*17),
                       dict(target='N1')]:
            row=dict(base,**fields)
            with self.assertRaises(ValueError):apply_review('PPSKILL',data,[row],{})
        with self.assertRaises(ValueError):apply_review('PPSKILL',data,[base,copy.deepcopy(base)],{})


if __name__=='__main__':unittest.main()
