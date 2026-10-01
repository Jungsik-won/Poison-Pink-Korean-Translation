#!/usr/bin/env python3
"""Export untranslated NUL-delimited strings from original ELF data sections.

These are candidates, not proof of UI use or safe replacement capacity.
"""
import csv,json,struct
from pathlib import Path
from localization_pipeline import ROOT,file_hash,write_json
from iso_archive_stage import SOURCE,source_sha
from extract_all import literal


def export(out):
    path=SOURCE/'SLPS_258.54';raw=path.read_bytes();digest=file_hash(path)
    if digest!=source_sha(path) or raw[:7]!=b'\x7fELF\x01\x01\x01':raise ValueError('Original ELF mismatch')
    shoff=struct.unpack_from('<I',raw,32)[0];shsize,count,names_index=struct.unpack_from('<HHH',raw,46)
    if shsize!=40 or shoff+count*shsize>len(raw):raise ValueError('Unsupported sections')
    sections=[struct.unpack_from('<10I',raw,shoff+i*40) for i in range(count)]
    names=sections[names_index];strings=raw[names[4]:names[4]+names[5]];rows=[];bounds=[]
    for s in sections:
        end=strings.find(b'\0',s[0]);name=strings[s[0]:end].decode('ascii')
        if name not in ('.rodata','.sdata','.data'):continue
        start,size=s[4:6]
        if start+size>len(raw):raise ValueError('Section outside ELF')
        bounds.append(dict(name=name,offset=start,bytes=size,virtual_address=s[3]));pos=start
        while pos<start+size:
            end=raw.find(b'\0',pos,start+size)
            if end<0:break
            value=raw[pos:end]
            if value:
                try:text=value.decode('cp932')
                except UnicodeDecodeError:text=None
                if text and all(ord(c)>=32 or c in '\n\r\t' for c in text):
                    row=literal(value,id=f'ELF:0x{pos:08x}',kind='elf_string_candidate',confidence='nul_range_in_data_section_unreviewed',path='SLPS_258.54',member_sha256=digest,section=name,payload_offset=pos,virtual_address=s[3]+pos-start)
                    rows.append(row)
            pos=end+1
    folder=out/'text';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'elf_strings.jsonl').open('w',encoding='utf-8') as fp:
        for row in rows:fp.write(json.dumps(row,ensure_ascii=False)+'\n')
    with (folder/'elf_strings.tsv').open('w',encoding='utf-8',newline='') as fp:
        w=csv.writer(fp,delimiter='\t');w.writerow(['id','section','offset','virtual_address','source','target','status'])
        for row in rows:w.writerow([row['id'],row['section'],row['payload_offset'],row['virtual_address'],row['source'],'','untranslated'])
    report=dict(source_sha256=digest,sections=bounds,strings=len(rows),japanese_candidates=sum(r['japanese_candidate'] for r in rows),translation_performed=False,confidence='candidate strings; pointers/UI use and capacities require later analysis')
    write_json(out/'elf_text.json',report);print('ELF strings:',len(rows),flush=True);return report


if __name__=='__main__':export(ROOT/'extracted/original')
