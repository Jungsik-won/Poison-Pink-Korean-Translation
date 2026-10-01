"""Export comparison and explicit uncertainty notes alongside movie subtitles."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'extracted_movies/korean_reviewed_v1'
B = ROOT / 'build/movie_subtitles_v1'
cues = json.loads((OUT / 'cues.json').read_text())
with (OUT / '원문_번역_대조.tsv').open('w') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['movie', 'cue', 'start', 'end', 'source', 'translation'])
    for tag, cc in cues.items():
        for i, c in enumerate(cc, 1):
            w.writerow([tag, i, c['start'], c['end'], c['source'], c['text'].replace('\n', ' / ')])

inventory = json.loads((B / 'original_inventory.json').read_text())
for r in inventory:
    tag = r['tag']
    r['subtitle_cues'] = len(cues.get(tag, []))
    r['subtitle_type'] = 'song' if tag in ['s10', 's11', 's12', 's13', 's14'] else ('dialogue' if tag in cues else 'none')
    r['translation_status'] = 'reviewed_with_listed_uncertainties' if tag in cues else 'no_dialogue_detected'
(OUT / '영상별_목록.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')

notes = [
    dict(tags=['s09'], start=44.05, end=49.2, source='道 앞 주문 수식어 미확정', action='확실한 부분인 길을 열어라만 번역'),
    dict(tags=['s14'], start=43.2, end=54.5, source='忘れぬこの痛みに 뒤 노랫말을 두 모델이 見られたの로 인식하나 의미 불확실', action='잊히지 않는 이 아픔까지만 적용; 후속 술어 생략'),
    dict(tags=['s10', 's11', 's12', 's13'], start=44.45, end=55.8, source='s14와 동일한 1절 가사', action='동일하게 불확실 술어 생략'),
    dict(tags=['s14'], start=172.1, end=178.0, source='반복 구절을 繰り返し 呼んで로 채택; 呼ぶて 등 모델 간 차이', action='되풀이해 부르며로 잠정 적용; 추가 청취 대상'),
    dict(tags=['s10', 's11', 's12', 's13', 's14'], source='さえ切って 표기를 遮って로 문맥 보정', action='가로막고로 번역; 공식 가사집 확인은 하지 않음'),
    dict(tags=['s14'], start=260, end=273, source='작은 모델 전곡 처리에서만 추가 가사 인식, 구간별 두 모델은 음악으로 분류', action='마지막 간주에 자동 인식 허위 가사를 넣지 않음'),
]
(OUT / '청취_확인필요.json').write_text(json.dumps(notes, ensure_ascii=False, indent=2) + '\n')
print('Exported', len(cues), 'tracks and', len(notes), 'uncertainty records')
