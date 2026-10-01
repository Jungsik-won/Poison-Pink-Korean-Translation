"""Regression checks for source integrity and candidate/translation validation."""
import contextlib
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import localization_pipeline as pipeline


def record(off, size, name, stamp=0):
    return struct.pack('<II32sI', off, size, name.encode('ascii'), stamp)


class PipelineTests(unittest.TestCase):
    def test_hed_nested_directories_use_record_indices(self):
        hed = (record(2, 4, 'root') + record(0, 0, '--DirEnd--') +
               record(0, 1, '..') + record(6, 3, 'sub') +
               record(0, 10, 'a.bin', 1) + record(0, 0, '--DirEnd--') +
               record(2, 4, '..') + record(16384, 20, 'a.bin', 1) +
               record(0, 0, '--DirEnd--'))
        files, dirs = pipeline.hed_tree(hed)
        self.assertEqual({e['path'] for e in files}, {'root/a.bin', 'root/sub/a.bin'})
        self.assertEqual(len(dirs), 2)

    def test_hed_rejects_trailing_partial_record_and_bad_range(self):
        hed = (record(2, 3, 'root') + record(0, 0, '--DirEnd--') +
               record(0, 1, '..') + record(0, 10, 'a.bin', 1) + record(0, 0, '--DirEnd--'))
        with self.assertRaises(ValueError):
            pipeline.hed_tree(hed + b'\0')
        with self.assertRaises(ValueError):
            pipeline.hed_tree(record(999, 3, 'root') + hed[44:])

    def test_candidates_keep_raw_offsets_and_decode_failures(self):
        good = 'テージ'.encode('cp932')
        data = b'\xfe\0\0' + b'\x33\x01ABC' + bytes([len(good)]) + good + b'\x65\x01ABC'
        data += b'\x33\x01DEF\x01\x81'  # incomplete CP932, kept for audit
        data += b'\x33\x01GHI\xff'  # truncated payload, not accepted
        rows = pipeline.candidates(data, dict(index=10, path='dmap/script/a.rtb'))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['opcode_offset'], 3)
        self.assertEqual(rows[0]['payload_offset'], 9)
        self.assertEqual(bytes.fromhex(rows[0]['raw_hex']), good)
        self.assertIsNone(rows[1]['source'])

    def test_symbol_table_is_skipped(self):
        fake = b'\x33\x01ABC\x01X'
        data = b'\xfe\x01\x00' + b'HASH' + bytes([len(fake)]) + fake
        self.assertEqual(pipeline.candidates(data, dict(index=10, path='a.rtb')), [])

    def test_lint_detects_source_drift_duplicates_and_nfd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline.write_jsonl(root / 'catalog.jsonl', [dict(id='a', source='原文', source_sha256='hash')])
            row = dict(id='a', source='wrong', source_sha256='hash', target='\u1100\u1161', status='draft')
            pipeline.write_jsonl(root / 'translations.jsonl', [row, row])
            with patch.object(pipeline, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                result = pipeline.lint(dict(catalog='catalog.jsonl'), root / 'translations.jsonl')
            self.assertTrue(result)
            report = json.loads((root / 'reports/translation_lint.json').read_text())
            self.assertEqual(len(report['errors']), 5)
            self.assertFalse(report['build_ready'])

    def test_source_lock_drift_fails_before_replacing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'source').mkdir()
            (root / 'source/file').write_bytes(b'changed')
            pipeline.write_json(root / 'lock.json', dict(files={'file': dict(size=3, sha256='old')}))
            with patch.object(pipeline, 'ROOT', root), self.assertRaisesRegex(ValueError, 'NOT updated'):
                pipeline.audit(dict(source_root='source', source_lock='lock.json'))
            self.assertEqual(json.loads((root / 'lock.json').read_text())['files']['file']['sha256'], 'old')

    def test_structural_exclusions_block_translation_and_new_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = [dict(id='false',source='原文',source_sha256='h',classification_hint='japanese_candidate')]
            pipeline.write_jsonl(root/'catalog.jsonl',catalog)
            pipeline.write_json(root/'exclude.json',dict(catalog_sha256=pipeline.file_hash(root/'catalog.jsonl'),
                entries=[dict(id='false',status='exclude')]))
            row=dict(id='false',source='原文',source_sha256='h',target='번역',status='draft')
            pipeline.write_jsonl(root/'translations.jsonl',[row])
            config=dict(catalog='catalog.jsonl',candidate_exclusions='exclude.json')
            with patch.object(pipeline,'ROOT',root), contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(pipeline.lint(config,root/'translations.jsonl'))
                pipeline.template(config,root/'new.jsonl')
            self.assertEqual((root/'new.jsonl').read_text(),'')
            report=json.loads((root/'reports/translation_lint.json').read_text())
            self.assertEqual(report['structurally_excluded_rows'],1)
            self.assertIn('structurally excluded',report['errors'][0]['error'])

    def test_stale_structural_exclusions_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'catalog.jsonl').write_text('changed')
            pipeline.write_json(root/'exclude.json',dict(catalog_sha256='old',entries=[]))
            with patch.object(pipeline,'ROOT',root), self.assertRaisesRegex(ValueError,'stale'):
                pipeline.structural_exclusions(dict(catalog='catalog.jsonl',candidate_exclusions='exclude.json'))


if __name__ == '__main__':
    unittest.main()
