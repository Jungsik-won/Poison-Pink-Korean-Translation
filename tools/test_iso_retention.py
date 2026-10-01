import gzip
import hashlib
import io
import struct
import tempfile
import unittest
from pathlib import Path
from iso_retention import MAGIC,CHUNK,reconstruct,load_blocks


class RetentionTests(unittest.TestCase):
    def test_reconstruction_across_chunks_and_short_final_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';patch=Path(tmp)/'patch.gz'
            raw=b'A'*CHUNK+b'B'*31;source.write_bytes(raw)
            with gzip.open(patch,'wb') as fp:
                fp.write(MAGIC+struct.pack('<QI',0,4)+b'TEST'+struct.pack('<QI',CHUNK,31)+b'C'*31)
            out=io.BytesIO();h,n=reconstruct(source,patch,out)
            expected=b'TEST'+raw[4:CHUNK]+b'C'*31
            self.assertEqual(out.getvalue(),expected)
            self.assertEqual((h,n),(hashlib.sha256(expected).hexdigest(),len(raw)))
            self.assertEqual(source.read_bytes(),raw)

    def test_truncated_overlapping_and_past_eof_deltas_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';source.write_bytes(b'A'*32);patch=Path(tmp)/'patch.gz'
            for body in [struct.pack('<QI',0,5)+b'bad',struct.pack('<QI',0,4)+b'abcd'+struct.pack('<QI',2,2)+b'ef',struct.pack('<QI',99,1)+b'x']:
                with gzip.open(patch,'wb') as fp:fp.write(MAGIC+body)
                with self.assertRaises(ValueError):reconstruct(source,patch)
