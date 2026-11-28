"""Bounded local OCR, source extraction, offline transcription and paged PDF generation."""
import csv
import io
import os
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from threading import Lock
from html import escape
from pathlib import Path
import pymupdf as fitz
from PIL import Image,ImageOps
from .store import ROOT,DATA,now
MAX_UPLOAD=8*1024*1024
def tesseract(image,lang):
    binary=os.getenv('TESSERACT_CMD') or shutil.which('tesseract')
    if not binary and os.name=='nt':
        candidate=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Tesseract-OCR'/'tesseract.exe'
        if candidate.exists():binary=str(candidate)
    if not binary:raise ValueError('Install Tesseract OCR. See SETUP.md for the Windows installer and language packs.')
    t={'en':'eng','hi':'hin+eng','te':'tel+eng','kn':'kan+eng'}[lang]
    extras=['--tessdata-dir',str(DATA/'ocr-languages')] if (DATA/'ocr-languages'/'eng.traineddata').is_file() else []
    buf=io.BytesIO();image.convert('RGB').save(buf,format='PNG')
    result=subprocess.run([binary,'stdin','stdout','-l',t,*extras,'--psm','6','tsv'],input=buf.getvalue(),capture_output=True,timeout=35)
    if result.returncode:raise ValueError('OCR could not read this image. Run SETUP_OCR_WINDOWS.bat and select the document language.')
    lines={};scores=[]
    for row in csv.DictReader(io.StringIO(result.stdout.decode('utf8',errors='replace')),delimiter='\t'):
        word=(row.get('text') or '').strip()
        if not word:continue
        key=tuple(row[k] for k in ('block_num','par_num','line_num'))
        line=lines.setdefault(key,[])
        left=int(row['left']);height=int(row['height'])
        if line and left-line[-1][1]>max(24,height*2):word='   '+word
        line.append((word,left+int(row['width'])));scores.append(float(row['conf']))
    return '\n'.join(' '.join(word for word,_ in line) for line in lines.values()),round(sum(scores)/len(scores)) if scores else 0
def extract(data,name,lang='en',citizen=False):
    if not 0<len(data)<=MAX_UPLOAD:raise ValueError('Select a file up to 8 MB.')
    ext=Path(name).suffix.lower()
    if ext=='.txt' and not citizen:return [(1,data.decode('utf8-sig')[:200000],None)]
    if ext=='.pdf' and data.startswith(b'%PDF-'):
        with fitz.open(stream=data,filetype='pdf') as pdf:
            if pdf.needs_pass or len(pdf)>(4 if citizen else 80):raise ValueError('PDF is locked or exceeds the page limit.')
            out=[]
            for i,p in enumerate(pdf):
                text=p.get_text('text',sort=True)[:20000];score=None
                if len(text.strip())<12:
                    factor=min(3.0,2400/max(1,p.rect.width,p.rect.height))
                    pix=p.get_pixmap(matrix=fitz.Matrix(factor,factor),alpha=False,colorspace=fitz.csRGB)
                    text,score=tesseract(Image.frombytes('RGB',(pix.width,pix.height),pix.samples),lang)
                out.append((i+1,text,score))
            return out
    if ext not in ['.png','.jpg','.jpeg','.webp']:raise ValueError('Use a supported image or PDF.')
    with Image.open(io.BytesIO(data)) as im:
        if im.format not in ['JPEG','PNG','WEBP'] or im.width*im.height>16000000:raise ValueError('Unsupported image or excessive dimensions.')
        im=ImageOps.exif_transpose(im);im.thumbnail((2400,2400))
        text,score=tesseract(im,lang)
        return [(1,text,score)]
def scanned(data,name,lang):
    pages=extract(data,name,lang,True)
    labels={'name':['applicant name','full name','name','పేరు','नाम','ಹೆಸರು'],'village':['village','గ్రామం','गाँव','ಗ್ರಾಮ'],'locality':['locality','local area'],'district':['district','జిల్లా','जिला','ಜಿಲ್ಲೆ'],'school':['school name','school'],'trade':['trade','occupation']}
    labels.update({'date of birth':['date of birth','dob','జన్మ తేదీ','जन्म तिथि','ಜನ್ಮ ದಿನಾಂಕ'],'gender':['gender','లింగం','लिंग','ಲಿಂಗ'],'address':['address','చిరునామా','पता','ವಿಳಾಸ'],'state':['state','రాష్ట్రం','राज्य','ರಾಜ್ಯ'],'postal code':['pin code','pincode','postal code']})
    aliases={alias:key for key,terms in labels.items() for alias in terms}
    pattern=re.compile(r'(?<!\w)('+ '|'.join(map(re.escape,sorted(aliases,key=len,reverse=True))) +r')[ \t]*[:：\-][ \t]*',re.I)
    candidates={};structured=[]
    for number,raw,confidence in pages:
        redacted=re.sub(r'(?<!\d)(?:\d[ -]?){8,18}(?!\d)','[redacted]',raw)
        lines=[]
        rawlines=redacted.splitlines()
        for index,line in enumerate(rawlines):
            marks=list(pattern.finditer(line))
            if not marks:
                if line.strip():lines.append(line.strip())
                continue
            if line[:marks[0].start()].strip():lines.append(line[:marks[0].start()].strip())
            for i,m in enumerate(marks):
                value=line[m.end():marks[i+1].start() if i+1<len(marks) else len(line)].strip()
                lines.append(m.group(1)+': '+value)
                if not value and index+1<len(rawlines) and not pattern.search(rawlines[index+1]):
                    value=rawlines[index+1].strip()
                if value:candidates.setdefault(aliases[m.group(1).lower()],value[:100])
        structured.append({'page':number,'lines':lines,'confidence':confidence})
    text='\n\n'.join('\n'.join(page['lines']) for page in structured)[:16000]
    kind=next((label for term,label in [('income','Income evidence'),('school','School record'),('ration','Household document'),('aadhaar','Identity document'),('marriage','Marriage record')] if term in text.lower()),'Unclassified document')
    return {'pages':structured,'text':text,'kind':kind,'fields':candidates,'confidence':[p[2] for p in pages],'readable':len(text.strip())>=8}
_speech_lock = Lock()

@lru_cache(maxsize=1)
def _load_speech(model):
    from faster_whisper import WhisperModel
    return WhisperModel(model, device='cpu', compute_type='int8', local_files_only=True)

def transcribe(data,lang):
    model=os.getenv('WELFARE_WHISPER_DIR',str(DATA/'speech-model'))
    if not (Path(model) / 'model.bin').is_file():
        raise ValueError('Run SETUP_LOCAL_VOICE.bat in this project folder to install the local speech model.')
    try:
        import numpy as np
    except ImportError as error:
        raise ValueError('Run SETUP_LOCAL_VOICE.bat in this project folder to install voice support.') from error
    if len(data)%4 or not 3200<=len(data)<=45*16000*4:
        raise ValueError('Please record between a short sentence and 40 seconds, then retry.')
    samples=np.frombuffer(data,dtype='<f4')
    if not np.isfinite(samples).all() or np.max(np.abs(samples))>1.01:
        raise ValueError('Invalid microphone samples. Refresh the page and record again.')
    if np.max(np.abs(samples)) < 0.001:
        raise ValueError('The microphone sent silence. Check the input device or unmute it and try again.')
    try:
        with _speech_lock:
            speech = _load_speech(model)
            segments, _ = speech.transcribe(samples, language=lang, beam_size=1, condition_on_previous_text=False)
            text = ' '.join(segment.text.strip() for segment in segments).strip()[:3000]
    except (ImportError, OSError) as error:
        raise ValueError('The local voice engine could not start. Run SETUP_LOCAL_VOICE.bat and check its final message.') from error
    except Exception as error:
        raise ValueError('Local transcription failed. Check that the speech model is installed and try a shorter recording.') from error
    if not text:raise ValueError('No speech detected. Check the microphone and try again.')
    return text

def read_aloud(text,lang):
    if lang not in ('en','hi','te') or not isinstance(text,str) or not 0<len(text.strip())<=6000:
        raise ValueError('Choose a supported language and up to 6000 characters.')
    exe=shutil.which('espeak-ng')
    if not exe and os.name=='nt':
        for key in ('ProgramFiles','ProgramW6432','ProgramFiles(x86)'):
            path=Path(os.environ.get(key,'C:/Program Files'))/'eSpeak NG'/'espeak-ng.exe'
            if path.is_file():
                exe=str(path)
                break
    if not exe:raise ValueError('Install eSpeak NG on this laptop for Hindi and Telugu read-aloud, then restart the project.')
    try:
        with tempfile.TemporaryDirectory() as directory:
            wav=Path(directory)/'speech.wav'
            result=subprocess.run([exe,'-v',lang,'-b','1','-s','145','-w',str(wav),'--stdin'],input=text.encode('utf8'),capture_output=True,timeout=30)
            if result.returncode or not wav.is_file():raise ValueError('The local voice could not generate audio.')
            return wav.read_bytes()
    except (OSError,subprocess.TimeoutExpired) as error:
        raise ValueError('The local voice engine could not finish. Try a shorter passage.') from error

def pdf_report(title,sections,lang='en'):
    h=lambda s:escape(str(s))
    html='<h1>'+h(title)+'</h1><p>'+h(now()[:10])+' &nbsp; | &nbsp; Welfare Scheme Navigator</p>'
    for heading,lines in sections:
        html+='<h2>'+h(heading)+'</h2>'+''.join('<p>'+h(line)+'</p>' for line in lines)
    html+='<p>Academic guidance. The responsible authority verifies eligibility and receives the application.</p>'
    css="""@font-face{font-family:Telugu;src:url(NotoSansTelugu-Regular.ttf)} @font-face{font-family:Hindi;src:url(NotoSansDevanagari-Regular.ttf)} body{font:11pt sans-serif,Telugu,Hindi;color:#233948} h1{font-size:23pt;color:#123e48}h2{font-size:15pt;color:#146665;margin-top:16pt}p{margin:5pt 0}"""
    story=fitz.Story(html=html,user_css=css,archive=fitz.Archive(str(ROOT/'static/fonts')))
    out=io.BytesIO();writer=fitz.DocumentWriter(out);more=True
    while more:
        dev=writer.begin_page(fitz.paper_rect('a4'))
        more,_=story.place(fitz.Rect(40,40,555,795));story.draw(dev);writer.end_page()
    writer.close();return out.getvalue()
