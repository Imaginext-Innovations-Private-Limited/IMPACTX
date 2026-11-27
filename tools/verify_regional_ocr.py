"""Optional synthetic OCR audit using installed fonts and Tesseract language packs.
Developer-only, no network. Pass --font-dir to point to NotoSans...-Regular.ttf.
Generated images are not stored; source messages are known development cases.
"""
import argparse, csv, io, os, sys, unicodedata
from pathlib import Path
from difflib import SequenceMatcher
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'benchmark')]
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from scamshield.main import app
from regional_audit_cases import CASES
FONTS={'en':'','hi':'Devanagari','bn':'Bengali','kn':'Kannada','te':'Telugu','or':'Oriya','mr':'Devanagari','ta':'Tamil','ml':'Malayalam','gu':'Gujarati','pa':'Gurmukhi'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--font-dir',type=Path,default=Path('/usr/share/fonts/truetype/noto'));p.add_argument('--out',type=Path,default=ROOT/'benchmark/regional_ocr_audit.csv');args=p.parse_args()
    os.environ.pop('GROQ_API_KEY',None);os.environ.pop('SARVAM_API_KEY',None)
    c=TestClient(app); rows=[];norm=lambda t:' '.join(unicodedata.normalize('NFC',t).split())
    for lang,script in FONTS.items():
        text=CASES[lang][0][0];font_path=args.font_dir/f'NotoSans{script}-Regular.ttf';row=dict(language=lang,ocr_status='missing_font',text_similarity='',original_level='',ocr_level='',extracted='')
        if font_path.exists():
            font=ImageFont.truetype(str(font_path),48);probe=Image.new('RGB',(1,1));bounds=ImageDraw.Draw(probe).textbbox((0,0),text,font=font)
            im=Image.new('RGB',(bounds[2]-bounds[0]+100,bounds[3]-bounds[1]+100),'white');ImageDraw.Draw(im).text((50-bounds[0],50-bounds[1]),text,font=font,fill='black')
            b=io.BytesIO();im.save(b,format='PNG',dpi=(300,300));r=c.post('/api/ocr',params={'language':lang},files={'file':('synthetic.png',b.getvalue(),'image/png')});row['ocr_status']=r.status_code
            if r.status_code==200:
                extracted=r.json()['text'];row['extracted']=extracted;row['text_similarity']=round(SequenceMatcher(None,norm(text),norm(extracted)).ratio(),3)
                row['original_level']=c.post('/api/analyze',json={'text':text,'language':lang}).json()['level'];row['ocr_level']=c.post('/api/analyze',json={'text':extracted,'language':lang,'channel':'image'}).json()['level']
        rows.append(row);print(lang,row['ocr_status'],row['text_similarity'],row['original_level'],row['ocr_level'])
    with args.out.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
if __name__=='__main__':main()
