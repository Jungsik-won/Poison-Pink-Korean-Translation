"""Prepare five character tabs; never writes or builds an ISO."""
import json,sys,unicodedata,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build/python_psd'))
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from ui_texture_codec import parse,serialize,preview_rgba,unpack_indices,uad_rectangles
from build_battle_conditions_psd import compile_texture
from make_battle_lettering_work import layered_psd

B=ROOT/'build/character_tabs_ko_v1';OUT=ROOT/'outputs/character_tabs_ko_v1'
PREFIX='STATUS/status/chr_cel/'
ROWS=[
 [('テージ','테이지',(49,27,108,45)),('ルティカ','루티카',(33,59,94,75)),('ラナンキュラス','라난큘러스',(30,86,124,102))],
 [('オリフェン','오리펜',(31,12,116,30)),('リバト','리바트',(35,46,80,62)),('マリィ','마리',(55,72,97,88)),('ローグ','로그',(73,98,119,114))],
 [('ハーシュ','하슈',(30,29,100,46)),('レイナ','레이나',(40,61,88,76)),('グリン','그린',(77,86,123,102))],
 [('ロンデミオン','론데미온',(14,32,106,49))],
 [('デュファストン','듀파스톤',(22,47,131,65))],
]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def text_mask(arr,rect):
 x,y,r,b=rect;a=arr[y:b,x:r].astype(int);hi=a[:,:,:3].max(2);lo=a[:,:,:3].min(2)
 return (hi>8)&((hi-lo)<=3+hi*.025)&(a[:,:,3]>200)

def render_word(text,width,height,fontpath):
 fs=height*2
 while True:
  font=ImageFont.truetype(str(fontpath),fs);glyphs=[]
  for char in text:
   im=Image.new('L',(fs*3,fs*3));ImageDraw.Draw(im).text((fs,fs),char,font=font,fill=255)
   box=im.getbbox();assert box;glyphs.append((im.crop(box),box[1]-fs))
  top=min(t for g,t in glyphs);bottom=max(t+g.height for g,t in glyphs)
  if bottom-top<=height and sum(g.width for g,t in glyphs)+(len(text)-1)*4<=width:break
  fs-=1;assert fs>20
 gap=(width-sum(g.width for g,t in glyphs))/(len(glyphs)-1)
 strip=Image.new('L',(width,height));x=0
 for g,t in glyphs:
  strip.paste(g,(round(x),round((height-(bottom-top))/2)+t-top));x+=g.width+gap
 return strip,dict(font_size_native=fs/4,ink_gap_native=gap/4)

def main():
 assert not B.exists() and not OUT.exists(),'Preserve prior reviewed artwork'
 B.mkdir(parents=True);OUT.mkdir(parents=True)
 fonts=[p for p in (Path.home()/'Library/Fonts').iterdir() if unicodedata.normalize('NFC',p.name)=='EBS주시경B.otf'];assert len(fonts)==1;fontpath=fonts[0]
 check=ImageFont.truetype(str(fontpath),80);missing=bytes(check.getmask(chr(0x10ffff)))
 assert all(bytes(check.getmask(c))!=missing for rows in ROWS for _,text,_ in rows for c in text)
 reports=[];previews=[]
 for i,rows in enumerate(ROWS):
  name=f'csl_tb{i}';source=PREFIX+name+'.tm2';rawpath=ROOT/'extracted/original/raw'/source;raw=rawpath.read_bytes();model=parse(raw)
  original=Image.open(ROOT/'extracted/original/images'/(source+'.png')).convert('RGBA')
  assert original.tobytes()==preview_rgba(model)
  uad=rawpath.with_suffix('.uad');layout=uad_rectangles(uad.read_bytes(),256,128)
  assert [r['rect'] for r in layout['rectangles']]==[[0,0,256,128]]
  arr=np.array(original);clean=arr.copy();authorized=np.zeros((128,256),bool);metrics=[];ink=Image.new('RGBA',(1024,512))
  for jp,ko,rect in rows:
   x,y,r,b=rect;mask=text_mask(arr,rect);ys,xs=np.where(mask);assert len(xs)>30
   box=[int(xs.min()+x),int(ys.min()+y),int(xs.max()+x+1),int(ys.max()+y+1)]
   # Remove only neutral text pixels and their antialias fringe, inside the label ROI.
   remove=np.array(Image.fromarray((mask*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)))>0
   tile=clean[y:b,x:r];tile[remove]=[0,0,0,255];authorized[y:b,x:r]=True
   left,top,right,bottom=box;word,info=render_word(ko,(right-left)*4,(bottom-top)*4,fontpath)
   colored=Image.new('RGBA',word.size,(255,255,255,0));colored.putalpha(word);ink.alpha_composite(colored,(left*4,top*4))
   metrics.append(dict(source=jp,target=ko,edit_roi=rect,source_ink_box=box,target_span_native=right-left,**info))
  background=Image.fromarray(clean);high=background.resize((1024,512),Image.Resampling.NEAREST);high.alpha_composite(ink)
  target=background.copy();small_ink=ink.resize(original.size,Image.Resampling.LANCZOS);target.alpha_composite(small_ink)
  # Constrain even the resampling fringe to the audited label rectangles.
  ta=np.array(target);ta[~authorized]=arr[~authorized];target=Image.fromarray(ta)
  compiled,checks=compile_texture(raw,target)
  before=np.frombuffer(unpack_indices(model),np.uint8).reshape(128,256)
  after=np.frombuffer(unpack_indices(parse(compiled)),np.uint8).reshape(128,256).copy()
  after[~authorized]=before[~authorized];m=parse(compiled);m['indices']=after.tobytes();compiled=serialize(m)
  assert len(compiled)==len(raw) and parse(compiled)['palette']==model['palette'] and parse(compiled)['header']==model['header']
  np.testing.assert_array_equal(after[~authorized],before[~authorized])
  decoded=Image.frombytes('RGBA',original.size,preview_rgba(parse(compiled)))
  target_arr=np.array(target);bright=np.all(target_arr[:,:,:3]>245,axis=2)&authorized
  assert bright.any();palette=np.array([list(c) for c in m['palette']]);assert np.all(palette[after[bright],3]>=128),'White must not become transparent'
  tm=B/'textures'/source;tm.parent.mkdir(parents=True,exist_ok=True);tm.write_bytes(compiled)
  original.save(OUT/(name+'_original.png'));target.save(OUT/(name+'_ko.png'));decoded.save(OUT/(name+'_game_preview.png'))
  layered_psd(OUT/(name+'_ko.psd'),[('원문_일본어_내보내기제외',original.resize((1024,512),Image.Resampling.NEAREST),False),('배경_인물_보존',background.resize((1024,512),Image.Resampling.NEAREST),True),('한글_EBS주시경_Bold',ink,True)],high)
  reports.append(dict(source=source,source_sha256=sha(rawpath),compiled_sha256=sha(tm),uad_sha256=sha(uad),rows=metrics,checks=checks,unmodified_pixels_exact=True,opaque_white_checked=True))
  previews.append((original,decoded))
 board=Image.new('RGB',(1024,1280),(40,45,50))
 for i,(old,new) in enumerate(previews):
  for x,im in [(0,old),(512,new)]:
   im=im.resize((512,256),Image.Resampling.NEAREST);board.paste(im,(x,i*256),im)
 board.save(OUT/'원문_한글_비교.png')
 report=dict(status='prepared_not_applied',iso_built=False,runtime_verified=False,font=str(fontpath),font_sha256=sha(fontpath),font_family=check.getname(),textures=reports,character_names=12)
 (B/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(prepared=5,names=12,font=check.getname(),metrics=[r['rows'] for r in reports]),ensure_ascii=False))
if __name__=='__main__':main()
