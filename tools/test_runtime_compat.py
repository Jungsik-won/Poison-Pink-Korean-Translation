"""Compatibility regressions must block ISO publication, not corrupt other files."""
import json
import configparser
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import iso_archive_stage as stage
import runtime_compat as compat
from runtime_keys import validate_bindings


def elf():
    data = bytearray(512)
    data[:6] = b'\x7fELF\x01\x01'
    struct.pack_into('<I', data, 28, 52)
    struct.pack_into('<HH', data, 42, 32, 1)
    struct.pack_into('<8I', data, 52, 1, 128, 0x1000, 0x1000, 384, 384, 7, 16)
    return data


PATCH = '[Widescreen 16:9]\npatch=1,EE,00001040,word,12345678\n'


class CompatibilityTests(unittest.TestCase):
    def test_game_input_that_would_toggle_renderer_is_blocked(self):
        cfg = configparser.ConfigParser(interpolation=None)
        cfg.optionxform = str
        cfg.read_string('[Pad1]\nL1=Keyboard/F9\n[Hotkeys]\nToggleSoftwareRendering=Keyboard/F9\n')
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            validate_bindings(cfg, ['l1'])
        cfg['Hotkeys']['ToggleSoftwareRendering'] = ''
        validate_bindings(cfg, ['l1'])
        cfg['Pad1']['L1'] = 'Keyboard/Q'
        with self.assertRaisesRegex(ValueError, 'mapping differs'):
            validate_bindings(cfg, ['l1'])

    def test_old_state_layout_is_reported_without_modifying_the_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'SLPS-25854 (12345678).01.p2s'
            ram = bytearray(32 * 1024 * 1024)
            struct.pack_into('<I', ram, 0x1040, 0x12345678)
            struct.pack_into('<I', ram, 0x62DAF0, 400)
            struct.pack_into('<f', ram, 0x62DCB4, 312.0)
            with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr('eeMemory.bin', ram)
            before = path.read_bytes()
            info = dict(serial='SLPS-25854', elf_crc='12345678')
            result = compat.inspect_states(Path(tmp), info, PATCH.encode())
            self.assertEqual(result[0]['status'], 'needs_layout_recovery')
            self.assertEqual(result[0]['missing_patch_words'], [])
            self.assertEqual(path.read_bytes(), before)
            path.rename(Path(tmp) / 'SLPS-25854 (00000000).01.p2s')
            result = compat.inspect_states(Path(tmp), info, PATCH.encode())
            self.assertEqual(result[0]['status'], 'different_elf_crc_do_not_migrate')

    def test_crc_matches_pcsx2_word_xor_including_ignored_tail(self):
        self.assertEqual(compat.pcsx2_crc(bytes.fromhex('0100000078563412ff')), '12345679')

    def test_translation_elsewhere_changes_crc_without_breaking_patch(self):
        before = elf()
        after = bytearray(before)
        after[450:455] = b'hello'
        self.assertNotEqual(compat.pcsx2_crc(before), compat.pcsx2_crc(after))
        self.assertEqual(len(compat.validate_elf(before, after, PATCH)), 1)

    def test_instruction_neighbor_and_cave_conflicts_are_rejected(self):
        for address in (0x103C, 0x1040, 0x1044):
            before = elf()
            after = bytearray(before)
            after[compat.virtual_offset(after, address)] = 1
            with self.assertRaisesRegex(ValueError, 'context changed'):
                compat.validate_elf(before, after, PATCH)

    def test_unsupported_or_duplicate_patch_is_rejected(self):
        for text in (PATCH + 'patch=1,EE,00001050,extended,00000000',
                     PATCH + 'patch=1,EE,00001040,word,12345678'):
            with self.assertRaises(ValueError):
                compat.parse_patch(text)
        self.assertEqual(len(compat.parse_patch(PATCH + '//patch=garbage\n')), 1)
        self.assertEqual(compat.patch_directives('// note\n' + PATCH), compat.patch_directives(PATCH))
        self.assertNotEqual(compat.patch_directives(PATCH + 'gsaspectratio=4:3\n'), compat.patch_directives(PATCH))

    def test_unmapped_and_overlapping_load_regions_are_rejected(self):
        data = elf()
        with self.assertRaises(ValueError):
            compat.virtual_offset(data, 0x3000)
        struct.pack_into('<H', data, 44, 2)
        data[84:116] = data[52:84]
        with self.assertRaises(ValueError):
            compat.virtual_offset(data, 0x1040)

    def test_sidecar_conflict_never_overwrites_existing_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            iso = Path(tmp) / 'test.iso'
            info = dict(patch_filename='SLPS-25854_12345678.pnach', elf_crc='12345678')
            dest, created = compat.publish_sidecar(iso, info, PATCH.encode(), 'hash')
            self.assertTrue(created)
            self.assertFalse(compat.publish_sidecar(iso, info, PATCH.encode(), 'hash')[1])
            with self.assertRaises(ValueError):
                compat.publish_sidecar(iso, info, b'different', 'hash')
            self.assertEqual((dest / 'patches' / info['patch_filename']).read_text(), PATCH)

    def test_compatibility_failure_prevents_iso_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'source.iso', Path(tmp) / 'output.iso'
            source.write_bytes(b'fixture')
            with patch.object(compat, 'inspect_iso', side_effect=ValueError('patch conflict')):
                with self.assertRaisesRegex(ValueError, 'patch conflict'):
                    stage.overlay(source, output, [], compat.digest(source.read_bytes()))
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(), b'fixture')
            self.assertEqual(list(Path(tmp).glob('*.partial')), [])

    def test_profile_checks_per_game_override_and_accepts_repeated_list_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ['inis', 'patches', 'gamesettings']:
                (root / d).mkdir()
            (root / 'inis/PCSX2.ini').write_text('[EmuCore]\nEnableWideScreenPatches=true\n'
                                                '[GameList]\nRecursivePaths=a\nRecursivePaths=b\n')
            info = dict(serial='SLPS-25854', elf_crc='12345678', patch_filename='SLPS-25854_12345678.pnach')
            (root / 'patches' / info['patch_filename']).write_text(PATCH)
            (root / 'gamesettings/SLPS-25854_12345678.ini').write_text('[EmuCore]\nEnableWideScreenPatches=false\n')
            result = compat.inspect_profile(root, info, PATCH.encode())
            self.assertEqual(result['findings'], ['EnableWideScreenPatches is disabled'])

    def test_successful_iso_publication_has_matching_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'source.iso', Path(tmp) / 'output.iso'
            source.write_bytes(b'fixture')
            info = dict(patch_filename='SLPS-25854_12345678.pnach', elf_crc='12345678', patch_count=1)
            with patch.object(compat, 'inspect_iso', return_value=(info, PATCH.encode())):
                report = stage.overlay(source, output, [], compat.digest(source.read_bytes()))
            self.assertEqual(output.read_bytes(), source.read_bytes())
            manifest = json.loads((Path(report['runtime_compatibility']['sidecar']) / 'manifest.json').read_text())
            self.assertEqual(manifest['iso_sha256'], compat.digest(output.read_bytes()))

    def test_publication_failure_removes_only_new_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'source.iso', Path(tmp) / 'output.iso'
            source.write_bytes(b'fixture')
            info = dict(patch_filename='SLPS-25854_12345678.pnach', elf_crc='12345678', patch_count=1)
            with patch.object(compat, 'inspect_iso', return_value=(info, PATCH.encode())), \
                 patch.object(stage.os, 'link', side_effect=FileExistsError('race')):
                with self.assertRaises(FileExistsError):
                    stage.overlay(source, output, [], compat.digest(source.read_bytes()))
            self.assertFalse(output.exists())
            self.assertFalse(Path(str(output) + '.pcsx2').exists())


if __name__ == '__main__':
    unittest.main()
