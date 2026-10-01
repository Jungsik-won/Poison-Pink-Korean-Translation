#!/usr/bin/env python3
"""Whole-corpus triage plus explicitly scoped human-readable semantic corrections.
Flags are leads, not proof of errors. Does not mutate a build input or ISO.
"""
import csv, hashlib, json, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from status_db_codec import SCHEMAS
from korean_sentence_probe import encode_korean, decode_korean
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/translation_review_20260920'
CONFIG=ROOT/'localization/review_20260920'
INPUT=ROOT/'localization/imports/20260917_corrected'

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def emit(p,rows):
    with p.open('w') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
def tsv(p,rows,fields):
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t');w.writeheader();w.writerows(rows)
def size(t):return sum(1 if ord(c)<128 else 2 for c in t)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    build=read(ROOT/'reports/user_translations_applied_20260917.json')
    excluded={r['id'] for r in build['late_exclusions']}
    records=[]
    system=read(ROOT/'reports/system_messages_v1.json')
    later_offsets={r['offset'] for r in system['literals']}
    superseded=[]
    for line in (INPUT/'plan.jsonl').open():
        r=json.loads(line)
        if r['id'] in excluded:continue
        if r['id'].startswith('ELF:') and int(r['id'].split(':')[1],16) in later_offsets:
            superseded.append(r['id']);continue
        m=r['metadata'];records.append(dict(id=r['id'],source=r['source'],target=r['target'],
            kind=m.get('kind','elf'),path=m.get('path','SLPS_258.54'),function=m.get('function',''),
            catalog=r['catalog']))
    for r in system['literals']:
        records.append(dict(id='system:0x%08x'%r['offset'],source=r['source'],target=r['target'],
                            kind='elf_system',path='SLPS_258.54',function='',catalog='system'))
    byid={r['id']:r for r in records};assert len(byid)==len(records)
    grouped=defaultdict(list);scenes=defaultdict(list)
    for r in records:
        grouped[(r['source'],r['target'],r['kind'])].append(r)
        scenes[(r['path'],r['function'])].append(r)
    positions={r['id']:(rows,i) for rows in scenes.values() for i,r in enumerate(rows)}
    corrections={}
    for line in (CONFIG/'dialogue_fixes.txt').read_text().splitlines():
        ident,target,reason=line.split('|');target=target.replace('\\n','\n');r=byid[ident]
        # Only propagate identical originals/targets in the SAME function/file.
        for other in scenes[(r['path'],r['function'])]:
            if (other['source'],other['target'])==(r['source'],r['target']):
                corrections[other['id']]=(target,reason,'dialogue_context')
    terms=dict(line.split('|') for line in (CONFIG/'term_fixes.txt').read_text().splitlines())
    for r in records:
        s,t=r['source'],r['target']
        if r['kind']=='db_field' and ':name' in r['id'] and s in terms and terms[s]!=t:
            corrections[r['id']]=(terms[s],'장비/스킬/마신 이름의 의미 오역 또는 같은 계열 표기 불일치','db_name')
        if r['kind']=='db_field' and ':description' in r['id'] and '単体' in s:
            revised=t.replace('단체','단일').replace('단위','단일').replace('단독','단일')
            if revised!=t:corrections[r['id']]=(revised,'単体는 한 대상. 단체/단위로 오역된 대상 범위 수정','skill_target')
    manual=[]
    for ident,(target,reason,category) in corrections.items():
        r=byid[ident];assert target!=r['target']
        rows,i=positions[ident]
        context=[dict(id=x['id'],source=x['source'],target=x['target']) for x in rows[max(0,i-2):i+3]]
        capacity=255
        if r['kind']=='db_field':
            path,section,record,field=ident.split(':')
            capacity=next(x[2]-1 for x in SCHEMAS[Path(path).stem][int(section)] if x[0]==field)
        encoding_error=None
        try:
            payload=encode_korean(target,system['mapping'])
            assert decode_korean(payload,system['mapping'])==target
        except (ValueError, KeyError, UnicodeError) as error:
            encoding_error=str(error)
        manual.append(dict(**r,proposed_target=target,reason=reason,category=category,
             review_status='semantic_correction_proposed',iso_applied=False,context=context,
             context_note='同一関数の文字列順。分岐後の実行順や話者を自動確定したものではない。',
             encoded_bytes=size(target),capacity_bytes=capacity,capacity_ok=size(target)<=capacity,
             existing_font_encoding_ok=encoding_error is None,encoding_issue=encoding_error))
    suspects=[];unique=[];flagcounts=Counter();scenecount=Counter()
    for num,((s,t,kind),rows) in enumerate(grouped.items(),1):
        reasons=[];sn=unicodedata.normalize('NFKC',s);tn=unicodedata.normalize('NFKC',t)
        if re.findall(r'\d+',sn)!=re.findall(r'\d+',tn):reasons.append('numeric_sequence_diff_requires_context')
        if re.search('[ぁ-ヺ]',t):reasons.append('japanese_remains')
        if re.search('모순|전망치|사슬 똥|가슴맞춤|여드름|작은 스님|간에 명중|좋은 정도 가슴|느끼고 기압|너무 먹지 마라',t):reasons.append('confirmed_error_pattern_family')
        for jp,bad in [('テージ',r'(?<![가-힣])(?:테지|티지)(?![가-힣])'),('ベセク','베섹'),('シェイプシフター','모양 쉬프터'),('ルナーシェ','루너셰'),('ロンデミオン','론 데미온')]:
            if jp in s and re.search(bad,t):reasons.append('proper_name_variant');break
        if '単体' in s and re.search('단체|단위',t):reasons.append('single_target_mistranslation')
        if re.search('小僧|命が|僕として|肝に銘|身を引|気圧され|手に余|度胸|付き合|わなな|成敗|聞かれ|に刃向|とって喰',s):reasons.append('polysemy_or_idiom_context_review')
        if re.search('じゃない|わけではない|かまうもんか|ないはず|ないわけ',s):reasons.append('negation_or_rhetorical_context_review')
        if re.search('ください|なさい|してやろう|してくれる|して貰おう',s) and re.search('수 있습니다|말할까요|받자|들려주세요',t):reasons.append('speaker_direction_review')
        if size(t)>255 and kind=='rtb_literal':reasons.append('rtb_capacity')
        reviewed=[r['id'] for r in rows if r['id'] in corrections]
        entry=dict(unit=num,source=s,target=t,kind=kind,occurrences=len(rows),ids=[r['id'] for r in rows],
             reasons=sorted(set(reasons)),correction_ids=reviewed,
             semantic_status='partially_corrected_contexts' if reviewed else 'not_line_by_line_reviewed')
        unique.append(entry)
        if reasons:
            suspects.append(entry);flagcounts.update(entry['reasons'])
            for r in rows:scenecount[r['path']]+=1
    emit(OUT/'corpus.jsonl',records);emit(OUT/'unique_review_units.jsonl',unique)
    emit(OUT/'suspects.jsonl',suspects);emit(OUT/'corrections.jsonl',manual)
    fields=['id','path','function','source','target','proposed_target','reason','category','encoded_bytes','review_status']
    tsv(OUT/'확정오역_수정제안.tsv',[{k:r[k] for k in fields} for r in manual],fields)
    with (INPUT/'structured_ko_corrected.tsv').open(newline='') as f:
        reader=csv.DictReader(f,delimiter='\t');cols=reader.fieldnames;originals=list(reader)
    changed=0; revised=[]
    for r in originals:
        new=dict(r)
        if r['id'] in corrections:
            assert r['source']==byid[r['id']]['source'] and r['target']==byid[r['id']]['target']
            new['target']=corrections[r['id']][0];new['status']='semantic_reviewed_pending_build';changed+=1
        revised.append(new)
    assert changed==len(corrections)
    tsv(OUT/'structured_ko_reviewed_draft.tsv',revised,cols)
    with (OUT/'structured_ko_reviewed_draft.tsv').open(encoding='utf-8-sig',newline='') as f:roundtrip=list(csv.DictReader(f,delimiter='\t'))
    assert roundtrip==revised
    assert all(all(a[k]==b[k] for k in cols if k not in ['target','status']) for a,b in zip(originals,revised))
    summary=dict(records=len(records),kinds=dict(Counter(r['kind'] for r in records)),unique_units=len(unique),
        flagged_units=len(suspects),flags=dict(flagcounts),correction_occurrences=len(manual),
        correction_unique_pairs=len(set((r['source'],r['target'],r['proposed_target']) for r in manual)),
        correction_categories=dict(Counter(r['category'] for r in manual)),
        priority_files=scenecount.most_common(30),full_automated_scan=True,full_manual_semantic_review=False,
        iso_modified=False,original_build_inputs_modified=False,protected_columns_preserved=True,
        superseded_elf_rows_excluded=superseded,
        correction_capacity_failures=[r['id'] for r in manual if not r['capacity_ok']],
        correction_encoding_failures=[dict(id=r['id'],error=r['encoding_issue']) for r in manual if not r['existing_font_encoding_ok']],
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [INPUT/'plan.jsonl',INPUT/'structured_ko_corrected.tsv',ROOT/'reports/system_messages_v1.json']},
        scope_note='All applied plan rows except recorded exclusions, plus 540 later ELF system literals. Same-source duplicates retain separate locations. New image lettering is not OCR-audited. Flags are NOT confirmed errors. Draft corrections require encoding/font/buffer and runtime checks before ISO import.')
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
