"""Review full class-name table and 22 descriptions; stage over pending text fixes."""
import sys,json,struct,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'build/python_psd'),str(ROOT/'tools')]
from korean_sentence_probe import encode_korean,decode_korean
from localization_pipeline import sha,hed_tree
from iso_archive_stage import iso_inventory,exact
import status_db_codec as db
B=ROOT/'build/class_change_review_v1';OUT=ROOT/'outputs/class_change_review_v1'
assert not B.exists() and not OUT.exists()
w=json.loads((ROOT/'localization/class_change_review_v1/wording.json').read_text());report=json.loads((ROOT/'reports/system_messages_v1.json').read_text());mapping=report['mapping'];literals={r['offset']:r for r in report['literals']}
base=ROOT/'build/user_ui_test_v6/Poison Pink (Japan) - Korean user UI test v6.iso';es={e['path']:e for e in iso_inventory(base)['files']}
with base.open('rb') as f:
 def read(n):
  e=es[n];f.seek(e['lba']*2048);return exact(f,e['size'])
 elfbase=read('SLPS_258.54');hed=read('DATA/STATUS.HED');dat=read('DATA/STATUS.DAT');sysh=read('DATA/SYSTEM.HED');sysd=read('DATA/SYSTEM.DAT')
kt=next(e for e in hed_tree(sysh)[0] if e['path']=='system/kantable.dat');table=struct.unpack('<7560h',sysd[kt['offset']:kt['offset']+kt['size']])
def enc(t):
 b=encode_korean(t,mapping);assert decode_korean(b,mapping)==t
 for c in t:
  if c in mapping:assert table[mapping[c]['table_index']]==mapping[c]['glyph_id']
 return b
prior=(ROOT/'build/remaining_messages_v1/SLPS_258.54').read_bytes();elf=bytearray(prior);occupied=set();changes=[]
for h,t in w['descriptions'].items():
 p=int(h,16);r=literals[p];cap=r['capacity'];old=prior[p:prior.index(0,p)];before=decode_korean(old,mapping);assert before==r['target'];new=enc(t);assert len(new)<=cap and len(t)<=10
 assert not any(prior[p+len(old):p+cap+1]);elf[p:p+cap+1]=new+bytes(cap+1-len(new));occupied.update(range(p,p+cap+1))
 changes.append(dict(offset=p,source=r['source'],before=before,target=t,capacity=cap,cells=len(t)))
assert all(i in occupied for i,(a,b) in enumerate(zip(prior,elf)) if a!=b)
assert elf[0x3ddbb0:0x3ddcb8]==prior[0x3ddbb0:0x3ddcb8]
original=(ROOT/'Poison Pink (Japan)/SLPS_258.54').read_bytes();combinations=[]
for i,p in enumerate(range(0x3ddbb0,0x3ddcb4,12)):
 ptrs=struct.unpack_from('<3I',elf,p);lines=[];sources=[]
 for v in ptrs:
  if not v:lines.append('');sources.append('');continue
  q=v-0xff000;lines.append(decode_korean(bytes(elf[q:elf.index(0,q)]),mapping));sources.append(original[q:original.index(0,q)].decode('cp932'))
 combinations.append(dict(index=i,source=sources,translation=lines));assert all(len(t)<=10 for t in lines)
member=next(e for e in hed_tree(hed)[0] if e['path']=='status/PPPARAM.dat');raw=dat[member['offset']:member['offset']+member['size']];model=db.parse(raw,'PPPARAM');origmodel=db.parse((ROOT/'extracted/original/raw/STATUS/status/PPPARAM.dat').read_bytes(),'PPPARAM');origfields=dict(db.text_fields(origmodel));replacements={};names=[]
for k,v in db.text_fields(model):
 if k[0]!=4 or not v['value']:continue
 before=decode_korean(v['value'],mapping);t=w['names'].get(before,before);new=enc(t);assert len(new)<19
 if before!=t:replacements[k]=(v['value'],new)
 names.append(dict(key=list(k),source=origfields[k]['value'].decode('cp932'),before=before,target=t,changed=before!=t))
newraw=db.replace_text(raw,'PPPARAM',replacements,sha(raw));assert len(newraw)<=len(raw)
newfields=dict(db.text_fields(db.parse(newraw,'PPPARAM')))
for k,v in db.text_fields(model):assert newfields[k]['value']==replacements.get(k,(None,v['value']))[1]
newdat=bytearray(dat);pos=member['offset'];newdat[pos:pos+len(raw)]=newraw+bytes(len(raw)-len(newraw));newhed=bytearray(hed);struct.pack_into('<I',newhed,member['index']*44+4,len(newraw))
assert newdat[:pos]==dat[:pos] and newdat[pos+len(raw):]==dat[pos+len(raw):]
assert hed_tree(newhed)[0]==[dict(e,size=len(newraw)) if e['path']==member['path'] else e for e in hed_tree(hed)[0]]
B.mkdir();OUT.mkdir();pending=[]
for path,payload,old in [('SLPS_258.54',bytes(elf),elfbase),('DATA/STATUS.HED',bytes(newhed),hed),('DATA/STATUS.DAT',bytes(newdat),dat)]:
 dest=B/path;dest.parent.mkdir(exist_ok=True);dest.write_bytes(payload);assert len(payload)==len(old);pending.append(dict(path=path,replacement=str(dest.relative_to(ROOT)),sha256=sha(payload),expected_sha256=sha(old)))
r=dict(status='prepared_not_applied_to_iso',iso_built=False,runtime_verified=False,base_iso=str(base.relative_to(ROOT)),base_iso_sha256='3086890c313ffcbf1303671e3e0f11a1dded4194c0ad742cb54a59e61b5b3771',includes_pending_shop_and_controller_messages=True,supersedes_pending_reports=['reports/shop_messages_v1.json','reports/remaining_messages_v1.json'],descriptions=changes,combinations=combinations,names=names,pending_files=pending,checks=dict(description_cell_limit=10,all_22_combinations_checked=True,existing_font_mapping_verified=True,description_pointer_table_preserved=True,db_nontext_and_other_text_preserved=True,archive_other_members_preserved=True))
for p in [B/'report.json',ROOT/'reports/class_change_review_v1.json']:p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
with (OUT/'클래스명_검수.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.writer(f);writer.writerow(['위치','원문','기존','수정']);writer.writerows((str(n['key']),n['source'],n['before'],n['target']) for n in names)
with (OUT/'설명_22종_검수.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.writer(f);writer.writerow(['번호','원문','수정']);writer.writerows((n['index'],'\n'.join(n['source']),'\n'.join(n['translation'])) for n in combinations)
h=ROOT/'HANDOVER.md';s=h.read_text();note='## 적용 대기: 클래스 체인지 전체 문구 검수 (2026-09-30)\n\n다음 ISO에는 `reports/class_change_review_v1.json` pending_files 3개 사용. 상점/추가 안내문 대기 작업 포함하며 기존 두 pending 보고서를 대체함. 클래스명 전체 및 설명 22종 대조. 설명 한 줄 최대 10문자(공백 포함), 포인터·비문자 데이터 보존. ISO 미생성, 실제 게임 배치 미검증. `outputs/class_change_review_v1` 검수 CSV 참조.\n\n';h.write_text(s.replace('\n\n','\n\n'+note,1))
print(json.dumps(dict(names_reviewed=len(names),names_changed=len(replacements),description_literals=len(changes),combinations=len(combinations)),ensure_ascii=False))
