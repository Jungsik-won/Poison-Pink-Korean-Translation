import csv,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'outputs/translation_review_20260920/applied_v3';out.mkdir(exist_ok=True)
changes=list(map(json.loads,(root/'localization/semantic_revision_v3/changes.jsonl').open()));lookup={r['id']:r for r in changes}
with (out/'수정내역.tsv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['id','source','before','target','reason'],delimiter='\t');w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in changes)
src=root/'localization/imports/20260917_corrected/structured_ko_corrected.tsv'
with src.open(newline='') as f:
 reader=csv.DictReader(f,delimiter='\t');fields=reader.fieldnames;rows=list(reader)
found=set()
for r in rows:
 if r['id'] not in lookup:continue
 x=lookup[r['id']];assert r['source']==x['source'] and r['target']==x['before'];r['target']=x['target'];r['status']='reviewed_semantic_v3';found.add(r['id'])
assert found==set(lookup)
with (out/'structured_ko_reviewed_v3.tsv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields,delimiter='\t');w.writeheader();w.writerows(rows)
with src.open(newline='') as f,(out/'structured_ko_reviewed_v3.tsv').open(newline='') as g:
 a=list(csv.DictReader(f,delimiter='\t'));b=list(csv.DictReader(g,delimiter='\t'));assert len(a)==len(b)
 for x,y in zip(a,b):
  assert all(x[k]==y[k] for k in fields if k not in ['target','status'])
  if x['id'] not in lookup:assert x==y
pre=json.load((root/'localization/semantic_revision_v3/preflight.json').open())
corpus=list(map(json.loads,(root/'outputs/translation_review_20260920/corpus.jsonl').open()))
with (out/'테이지_장면별_검수대본.tsv').open('w',newline='') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['id','function','source','target','changed'])
 for r in sorted(corpus,key=lambda r:(r['path'],int(r['id'].split(':')[-1],16) if r['kind']=='rtb_literal' else 0)):
  if Path(r['path']).name not in pre['reviewed_scene_files'] or r['function'] in ['<module>','_staffroll']:continue
  w.writerow([r['id'],r['function'],r['source'],lookup.get(r['id'],{}).get('target',r['target']),r['id'] in lookup])
(out/'summary.json').write_text(json.dumps(dict(pre,tsv_rows=len(rows),source_columns_preserved=True,unchanged_rows_preserved=True,unique_corrections=len(set((r['source'],r['target'],r['kind']) for r in changes))),ensure_ascii=False,indent=2)+'\n')
(out/'검수결과.md').write_text('''# 번역 의미 검수 반영 — 2026-09-20

## 반영 범위

- 총 1,126개 저장 위치: 대사 930곳, DB 이름 139곳, 스킬 설명 57곳. 중복 분기를 제외한 원문·수정문·종류 조합은 903종.
- 테이지 주요 이벤트 ft_01~ft_16 및 ft_99의 원문/번역문을 장면 순서로 대조. 동일 문장이 다른 함수에 반복된 분기도 명시적 ID로 보완.
- 이전 검수 초안의 다른 루트 개별 확정 오역과 DB 수정도 포함. 다른 루트 전체를 검수했다는 뜻이 아님.
- 행위 주체·부정·이동 방향, 僕의 종/나 구분, 命의 명령/생명 구분, 관용구, 인물 말투, 이름 표기를 수정.
- 단일 대상 스킬을 단체 대상으로 오해하게 만들던 설명과 장비 이름 오역 수정.
- 教皇の聖杖는 이름칸 18바이트 안에 들어가는 ‘교황의 성스런 봉’으로 반영.

## 파일

- `수정내역.tsv`: ID, 원문, 이전 번역, 수정 번역, 수정 이유.
- `structured_ko_reviewed_v3.tsv`: 기존 128,274행의 원문/위치/ID를 유지한 통합 번역본. target과 해당 행의 status만 수정. 앞으로의 편집은 이 파일을 기준으로 삼되 재빌드는 현재 ISO에 기계적으로 재수입하지 말고 빌드 기준 해시를 확인할 것.
- `테이지_장면별_검수대본.tsv`: 검수 대상 이벤트 원문과 최종 번역을 위치 순서로 나열. 화자 이름 행도 보존. function은 엔진 함수명이며 확정 화자명이 아님.
- 적용 입력: `localization/semantic_revision_v3/changes.jsonl`.

## 정적 검증

기존 문자표로 모든 수정문 인코딩/디코딩 왕복. 수정 대사 한 줄은 36바이트 이내(화면 실측이 아닌 폭 예산). RTB 255바이트 및 DB별 용량 상한 준수. 문자열 외 명령/분기/게임 수치 보존. 변경하지 않은 문장도 바이트 대조. 전체 ISO에서 계획한 범위 밖 바이트가 같은지 확인하고 36개 변경 멤버를 재읽기 검증.
대사 파서 6개, DB 파서 9개, PCSX2 호환 검사 12개 통과. 기존 이미지/폰트/ELF 보존. 이번 수정 대사의 실제 플레이/음성 대조는 미실시.

## 아직 남은 범위

게임 전체 수동 문맥 검수는 미완료다. 다른 인물 주요 루트, 마을/전투/개별 엔딩 대사, 전체 DB 설명·고유명사와 이미지 표기 대조가 남아 있다. 전수 자동검사에서 검토 후보가 된 1,005건을 확정 오역으로 간주하지 않는다. 검수한 테이지 파일도 음성 억양과 화면 폭에 따른 추가 조정이 가능하다.
포획 이미지의 이름과 텍스트 DB 사이 표기 차이도 별도 대조 대상이다.

## 방언 확인 기록

쿠쿠족 ft_06의 `オウトル`는 앞선 루나셰 확인 질문에 대한 응답으로 보고 ‘맞구먼’으로 해석했다. 지역어의 ‘합치다/맞다’ 용례와 장면 문맥에 따른 추론이다. ‘찾고 있다’라는 초안은 폐기했다. 참고: [아마쿠사 방언집](https://hougen.amakusa-web.jp/MyHp/Pub/Free.aspx?CNo=6), [지역어 어휘 기록](https://note.com/ryo11510/n/n2162bd2b2425). 게임 공식 번역 근거는 아니며 음성·현지어 추가 검증 가능.
''')
print('Delivery TSVs verified',len(changes))
