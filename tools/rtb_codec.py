#!/usr/bin/env python3
"""Strict Ratonga RTB wire parser, lossless serializer and string-only editor.

Opcode formats are grounded in this revision's ELF readers, not pattern scans.
Packed operand bits and several metadata meanings remain intentionally unnamed.
"""
import argparse
import copy
import json
import struct
from pathlib import Path
from localization_pipeline import ROOT, hed_tree, sha, file_hash, write_json
from iso_archive_stage import SOURCE, exact, source_sha

REGISTRY = json.loads((ROOT/'localization/rtb_opcodes.json').read_text())
OPCODES = {r['op']:r for r in REGISTRY['opcodes']}


class Reader:
    def __init__(self, data):
        self.data, self.pos, self.fields = data, 0, []

    def read(self, kind, size=None):
        start = self.pos
        if kind == 'compact':
            if start >= len(self.data): raise ValueError('Truncated compact integer')
            marker = self.data[start]
            size = 3 if marker == 254 else 5 if marker == 255 else 1
        elif kind == 'u8': size = 1
        elif kind == 'u32': size = 4
        elif kind != 'bytes': raise ValueError('Unknown field kind')
        if size is None or size < 0 or start + size > len(self.data):
            raise ValueError('Truncated field at 0x{:x}'.format(start))
        raw = self.data[start:start+size]
        self.pos += size
        if kind == 'bytes': value = raw.hex()
        elif kind == 'compact': value = int.from_bytes(raw[1:] if size > 1 else raw, 'little')
        else: value = int.from_bytes(raw, 'little')
        self.fields.append(dict(kind=kind, width=size, value=value, offset=start))
        return value

    def count(self):
        value = self.read('compact')
        if value > len(self.data): raise ValueError('Implausible collection count')
        return value

    def text(self):
        return bytes.fromhex(self.read('bytes', self.read('u8')))


def parse(data):
    r = Reader(data)
    symbols = {}
    for _ in range(r.count()):
        ident = r.read('u32')
        symbols[ident] = r.text().decode('ascii', errors='strict')
    source_files = [r.text().decode('ascii', errors='strict') for _ in range(r.count())]
    type_map = [(r.read('u32'),r.read('u32')) for _ in range(r.count())]
    type_descriptors = [(r.read('compact'),r.read('u32')) for _ in range(r.count())]
    functions = []

    def function(name, symbol):
        start = r.pos
        return_type = r.read('u32')
        locals_ = [(r.read('u32'),r.read('u32')) for _ in range(r.count())]
        meta = [r.read('compact') for _ in range(4)]
        declared_count, allocation = meta[2:]
        if declared_count > len(data): raise ValueError('Implausible instruction count')
        ops = []
        while True:
            off = r.pos
            op = r.read('u8')
            if op == 0: break
            if op not in OPCODES: raise ValueError('Unknown opcode {:02x} at {:x}'.format(op,off))
            packed = r.read('u32')
            reader = OPCODES[op]['reader']
            args = []
            string_fields = None
            if reader in (0x236ab0,0x236bd0,0x237418,0x237308): args = [r.read('u32')]
            elif reader == 0x236cf0:
                length_field = len(r.fields)
                text = r.text()
                args = [text.hex()]
                string_fields = [length_field,length_field+1]
            elif reader == 0x236fa0: args = [r.read('u32'),r.read('u32')]
            elif reader == 0x236ff0: args = [r.read('compact')]
            elif reader in (0x237078,0x2370d8,0x237138,0x237198):
                args = [r.read('u32'),r.read('u32'),r.read('compact')]
            elif reader != 0x3b7530: raise ValueError('Unknown opcode reader')
            ops.append(dict(offset=off,end=r.pos,opcode=op,packed=packed,args=args,string_fields=string_fields))
        if len(ops) != declared_count: raise ValueError('Instruction count mismatch in '+name)
        if sum(OPCODES[o['opcode']]['memory_bytes'] for o in ops) > allocation:
            raise ValueError('Instruction allocation is too small')
        branches = []
        for i,o in enumerate(ops):
            if o['opcode'] in (0x6b,0x6c,0x6d):
                delta = struct.unpack('<i',struct.pack('<I',o['args'][0]))[0]
                target = i + delta
                if not 0 <= target < len(ops): raise ValueError('Branch outside function')
                branches.append(dict(instruction=i,target=target,delta=delta,opcode=o['opcode']))
        functions.append(dict(name=name,symbol=symbol,offset=start,end=r.pos,return_type=return_type,
                              locals=locals_,metadata=meta,instructions=ops,branches=branches))

    exports = []
    for _ in range(r.count()):
        symbol = r.read('u32')
        present = r.read('compact')
        if present not in (0,1): raise ValueError('Unsupported function presence marker')
        exports.append((symbol,present))
        if present: function(symbols.get(symbol,hex(symbol)),symbol)
    function('<module>',None)
    global_slots = r.read('u32')
    if r.pos != len(data): raise ValueError('Unparsed trailing bytes')
    result = dict(symbols=symbols,sources=source_files,type_map=type_map,type_descriptors=type_descriptors,
                  exports=exports,functions=functions,global_slots=global_slots,fields=r.fields)
    if serialize(result) != data: raise ValueError('RTB byte roundtrip mismatch')
    return result


def serialize(parsed):
    parts = []
    for f in parsed['fields']:
        value,kind,width = f['value'],f['kind'],f['width']
        if kind == 'bytes':
            raw = bytes.fromhex(value)
            if len(raw) != width: raise ValueError('Byte field size mismatch')
        elif kind == 'compact':
            if width == 1:
                if not 0 <= value < 254: raise ValueError('Compact width overflow')
                raw = bytes([value])
            elif width in (3,5):
                raw = bytes([254 if width == 3 else 255])+value.to_bytes(width-1,'little')
            else: raise ValueError('Invalid compact width')
        elif kind in ('u8','u32'):
            if width != (1 if kind=='u8' else 4): raise ValueError('Invalid integer width')
            raw = value.to_bytes(width,'little')
        else: raise ValueError('Unknown field kind')
        parts.append(raw)
    return b''.join(parts)


def control_signature(parsed):
    return [(f['symbol'],f['metadata'],f['branches'],[o['opcode'] for o in f['instructions']])
            for f in parsed['functions']]


def replace_strings(data, replacements, expected_sha256):
    """Edit only string length+payload fields; retain every instruction and reference.

    replacements: {original opcode file offset: (expected original bytes, new bytes)}.
    This is a wire-format operation; callers must supply reviewed text and encoding.
    """
    if sha(data) != expected_sha256: raise ValueError('RTB source hash mismatch')
    parsed = parse(data)
    strings = {o['offset']:o for f in parsed['functions'] for o in f['instructions'] if o['opcode']==0x33}
    edited = copy.deepcopy(parsed)
    allowed = set()
    for off,(original,new) in replacements.items():
        if off not in strings: raise ValueError('Replacement is not an instruction string')
        op = strings[off]
        if bytes.fromhex(op['args'][0]) != original: raise ValueError('Literal source mismatch')
        if not isinstance(new,bytes) or len(new)>255: raise ValueError('String exceeds uint8 length')
        length_idx,payload_idx = op['string_fields']
        edited['fields'][length_idx]['value'] = len(new)
        edited['fields'][payload_idx].update(value=new.hex(),width=len(new))
        allowed.update((length_idx,payload_idx))
    result = serialize(edited)
    checked = parse(result)
    if control_signature(parsed) != control_signature(checked): raise ValueError('Control structure changed')
    if len(parsed['fields']) != len(checked['fields']): raise ValueError('Field count changed')
    for i,(old,new) in enumerate(zip(parsed['fields'],checked['fields'])):
        if i not in allowed and any(old[k]!=new[k] for k in ('kind','width','value')):
            raise ValueError('Nontext field changed')
    return result


def summary(parsed):
    functions=parsed['functions']
    return dict(functions=len(functions),instructions=sum(len(f['instructions']) for f in functions),
                strings=sum(o['opcode']==0x33 for f in functions for o in f['instructions']),
                branches=sum(len(f['branches']) for f in functions),roundtrip=True,
                all_bytes_parsed=True,all_branch_targets_within_function=True)


def audit():
    elf=SOURCE/'SLPS_258.54'
    if file_hash(elf)!=REGISTRY['source_elf_sha256'] or file_hash(elf)!=source_sha(elf):
        raise ValueError('ELF revision mismatch')
    for name in ('DMAP.HED','DMAP.DAT'):
        p=SOURCE/'DATA'/name
        if file_hash(p)!=source_sha(p): raise ValueError('DMAP source mismatch')
    entries,_=hed_tree((SOURCE/'DATA/DMAP.HED').read_bytes())
    candidates={}
    for line in (ROOT/'localization/rtb_candidates.jsonl').open():
        candidate=json.loads(line)
        candidates.setdefault(candidate['path'],[]).append(candidate)
    rows=[]; matched=0; mismatches=[]; exclusions=[]
    with (SOURCE/'DATA/DMAP.DAT').open('rb') as fp:
        for e in entries:
            if not e['path'].endswith('.rtb'): continue
            fp.seek(e['offset']);data=exact(fp,e['size']);parsed=parse(data)
            row=dict(path=e['path'],sha256=sha(data),bytes=len(data),**summary(parsed));rows.append(row)
            strings={o['offset']:o for f in parsed['functions'] for o in f['instructions'] if o['opcode']==0x33}
            for candidate in candidates.pop(e['path'],[]):
                op=strings.get(candidate['opcode_offset'])
                if (op is not None and op['args'][0]==candidate['raw_hex']
                        and candidate['member_sha256']==sha(data)
                        and candidate['source_sha256']==sha(bytes.fromhex(op['args'][0]))):
                    matched+=1
                else:
                    mismatches.append(candidate['id'])
                    exclusions.append(dict(id=candidate['id'],source_sha256=candidate['source_sha256'],
                        member_sha256=candidate['member_sha256'],status='exclude',
                        reason='ELF 로더 기반 전체 파싱에서 문자열 명령 경계가 아님'))
            if e['path']=='dmap/script/t00_0010.rtb':
                detail={k:v for k,v in parsed.items() if k!='fields'}
                write_json(ROOT/'reports/t00_0010_structure.json',detail)
    totals={k:sum(r[k] for r in rows) for k in ('bytes','functions','instructions','strings','branches')}
    report=dict(schema_version=1,files=len(rows),totals=totals,entries=rows,all_roundtrips_passed=True,
                unknown_bytes=0,branch_unit='relative instruction index from current instruction',
                runtime_length_change_verified=False,full_opcode_semantics_verified=False,
                evidence='docs/RTB_FORMAT.md',elf_sha256=REGISTRY['source_elf_sha256'])
    report['existing_candidate_crosscheck']=dict(matched=matched,mismatches=mismatches,
        missing_paths=sorted(candidates),roles_auto_approved=False)
    if candidates: raise ValueError('Candidate paths absent from RTB corpus')
    write_json(ROOT/'reports/rtb_structure_audit.json',report)
    write_json(ROOT/'localization/rtb_candidate_exclusions.json',dict(
        catalog_sha256=file_hash(ROOT/'localization/rtb_candidates.jsonl'),
        evidence='reports/rtb_structure_audit.json',entries=exclusions))
    print(json.dumps(dict(files=len(rows),**totals)),flush=True)


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    audit()
