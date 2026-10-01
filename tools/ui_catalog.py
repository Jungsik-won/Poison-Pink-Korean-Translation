#!/usr/bin/env python3
"""Persist visually reviewed asset categories and Korean title drafts."""
import json
from localization_pipeline import ROOT, write_json

TITLE_DRAFTS = {
    135:'유닛 턴',136:'이동과 공격',137:'공격',138:'피해 보정',139:'사정거리에 따른 피해 보정',
    140:'스킬 사용',141:'스킬의 종류',142:'스킬 획득 방법',143:'오버킬',144:'마신 포획',
    145:'포획한 마신의 활용',146:'마신 장벽',147:'마신의 약점',148:'유닛 재행동',149:'쌍격',
    150:'대형 마신 포획 방법',151:'둘러싸서 포획',153:'게임 이용 안내',154:'GAME OVER',
    155:'춘희의 저택',156:'포획한 마신의 활용 가치',157:'포획한 마신의 활용 가치',
    158:'스텝 스톤 규칙·조작',159:'스텝 스톤 규칙·조작',160:'스텝 스톤 규칙·조작',
    161:'스텝 스톤 규칙·조작',162:'내성',
}
MENUS = {
    'sys000':'전투 명령 9종과 추가 명령','sys009':'결정·취소·선택 안내','sys011':'스킬 종류 제목',
    'sys015':'출격 준비·승패 조건·저장·로드','sys019':'상점·장비·스킬 조작','sys021':'아이템 분류 탭',
    'sys027':'저장 슬롯 안내','sys036':'대화 상대 선택 안내','sys040':'거점 메뉴','sys045':'장비 제목',
}


def main():
    audit=json.loads((ROOT/'reports/ui_texture_audit.json').read_text())
    catalog_path=ROOT/'localization/ui_catalog.json'
    previous=json.loads(catalog_path.read_text()) if catalog_path.exists() else {}
    previous_rows={r['path']:r for group in ('help_and_related','menu_atlases') for r in previous.get(group,[])}
    assets={a['path']:a for a in audit['catalog']};rows=[];menus=[]
    for n,title in TITLE_DRAFTS.items():
        path='dmap/ev/ev%d.tm2'%n;a=assets[path]
        rows.append(dict(path=path,sha256=a['sha256'],size=[a['width'],a['height']],korean_title_draft=title,
            classification='health_notice' if n==153 else 'game_over' if n==154 else 'minigame_help' if 158<=n<=161 else 'help',
            priority=0 if n==135 else 1 if n<=149 else 2,
            status='runtime_verified_title_body' if n==135 else 'source_identified',preview=a['preview'],
            notes='Inset screenshot name/stats preserved' if n==135 else 'Full body transcription and translation pending'))
    for name,description in MENUS.items():
        a=assets['status/'+name+'.tm2']
        menus.append(dict(path=a['path'],sha256=a['sha256'],purpose=description,priority=1,
            sprite_rectangles=len(a['uad']['rectangles']),status='9_commands_25_tiles_authored' if name=='sys000' else 'source_identified',preview=a['preview']))
    # Keep evidence earned after source discovery when it belongs to the same
    # immutable asset. Regenerating title drafts must not erase reviewed work.
    for row in rows+menus:
        old=previous_rows.get(row['path'],{})
        if old.get('sha256')==row['sha256']:
            for key in ('status','notes','translation_review','runtime_report','runtime_evidence','built_preview','build_sha256'):
                if key in old:row[key]=old[key]
    write_json(catalog_path,dict(schema_version=1,help_and_related=rows,menu_atlases=menus,
        notes=['Titles outside the authored sample are translation drafts, not approved terminology.',
               'ev153 is a play-health notice and ev154 is GAME OVER, not help pages.',
               'RTB common choice strings and ELF menu strings require separate field/reference mapping.']))
    print('Curated catalog:',len(rows),'help/related assets,',len(menus),'menu atlases')


if __name__=='__main__':main()
