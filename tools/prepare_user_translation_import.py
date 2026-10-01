#!/usr/bin/env python3
"""Prepare reviewed import records; never alter incoming TSVs or game assets."""
import csv, json, re, sys, unicodedata
from collections import Counter
from pathlib import Path
from functools import lru_cache
from localization_pipeline import ROOT, write_json, sha
from status_db_codec import SCHEMAS

OUT = ROOT/'localization/imports/20260917_corrected'
FIXED_NAMES = {
 '獣魔の錫杖':'수마의 석장', '獣魔の錫杖＋１':'수마의 석장+1',
 '蜥蜴鱗の革鎧':'도마뱀비늘 갑옷', '我流連打・矛':'가류 연타·창',
 '闇耐性上昇＋１':'암흑내성 상승+1', '闇耐性上昇＋２':'암흑내성 상승+2',
 '闇を纏う烙印者':'어둠을 두른 낙인자',
 '魚凸の槍':'어신의 창', '鳥凸の槍':'조신의 창', '鳥凸の槍＋１':'조신의 창+1',
 '狩凸の短弓':'사냥신의 단궁', '鬼凸の首飾り':'귀신의 목걸이',
 '仙凸の首飾り':'선신의 목걸이', '水凸の首飾り':'수신의 목걸이',
 '魔凸の肉':'마신의 고기', '魔凸の肝':'마신의 간', '魔凸の心臓':'마신의 심장',
 '羽化の凸光':'우화의 신광', '堕天の凸光':'타천의 신광', '天啓の凸光':'계시의 신광',
 '行動順':'행동순', 'ロード':'로드', '右上':'우상', '左上':'좌상', '体':'체',
 '刺突':'자돌', '退喚':'귀환', '全ての敵をせん滅':'적 전멸', '主人公の戦闘不能':'주인공 전투불능',
}
# Whitespace-insensitive lookup corrects repeated enemy descriptions across records.
DESC_PAIRS = [
 ('聖域を守る機工魔凸聖魔法による魔術装甲が施されている','성역을 지키는 기공 마신\n성마법으로 만든\n마술 장갑을 두르고 있다'),
 ('闇の眷属の機工魔凸闇属性魔法の耐性が高い','어둠의 권속인 기공 마신\n암속성 마법에 대한\n내성이 높다'),
 ('闇に魅入られた屍魔凸腐敗した体からは常に臭気が漂う','어둠에 홀린 시체 마신\n썩은 몸에서 언제나\n악취가 풍긴다'),
 ('錬金術で動く機工魔凸剣や斧で重い一撃を繰り出す','연금술로 움직이는 기공 마신\n검과 도끼로\n묵직한 일격을 가한다'),
 ('全身が剣でできた機工魔凸全身の剣を自在に操る','온몸이 검으로 된 기공 마신\n전신의 검을\n자유자재로 다룬다'),
 ('魔術に長けた機工魔凸様々な属性の魔法を駆使する','마술에 능한 기공 마신\n여러 속성의 마법을\n자유자재로 사용한다'),
 ('重機工魔凸強力な打撃攻撃は骨をも砕く','중기공 마신\n강력한 타격 공격으로\n뼈마저 부순다'),
 ('ヘクトギガスと同系の大型機工魔凸風属性の魔法を使う','헥토기가스 계열의\n대형 기공 마신\n풍속성 마법을 사용한다'),
 ('聖竜が闇に堕ちて魔凸と化した姿様々な災厄をもたらす','성룡이 어둠에 타락해\n마신으로 변한 모습\n온갖 재앙을 불러온다'),
 ('火の精霊魔凸容姿に似合わない強力な火属性魔法を使う','불의 정령 마신\n겉모습과 달리 강력한\n화속성 마법을 사용한다'),
 ('土の精霊魔凸宝を集めることに妄執して宝箱を荒らす','땅의 정령 마신\n보물 수집에 집착해\n보물 상자를 뒤진다'),
 ('傷ついている者に癒しを施すことで歓喜を得る精霊魔凸','다친 이를 치료하며\n기쁨을 느끼는\n정령 마신'),
 ('風と同化した精霊魔凸霊体のため物理攻撃が効きにくい','바람과 하나 된 정령 마신\n영체이므로 물리 공격이\n잘 통하지 않는다'),
 ('生前に暴虐の限りを尽くした騎士の霊から生まれた死霊魔凸','생전에 온갖 폭행을 일삼던\n기사의 영혼에서 태어난\n사령 마신'),
 ('闇・火・土属性の魔法に長けた大型魔凸','암·화·토속성 마법에\n능한 대형 마신'),
 ('死が具現化した魔凸超神に匹敵する力を持つ','죽음이 형체를 이룬 마신\n초신에 필적하는\n힘을 지녔다'),
 ('ベセクの浅い場所に生息する獣魔凸','베세크의 얕은 곳에\n서식하는 짐승 마신'),
 ('水辺を好む水棲魔凸長い舌を突き出す貫通攻撃が特長','물가를 좋아하는 수생 마신\n긴 혀를 내미는\n관통 공격이 특징이다'),
 ('水属性の魔法に長けた獣魔凸刺突攻撃に弱い','수속성 마법에 능한\n짐승 마신\n자돌 공격에 약하다'),
 ('火属性の魔法に長けた獣魔凸刺突攻撃に弱い','화속성 마법에 능한\n짐승 마신\n자돌 공격에 약하다'),
 ('弓を得意とする獣魔凸ゴートアスと組んで行動することが多い','활에 능한 짐승 마신\n고트아스와 함께\n행동하는 일이 많다'),
 ('大きな足を持つ獣魔凸常に飛び跳ねていて落ち着きがない','큰 발을 가진 짐승 마신\n늘 이리저리 뛰어다니며\n가만히 있지 못한다'),
 ('森に生息する植物魔凸眠りや麻痺を誘う蔓攻撃が特長','숲에 사는 식물 마신\n수면과 마비를 일으키는\n덩굴 공격이 특징이다'),
 ('トカゲに似た獣魔凸斬撃属性の錫杖で攻撃する','도마뱀을 닮은 짐승 마신\n참격 속성의 석장으로\n공격한다'),
 ('巨大な甲殻魔凸硬い甲羅に守られているが打撃に弱い','거대한 갑각 마신\n단단한 껍질을 둘렀으나\n타격에 약하다'),
 ('大型の虫魔凸外見に反して火属性の魔法が得意','대형 곤충 마신\n겉모습과 달리\n화속성 마법에 능하다'),
 ('尾針を飛ばして攻撃する飛虫魔凸','꼬리의 침을 날려\n공격하는 비충 마신'),
 ('狡猾で凶暴な魔凸反撃とクリティカル能力に長けている','교활하고 흉포한 마신\n반격과 치명타 능력이\n뛰어나다'),
 ('魔法が得意な甲殻魔凸強力な水属性の魔法を使う','마법에 능한 갑각 마신\n강력한 수속성 마법을\n사용한다'),
 ('槍を得意とする鳥魔凸急所攻撃が得意で回避能力を持つ','창에 능한 조류 마신\n급소 공격에 뛰어나며\n회피 능력을 지녔다'),
 ('日光浴好きな水棲魔凸尻尾で突く攻撃と水属性魔法を使う','일광욕을 즐기는 수생 마신\n꼬리로 찌르는 공격과\n수속성 마법을 사용한다'),
 ('格闘が得意な鳥魔凸回避能力が高い','격투에 능한 조류 마신\n회피 능력이 높다'),
 ('雌型の虫魔凸大型魔凸に付き従っていることが多い','암컷 형태의 곤충 마신\n대형 마신을 따라다니는\n일이 많다'),
 ('再生と破壊の炎を司る大型の鳥魔凸','재생과 파괴의 불꽃을\n관장하는 대형 조류 마신'),
 ('風と水の加護を受けている竜魔凸の亜種','바람과 물의 가호를 받는\n용 마신의 아종'),
 ('獣魔凸を統べる超神の一人常に血に飢えている','짐승 마신을 다스리는 초신\n언제나 피에 굶주려 있다'),
 ('魔法が得意な獣魔凸獣魔凸を統べる超神の一人','마법에 능한 짐승 마신\n짐승 마신을 다스리는\n초신 중 하나'),
 ('獣魔凸を統べる超神の一人で戦神として崇められている','짐승 마신을 다스리는 초신\n전쟁의 신으로\n숭배받고 있다'),
 ('混沌を支配する超神元は獣魔凸を統べる一人','혼돈을 지배하는 초신\n본래 짐승 마신을\n다스리던 자 중 하나'),
]
EXACT = {
 '想像を、絶する、結ま・・・':'상상을... 초월한... 결말...',
 'ですが、お気をつけなさい、\nここからが本番ですよ？':'하지만 조심하세요\n이제부터가 본격적입니다',
 'なあ、何で魔凸たちは\nテージを見ると騒ぎ出すんだ？':'그런데 마신들은 왜\n테이지를 보면 소란을 피워?',
 'ところで、何でベセクには\nこんなに魔凸が多いんだ？':'그런데 베세크에는 왜\n이렇게 마신이 많은 거야?',
 'ふっ・・、こっちも、\n魔凸には聞いてないよ':'훗... 이쪽도\n마신에게 물은 건 아니야',
 '高位な魔凸の気配だ、\n小僧に憑依しようとしている！！':'고위 마신의 기척이다\n애송이에게 빙의하려 한다!',
 '魔凸でも消滅を恐れる、\nということですか・・・':'마신도 소멸을\n두려워한다는 건가요...',
 'エル・ステーラは聖属性\nの魔凸です':'엘 스테라는\n성속성 마신입니다',
 'そろそろ終わりにしよう、\n神の名を持つ魔凸よ':'이제 끝내자\n신의 이름을 지닌 마신이여',
 'そして我が、ベセク最強の\n魔凸となってくれるわ！！':'그리고 내가 베세크 최강의\n마신이 되어 주마!',
 '神の名を持つ魔凸・・・\n一体どういうことだ？':'신의 이름을 지닌 마신...\n대체 무슨 뜻이지?',
 'レオ・レクスは闇属性の\n魔凸だから・・・':'레오 렉스는\n암속성 마신이니까...',
 'ベセクの最上階に居座る\n魔凸なんだ':'베세크 최상층에\n자리 잡은 마신이야',
 'それが、ルティカの追う\n魔凸だというの・・・？':'그게 루티카가 쫓는\n마신이라는 거야...?',
 '賢しい異端児よ、\n我は人でも、魔凸でもない':'영악한 이단아여\n난 인간도 마신도 아니다',
 'この国の王は、魔凸の力を\n支配しうる者のみが成り得る':'마신의 힘을 지배하는 자만이\n이 나라의 왕이 될 수 있다',
 '・・・魔凸なんかに\n話すことなんてない！！':'...마신 따위에게\n할 말은 없어!',
 'プッチー来てよう、その魔凸に\nパチキ食らわそうと追いかけ回してん':'열받아서 그 마신한테\n박치기하려고 쫓아다녔어',
 'ほんで、いっぱい魔凸倒して\nヒーローになんねん！！':'그래서 마신을 잔뜩 잡고\n영웅이 될 거야!',
 '金色の、全身骨のような造形の\n魔凸なんだが・・・':'금빛에 온몸이 뼈처럼 생긴\n마신인데...',
 'アリエルちゃんは魔凸が怖いのに\nどうしてベセクへ行くのでしょう':'아리엘은 마신이 무서운데\n왜 베세크에 가는 걸까요?',
 'かつて、人に化ける魔凸が\nこの世に存在していた・・・':'옛날 이 세상에는\n인간으로 변하는 마신이 있었지',
 'ちょいと耳に挟んだ情報だけど\n人に化ける魔凸がいるらしいな':'얼핏 들은 얘긴데\n인간으로 변하는 마신이 있대',
 '・・・魔凸の姿を確認した\n行くぞ':'...마신을 확인했다\n가자',
 'どんな魔凸なのかもわからないのに\n本当に見つけられるのか？':'어떤 마신인지도 모르는데\n정말 찾을 수 있겠어?',
 '奴は狡猾な魔凸だ':'놈은 교활한 마신이다',
 'だって、魔凸に聞いても\n知らないって言うんだよ？':'마신에게 물어봐도\n모른다고 하잖아?',
 '死を司りしその魔凸、\n光りを嫌い地の底をさまよう':'죽음을 관장하는 그 마신은\n빛을 피해 땅 밑을 떠돈다',
 '彼女自身も厄介ですが\nあの魔凸はもっと厄介です':'그녀도 성가시지만\n저 마신은 더 성가십니다',
 'はあ、はあ、はあ、\nくそっ魔凸たちめ・・・':'하아, 하아, 하아,\n젠장, 이 마신 놈들...',
 'ああ・・・数匹の魔凸に対し、\n王国の騎士団、総勢１６００人でな':'그래... 마신 몇 마리에\n왕국 기사단 1600명이 맞섰지',
 'いかに美しい場所と言えど\nこう魔凸がいては、な':'아무리 아름다운 곳이라도\n이렇게 마신이 있어서야...',
 'いったい何匹の魔凸を\nその本の中に呑みこんだのだ？':'대체 몇 마리의 마신을\n그 책 속에 삼킨 것이냐?',
 'ラキは人間を襲うような\n低俗な魔凸ではない':'라키는 인간을 덮치는\n저급한 마신이 아니야',
 '（やっぱり、ラキも他の魔凸と\n　変わらないじゃないか・・・）':'(역시 라키도 다른 마신과\n다를 게 없잖아...)',
}

def units(text): return sum(1 if ord(c)<128 else 2 for c in text)
@lru_cache(maxsize=None)
def wrap(text, width, lines):
    """Reflow without deleting non-whitespace characters; prefer word boundaries."""
    if len(text.split('\n'))<=lines and all(units(s)<=width for s in text.split('\n')): return text
    flat=re.sub(r'\s+',' ',text).strip()
    @lru_cache(maxsize=None)
    def solve(pos,left):
        if pos>=len(flat):return (0,[])
        if not left:return None
        result=None
        for end in range(pos+1,len(flat)+1):
            part=flat[pos:end].strip();size=units(part)
            if size>width:break
            nxt=end
            while nxt<len(flat) and flat[nxt]==' ':nxt+=1
            tail=solve(nxt,left-1)
            if tail is None:continue
            boundary=end==len(flat) or flat[end-1]==' ' or flat[end]==' '
            cost=tail[0]+(0 if boundary else 10000)+(width-size)**2
            if result is None or cost<result[0]:result=(cost,[part]+tail[1])
        return result
    result=solve(0,lines)
    return '\n'.join(result[1]) if result else None

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    long_source=OUT/'long_dialogue_review_source.json'
    if long_source.exists():
        originals=json.loads(long_source.read_text());corrections=json.loads((OUT/'long_dialogue_corrections.json').read_text())
        assert len(originals)==132 and set(corrections)=={str(i) for i in range(132)}
        EXACT.update({originals[int(i)]['source']:t for i,t in corrections.items()})
    desc=dict(DESC_PAIRS)
    glossary={r['source']:r['target'] for r in csv.DictReader((ROOT/'localization/glossary.csv').open()) if r['status']=='approved'}
    prior={}
    for file in ('tutorial_slice','status_slice'):
        for r in json.loads((ROOT/f'localization/{file}.json').read_text())['records']:prior[r['source']]=r['target']
    stats={}; plan=[];changes=[];excluded=[]
    function_width={}
    for m in map(json.loads,(ROOT/'extracted/original/text/structured.jsonl').open()):
        if m['kind']=='rtb_literal' and m.get('japanese_candidate'):
            function_width[m['function']]=max(function_width.get(m['function'],30),max(map(units,m['source'].split('\n'))))
    for label,name in [('structured','structured_ko_working_translated.tsv'),('elf','elf_strings_ko_final_v4.tsv')]:
        source=ROOT/'localization/imports/20260917'/name
        with source.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f,delimiter='\t');headers=reader.fieldnames;rows=list(reader)
        metadata={r['id']:r for r in map(json.loads,(ROOT/f'extracted/original/text/{"structured" if label=="structured" else "elf_strings"}.jsonl').open())}
        edits=[];counts=Counter()
        for i,row in enumerate(rows):
            target=row['target'];src=row['source'];m=metadata[row['id']];original=target
            if not target or target==src:continue
            reason=[];target=unicodedata.normalize('NFC',target).replace('\u200b','')
            if '凸' in src:
                target=re.sub(r'마\s*볼록?', '마신',target)
            if '錫杖' in src:target=target.replace('주석 지팡이','석장')
            target=EXACT.get(src,desc.get(re.sub(r'\s+','',src),target))
            target=prior.get(src,glossary.get(src,target))
            target=FIXED_NAMES.get(src,target)
            if target!=original:reason.append('term_or_meaning_correction')
            reject=[]
            if label=='elf':
                off=m['payload_offset']
                # Game-facing map/condition table and compact battle/status labels.
                allowed=(0x4368c8<=off<0x4391b0 or 0x453368<=off<=0x453660 or off in (0x452808,0x452810,0x452820))
                if not allowed:reject.append('internal_or_unverified_elf_scope')
                if units(target)>m['source_byte_length']:reject.append('elf_capacity_requires_rewrite_or_relocation')
                if any(ord(c)<32 and c!='\n' or 127<=ord(c)<160 for c in target):reject.append('control_bytes')
            elif m['kind']=='plain_file':reject.append('configuration_not_dialogue')
            elif m['kind']=='db_field':
                cap=next(s[2]-1 for s in SCHEMAS[Path(m['path']).stem][m['section']] if s[0]==m['field'])
                if units(target)>cap:reject.append('db_capacity')
            elif m['kind']=='rtb_literal':
                if m.get('decode_error') or not m.get('japanese_candidate'):reject.append('unverified_literal')
                if '볼록' in target:reject.append('unresolved_glyph_alias')
                # Match source line budget, with the existing 360px dialogue minimum.
                # Preserve explicit longer/narration layouts instead of forcing all to two lines.
                width=max(30,min(48,function_width.get(m['function'],30))); lines=max(2,len(src.split('\n')))
                wrapped=wrap(target,width,lines)
                if wrapped is None:reject.append('dialogue_layout_needs_condensing')
                else:
                    if target!=wrapped:reason.append('line_reflow')
                    target=wrapped
                if units(target)>255:reject.append('rtb_capacity')
            if label=='structured' and m['kind']!='plain_file' and any(ord(c)<32 and c!='\n' or 127<=ord(c)<160 for c in target):reject.append('control_bytes')
            if '볼록' in target:reject.append('unresolved_glyph_alias')
            status='deferred' if reject else 'ready'
            item=dict(id=row['id'],catalog=label,source=src,target=target,original_target=original,reasons=reason,exclusions=reject,metadata=m)
            if reject:excluded.append({k:v for k,v in item.items() if k!='metadata'})
            else:plan.append(item)
            if target!=original:changes.append({k:v for k,v in item.items() if k!='metadata'})
            edits.append(dict(row=i+2,target=target,status=status));counts[status]+=1
        # JSON is a machine intermediate; TSV authoring is handled by the artifact builder.
        write_json(OUT/(label+'_table.json'),dict(headers=headers,rows=[[r[h] for h in headers] for r in rows],edits=edits))
        stats[label]=dict(counts)
    for name,rows in [('plan',plan),('changes',changes),('deferred',excluded)]:
        with (OUT/(name+'.jsonl')).open('w') as f:
            for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    write_json(OUT/'summary.json',dict(counts=stats,exclusions=dict(Counter(x for r in excluded for x in r['exclusions'])),corrected_rows=len(changes)))
    print((OUT/'summary.json').read_text())

if __name__=='__main__':main()
