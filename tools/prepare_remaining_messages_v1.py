"""Stage fixed-span shop quantity messages over UI test v6, without building an ISO."""
import sys,json,csv,re,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'build/python_psd'),str(ROOT/'tools')]
from korean_sentence_probe import encode_korean,decode_korean
from iso_archive_stage import iso_inventory,exact
from localization_pipeline import sha,hed_tree
BASE=ROOT/'build/user_ui_test_v6/Poison Pink (Japan) - Korean user UI test v6.iso'
B=ROOT/'build/remaining_messages_v1';OUT=ROOT/'outputs/remaining_messages_v1'
assert not B.exists() and not OUT.exists()
mapping=json.loads((ROOT/'reports/system_messages_v1.json').read_text())['mapping']
files={e['path']:e for e in iso_inventory(BASE)['files']}
with BASE.open('rb') as fp:
 def read(path):
  e=files[path];fp.seek(e['lba']*2048);return exact(fp,e['size'])
 elf=read('SLPS_258.54');hed=read('DATA/SYSTEM.HED');dat=read('DATA/SYSTEM.DAT')
original=(ROOT/'Poison Pink (Japan)/SLPS_258.54').read_bytes()
member=next(e for e in hed_tree(hed)[0] if e['path']=='system/kantable.dat')
table=struct.unpack('<7560h',dat[member['offset']:member['offset']+member['size']])
prior=(ROOT/'build/shop_messages_v1/SLPS_258.54').read_bytes();changed=bytearray(prior);allowed=set();rows=[]
overrides={0x3dcba8:'아날로그 컨트롤러(DUALSHOCK 2)가 연결되지 않았습니다.',0x3dcbe0:'컨트롤러 단자 1에 아날로그 컨트롤러(DUALSHOCK 2)를',0x3dcc18:'올바르게 다시 연결해 주세요.',0x435638:'%s   회차'}
with (ROOT/'localization/imports/20260917_corrected/elf_ko_corrected.tsv').open() as f:
 for r in csv.DictReader(f,delimiter='\t'):
  p=int(r['offset'])
  if p not in overrides:continue
  s=r['source'];t=overrides[p];old=s.encode('cp932');new=encode_korean(t,mapping)
  assert original[p:p+len(old)+1]==elf[p:p+len(old)+1]==old+b'\0'
  assert len(new)<=len(old) and decode_korean(new,mapping)==t
  assert re.findall(r'@[a-z]',s)==re.findall(r'@[a-z]',t) and s.count('\n')==t.count('\n')
  for c in t:
   if c in mapping:
    e=mapping[c];assert table[e['table_index']]==e['glyph_id']
  payload=new+b' '*(len(old)-len(new))+b'\0'
  changed[p:p+len(payload)]=payload;allowed.update(range(p,p+len(old)))
  assert decode_korean(bytes(changed[p:p+len(old)]),mapping).rstrip()==t
  rows.append(dict(offset=p,source=s,target=t,capacity=len(old),encoded_bytes=len(new),original_nul_offset=p+len(old)))
assert len(rows)==4 and len(changed)==len(elf)
assert all(i in allowed for i,(a,b) in enumerate(zip(prior,changed)) if a!=b)
shoff=struct.unpack_from('<I',elf,32)[0];count=struct.unpack_from('<H',elf,48)[0]
for i in range(count):
 section=struct.unpack_from('<10I',elf,shoff+i*40)
 if section[2]&4:assert changed[section[4]:section[4]+section[5]]==elf[section[4]:section[4]+section[5]]
B.mkdir();OUT.mkdir();dest=B/'SLPS_258.54';dest.write_bytes(changed)
r=dict(includes_pending_shop_messages=True,supersedes_pending_report='reports/shop_messages_v1.json',status='prepared_not_applied_to_iso',date='2026-09-30',base_iso=str(BASE.relative_to(ROOT)),base_iso_sha256='3086890c313ffcbf1303671e3e0f11a1dded4194c0ad742cb54a59e61b5b3771',iso_built=False,runtime_verified=False,rows=rows,checks=dict(original_nul_positions_preserved=True,control_tokens_preserved=True,existing_font_mapping_verified=True,executable_sections_unchanged=True,outside_literal_spans_identical=True),changed_bytes=sum(a!=b for a,b in zip(elf,changed)),pending_files=[dict(path='SLPS_258.54',replacement=str(dest.relative_to(ROOT)),expected_sha256=sha(elf),sha256=sha(changed))])
for p in [B/'report.json',ROOT/'reports/remaining_messages_v1.json']:p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
with (OUT/'추가_안내문_번역.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['offset','원문','번역']);w.writerows((hex(x['offset']),x['source'],x['target']) for x in rows)
h=ROOT/'HANDOVER.md';text=h.read_text();note='## 적용 대기: 추가 안내문 통합 (2026-09-30)\n\n`reports/remaining_messages_v1.json` pending_files를 다음 ISO에 사용. 기존 shop_messages_v1의 10문구 포함 + 컨트롤러 연결 3줄·회차 1개 추가. shop_messages_v1을 뒤에 덮어쓰지 말 것. 원래 문자열 종료 위치와 제어문자, 실행 코드 및 기존 한글 폰트 확인. ISO 미생성, 실행 미검증. 번역 목록 128,274행에 의미 검수 v1~v4를 합쳐 검사했고 일본어 단어 잔존/빈 번역 후보 0개. 이미지·실행 경로 전체 번역 완료를 의미하지 않음.\n\n';h.write_text(text.replace('\n\n','\n\n'+note,1))
shop_path=ROOT/'reports/shop_messages_v1.json';shop=json.loads(shop_path.read_text());shop['superseded_for_next_integration_by']='reports/remaining_messages_v1.json';shop_path.write_text(json.dumps(shop,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'new_messages':len(rows),'includes_shop_messages':True,'checks':r['checks']},ensure_ascii=False))
