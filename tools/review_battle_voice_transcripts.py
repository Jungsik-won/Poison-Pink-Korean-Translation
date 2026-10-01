#!/usr/bin/env python3
"""Review recognized short battle phrases; keep uncertain audio out of subtitles.

This is text review of local ASR evidence, not a claim of human audio listening.
"""
import json
import re
import unicodedata
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/battle_voice_subtitles_v1'


def normalize(text):
    text=unicodedata.normalize('NFKC',text)
    text=''.join(chr(ord(c)-96) if 'ァ'<=c<='ヶ' else c for c in text)
    return re.sub(r'[\s!！?？。、,\.…ー〜～"「」]+','',text).lower()


def main():
    path=ROOT/'localization/battle_voice_subtitles_v1.json'
    data=json.loads(path.read_text());phrases=json.loads((ROOT/'localization/battle_voice_phrases.json').read_text())
    phrases['ひれ伏せ']='엎드려라!'
    phrases.update({'行きなさい':'가거라!','命令よ':'명령이야!','決めるか':'끝내 볼까!','もうよい':'이제 됐다.',
        'もういいわ':'이제 됐어.','女神よ':'여신이여!', '終わりよ':'끝이야!', '邪魔だ':'방해된다!',
        '頼んだよ':'부탁한다.', '頼む':'부탁한다.', '許しを':'용서를!', '終わりだ':'끝이다!',
        '許しをここに':'이곳에 용서를!', '残罪の許しを':'죄를 용서하소서!',
        '仕留めろ':'해치워라!', '去れ':'물러가라!', '神の息吹を':'신의 숨결을!',
        'ごめんなさい':'미안해요.', '決めるぜ':'끝내 주마!', '決めてやるぜ':'끝내 주겠어!',
        '万物の力よ':'만물의 힘이여!', 'よっしゃ':'좋았어!', '祈りを天に':'하늘에 기도를!',
        '残念':'안됐군.', '消え失せろ':'꺼져 버려라!', '神の一鉄':'신의 일격을!',
        '受けてみよう':'받아 보아라!', '愚者に浄化を':'어리석은 자에게 정화를!',
        '愚者に救いを':'어리석은 자에게 구원을!', 'この一撃で':'이 일격으로!',
        '汚れし御霊よ':'더럽혀진 영혼이여!', '断罪よ':'단죄하라!', '神の鉄よ':'신의 철퇴여!',
        '死に':'죽어라!', 'おわりだ':'끝이다!', '覚悟':'각오해라!', 'いざ':'자, 간다!',
        '行く':'간다!', '消えちゃえ':'사라져 버려!', '駆逐せよ':'몰아내라!',
        '地獄へ落ちろ':'지옥에 떨어져라!', '破魔の力よ':'마를 물리치는 힘이여!',
        '魔を滅せよ':'마를 멸하라!', '魔を駆逐せよ':'마를 몰아내라!',
        '滅せよ':'멸하라!', '消え去る':'사라져라!', '愚か者が':'어리석은 놈이!',
        '私も':'나도!', '僕も':'나도!', '失せろ':'꺼져라!', '消し飛べ':'날아가 버려!',
        'どっか行って':'저리 가!', '終われ':'끝나라!', '慈悲だ':'자비다!',
        '続くぞ':'계속 간다!', '破魔の恩恵を':'마를 물리치는 은혜를!',
        '加護よ':'가호여!', '加護':'가호를!', '恩恵よ':'은혜여!', '終わりだよ':'끝이야!',
        '当てろ':'맞혀라!', 'まだ':'아직이다!', '行きます':'갑니다!',
        'それ':'받아라!', 'クズが':'쓰레기 같은 놈!', '死にな':'죽어라!',
        'へへんだ':'흥, 어때!', 'ぶっ潰し':'박살 내 주마!', '覚悟せんね':'각오하라고!',
        '決めるん':'끝내 주겠어!', '終わり':'끝이다!'})
    # These readings could change the meaning of a healing/holy spell. Retain
    # the raw evidence for audio review instead of publishing an inferred phrase.
    for uncertain in ['許しをここに','残罪の許しを','神の一鉄']:
        phrases.pop(uncertain,None)
    lookup={normalize(k):(k,v) for k,v in phrases.items()}
    aliases={'食らえ':'くらえ','喰らえ':'くらえ','目触りよ':'目障りよ','目触りなの':'目障りなの',
        'Zodiaよ':'ゾディアよ','ホロビヨ':'滅びよ','いくzoom':'行くぞ','イキ':'行け',
        'ザコが':'雑魚が','ヒレフセ':'ひれ伏せ','滅びよう':'滅びよ',
        'シトメロ':'仕留めろ','され':'去れ','キイエロ':'消えろ','いっけー':'行け',
        '神のいぶきを':'神の息吹を','偶者に浄化を':'愚者に浄化を','偶射に浄化を':'愚者に浄化を',
        'この一ガキで':'この一撃で','汚れし見たまよ':'汚れし御霊よ','神の一徹':'神の一鉄',
        '死ねえ':'死ね','消えされ':'消え去れ','浜の力よ':'破魔の力よ',
        'ハマの力よ':'破魔の力よ','浜の恩恵を':'破魔の恩恵を',
        'メッセよ':'滅せよ','めせよ':'滅せよ','マオメッセよ':'魔を滅せよ',
        'まおめせよ':'魔を滅せよ','マオメセヨ':'魔を滅せよ',
        '真を駆逐せよ':'魔を駆逐せよ','愚者に救いよう':'愚者に救いを',
        'イケー':'行け','いけっ':'行け','カゴー':'加護','カゴよ':'加護よ','オンケーよ':'恩恵よ',
        'いきます':'行きます','まだっ':'まだ','キエロ':'消えろ','ボクも':'僕も',
        '断在よ':'断罪よ','へへーんだー':'へへんだ','シニナ':'死にな',
        '消えうせろ':'消え失せろ'}
    alias_lookup={normalize(k):normalize(v) for k,v in aliases.items()}
    # Repeated recognizer text in short clips is only collapsed for an identical
    # known word; unrelated syllables are never inferred from the bank/slot.
    for key in list(lookup):lookup[key+key]=lookup[key]
    manual={'kv3_0010_03':('終わりよ','끝이야!','asr/batch_14.json'),
            'kv3_0010_05':('消えろ','사라져라!','asr/batch_14.json'),
            'kv3_0010_07':('ゾディアよ','조디아여!','tei_spell_full.json')}
    for row in data['rows']:
        if row['status']=='non_dialogue':continue
        full=OUT/'review_asr'/(Path(row['audio']).name+'.txt')
        candidates=[row.get('asr_individual','')]
        if full.exists():
            row['asr_review_model']=full.read_text(errors='replace').strip();candidates.append(row['asr_review_model'])
        final=OUT/'full_review_asr'/(Path(row['audio']).name+'.txt')
        if final.exists():
            row['asr_padded_review']=final.read_text(errors='replace').strip();candidates.append(row['asr_padded_review'])
        matches=[]
        for candidate in candidates:
            key=normalize(candidate);key=alias_lookup.get(key,key)
            if key in lookup: matches.append(lookup[key])
        unique=set(matches)
        if row['tag'] in manual:
            row['ja'],row['ko'],row['review_evidence']=manual[row['tag']]
            row['status']='reviewed_translation'
        elif len(unique)==1:
            row['ja'],row['ko']=unique.pop();row['status']='reviewed_translation'
            row['review_evidence']='Known Japanese phrase in local ASR; Korean meaning reviewed'
        elif candidates and row.get('asr_review_model') and re.fullmatch(r'[はぁあ゛っうおやえぇたてんふへ()笑シャッパァク!?！?\s]+', row['asr_review_model']):
            row['ja']=row['ko']='';row['status']='non_dialogue'
            row['review_evidence']='Non-verbal exertion/kiai in multiple ASR passes; no semantic subtitle'
        else:
            row['ja']=row['ko']='';row['status']='needs_transcript_review'
            if len(unique)>1:row['review_evidence']='Conflicting recognizer phrases; not applied'
    data['review_method']='Japanese phrase and Korean text review from local ASR; uncertain clips withheld, no human audio audit'
    data['counts']=dict(Counter(r['status'] for r in data['rows']))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'localization/battle_voice_phrases.json').write_text(json.dumps(phrases,ensure_ascii=False,indent=2)+'\n')
    print(data['counts'])


if __name__=='__main__':main()
