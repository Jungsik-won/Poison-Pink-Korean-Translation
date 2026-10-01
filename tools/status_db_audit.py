#!/usr/bin/env python3
"""Reproduce STATUS DB field/EOF/roundtrip and offline text-resize checks."""
import json
from pathlib import Path

from localization_pipeline import ROOT, hed_tree, file_hash, write_json
from status_db_codec import (SCHEMAS, LOADER_VAS, parse, serialize, digest,
                             text_fields, replace_text, nontext_signature)

SOURCE = ROOT / 'Poison Pink (Japan)'
OUT = ROOT / 'build/db_audit'
RANGES = {
    'item_dispatch': (0x2746d8,0x27475c), 'item_0': (0x275118,0x2753b0),
    'item_1': (0x275550,0x2757cc), 'item_2': (0x2758b8,0x275b48),
    'item_3': (0x275ba0,0x275d4c), 'item_4': (0x275e08,0x275efc),
    'skill_dispatch': (0x276a98,0x276aec), 'skill_0': (0x276af0,0x276e3c),
    'param_dispatch': (0x26bcd8,0x26bd74), 'param_0': (0x26c2e0,0x26c624),
    'param_1': (0x26ca18,0x26cc38), 'param_2': (0x26ccd0,0x26ce80),
    'param_3': (0x26cef0,0x26d0b8), 'param_4': (0x26d110,0x26d26c),
    'param_5': (0x26d2c8,0x26d4c8), 'param_6': (0x26d568,0x26d6b8),
    'strcpy_scalar': (0x3589f0,0x358a14), 'strlen_scalar': (0x3592ec,0x359310),
}


def encoded_model(value):
    if isinstance(value, bytes):
        try:
            view = value.decode('cp932', errors='strict')
            error = None
        except UnicodeDecodeError as exc:
            view, error = None, str(exc)
        return dict(raw_hex=value.hex(), cp932_view=view, decode_error=error)
    if isinstance(value, dict):return {k:encoded_model(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):return [encoded_model(v) for v in value]
    return value


def audit():
    lock = json.loads((ROOT/'localization/source.lock.json').read_text())['files']
    checked = {}
    for relative in ['DATA/STATUS.HED','DATA/STATUS.DAT','SLPS_258.54']:
        path = SOURCE / relative
        actual = dict(size=path.stat().st_size, sha256=file_hash(path))
        if actual != lock[relative]:
            raise ValueError('Source lock mismatch: ' + relative)
        checked[relative] = actual
    files, _ = hed_tree((SOURCE/'DATA/STATUS.HED').read_bytes())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'experiments').mkdir(exist_ok=True)
    elf = (SOURCE/'SLPS_258.54').read_bytes()
    evidence = []
    for label,(start,end) in RANGES.items():
        raw=elf[start-0xff000:end-0xff000]
        evidence.append(dict(label=label,va_start=hex(start),va_end_exclusive=hex(end),
                             file_offset=hex(start-0xff000),sha256=digest(raw),raw_hex=raw.hex()))
    write_json(OUT/'elf_evidence.json',dict(elf_sha256=checked['SLPS_258.54']['sha256'],ranges=evidence))
    report = dict(schema_version=1,source_files=checked,source_lock_matched=True,
                  elf_evidence='build/db_audit/elf_evidence.json',
                  codec_sha256=file_hash(Path(__file__).with_name('status_db_codec.py')),
                  audit_tool_sha256=file_hash(Path(__file__)),files={})
    for kind in SCHEMAS:
        path = 'status/'+kind+'.dat'
        matches = [e for e in files if e['path']==path]
        if len(matches)!=1:raise ValueError('Missing/ambiguous archive path: '+path)
        entry = matches[0]
        with (SOURCE/'DATA/STATUS.DAT').open('rb') as fp:
            fp.seek(entry['offset']);data=fp.read(entry['size'])
        if len(data)!=entry['size']:raise ValueError('Truncated member')
        model=parse(data,kind)
        if serialize(model)!=data:raise ValueError('Roundtrip mismatch')
        (OUT/(kind+'.dat')).write_bytes(data)
        write_json(OUT/(kind+'.fields.json'),encoded_model(model))
        schema_caps = {(s,name):cap for s,schema in enumerate(SCHEMAS[kind]) for name,typ,cap in schema if typ=='z'}
        errors, sections = [], []
        all_text = list(text_fields(model))
        for key,field in all_text:
            try:field['value'].decode('cp932',errors='strict')
            except UnicodeError as exc:errors.append(dict(key=key,offset=field['offset'],error=str(exc)))
        for s in model['sections']:
            strings=[(key,f) for key,f in all_text if key[0]==s['index']]
            names=sorted(set(key[2] for key,f in strings))
            ids=[r['fields'][0]['value'] for r in s['records'] if r['fields'][0]['name']=='id']
            sections.append(dict(index=s['index'],loader_va=hex(LOADER_VAS[kind][s['index']]),
                offset=s['offset'],end=s['offset']+s['size'],records=s['count'],
                id_min=min(ids) if ids else None,id_max=max(ids) if ids else None,
                unique_ids=len(set(ids)) if ids else None,
                text_fields={n:dict(count=sum(k[2]==n for k,f in strings),
                    nonempty=sum(k[2]==n and bool(f['value']) for k,f in strings),
                    max_source_bytes=max((len(f['value']) for k,f in strings if k[2]==n),default=0),
                    max_replacement_bytes=schema_caps[(s['index'],n)]-1) for n in names}))
        trials=[]
        for variant in ['empty','same_length','capacity']:
            changes={}
            for key,f in all_text:
                size=0 if variant=='empty' else len(f['value']) if variant=='same_length' else schema_caps[(key[0],key[2])]-1
                changes[key]=(f['value'],b'X'*size)
            out=replace_text(data,kind,changes,digest(data)); new=parse(out,kind)
            if nontext_signature(model)!=nontext_signature(new):raise ValueError('Nontext signature mismatch')
            name=kind+'-'+variant+'.dat'
            (OUT/'experiments'/name).write_bytes(out)
            trials.append(dict(variant=variant,path='build/db_audit/experiments/'+name,size=len(out),
                               sha256=digest(out),all_text_fields_targeted=len(changes),
                               nontext_fields_unchanged=True,record_counts_unchanged=True,exact_eof=True))
        numeric=nontext_signature(model)
        report['files'][kind]=dict(member=entry,bytes=len(data),sha256=digest(data),
            sections=sections,records=sum(s['count'] for s in model['sections']),
            text_fields=len(all_text),nonempty_text_fields=sum(bool(f['value']) for _,f in all_text),
            cp932_decode_errors=errors,exact_eof=True,lossless_roundtrip=True,
            nontext_signature_sha256=digest(json.dumps(numeric,separators=(',',':')).encode()),
            offline_resize_trials=trials)
    report['totals']={key:sum(f[key] for f in report['files'].values()) for key in ['bytes','records','text_fields','nonempty_text_fields']}
    report['totals']['sections']=sum(len(f['sections']) for f in report['files'].values())
    report['db_lossless_roundtrip']=True
    report['strict_cp932_inspection_pass']=all(not f['cp932_decode_errors'] for f in report['files'].values())
    report['db_translation_runtime_verified']=False
    report['production_translation_ready']=False
    report['limitations']=['Numeric field meanings and cross-table reference semantics remain partly unknown.',
        'CP932 inspection text is not proof of the original font glyph semantics.',
        'Text limits are conservative native-memory bounds; UI width and Hangul mapping require separate checks.',
        'Resize trials are offline ASCII fixtures only; no STATUS repack, ISO injection, or game runtime validation.']
    write_json(ROOT/'reports/status_db_audit.json',report)
    if not report['strict_cp932_inspection_pass']:raise ValueError('Strict text inspection failed; see report')
    print(json.dumps(dict(totals=report['totals'],roundtrip=True,strict_cp932=True,offline_variants=9),ensure_ascii=False,indent=2))
    return report


if __name__=='__main__':audit()
