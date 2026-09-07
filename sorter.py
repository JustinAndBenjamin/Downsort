import os, shutil

CATS=[
 ("image",("jpg","jpeg","png","gif","bmp","tiff","webp","svg"),"Bilder"),
 ("doc",("pdf","docx","doc","txt","xlsx","xls","pptx","ppt","csv","odt","rtf","md"),"Dokumente"),
 ("music",("mp3","wav","aac","flac","ogg","m4a","opus","wma","alac","aiff","ape"),"Musik"),
 ("video",("mp4","avi","mkv","mov","wmv","flv","mpeg","mpg","webm","vob","3gp","3g2","m4v","divx","ts","mts","m2ts"),"Videos"),
 ("app",("exe","msi","zip","bat","rar","7z","tar","gz","iso","dmg","pkg","deb","rpm","apk","jar","tgz"),"Anwendungen"),
]
EXT={e:c for c,ex,l in CATS for e in ex}
LBL={c:l for c,ex,l in CATS}

def rs(b):
 for u in ["B","KB","MB","GB","TB"]:
  if b<1024:return f"{b:.2f}{u}"
  b/=1024
 return f"{b:.2f}PB"

def mvf(s,t,n):
 os.makedirs(t,exist_ok=True)
 d=os.path.join(t,n)
 if os.path.exists(d):
  p,e=os.path.splitext(n);i=1
  while os.path.exists(d):
   d=os.path.join(t,f"{p}_{i:02d}{e}");i+=1
 shutil.move(s,d);return os.path.basename(d)

def sort_downloads(df,folds):
 r=[]
 for fn in os.listdir(df):
  sp=os.path.join(df,fn)
  if not os.path.isfile(sp):continue
  e=fn.lower().rsplit(".",1)[-1]
  c=EXT.get(e)
  if not c:continue
  sz=os.path.getsize(sp)
  r.append({"name":mvf(sp,folds[c],fn),"category":LBL[c],"size":rs(sz)})
 return r