"""Quick offline release smoke check. No live API calls; run from project root."""
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.pop('GROQ_API_KEY', None)
os.environ.pop('SARVAM_API_KEY', None)
from fastapi.testclient import TestClient
from scamshield.main import app
from scamshield.languages import LANGUAGE_NAMES, LEVELS
from scamshield import voice


def main():
    c=TestClient(app)
    health=c.get('/api/health').json()
    print('Release:',health['version'],'| Training samples:',health['training_samples'])
    assert health['version']=='2.1.1' and health['training_samples']==394
    assert c.get('/').status_code==200
    for message,expected in [
        ('Your OTP is 482193. Do not share it with anyone.', 'no_clear_signal'),
        ('Send your OTP immediately to claim your lottery prize.', 'high'),
        ('તમારી સામે પોલીસ કેસ છે. ધરપકડ ટાળવા માટે પૈસા મોકલો.', 'caution'),
        ('வேலை பெற பதிவு கட்டணமாக ரூ. 5000 செலுத்துங்கள்.', 'caution'),
        ('നിങ്ങൾക്ക് ലോട്ടറി സമ്മാനം ലഭിച്ചു. സമ്മാനം ലഭിക്കാൻ ആദ്യം 2000 രൂപ അടയ്ക്കുക.', 'caution'),
        ('ਪੈਸੇ ਪ੍ਰਾਪਤ ਕਰਨ ਲਈ ਆਪਣਾ UPI PIN ਦਰਜ ਕਰੋ।', 'caution'),
    ]:
        r=c.post('/api/analyze',json={'text':message,'cloud_consent':False}); assert r.status_code==200
        assert r.json()['level']==expected, (expected,r.json()['level'])
    print('PASS: six text and regional regression cases')
    natural=basic=0
    for lang in LANGUAGE_NAMES:
        for level in LEVELS:
            for topic in voice.TOPICS if level=='high' else ['generic']:
                r=c.get('/static/voices-basic/'+lang+'/'+level+'-'+topic+'.mp3');assert r.status_code==200
                basic+=1
                r=c.get('/api/voice/audio',params={'language':lang,'level':level,'topic':topic})
                if r.status_code==200:natural+=1
    print(f'PASS: {basic} basic clips; {natural} optional natural cached clips available')
    with (ROOT/'demo_assets'/'demo_sms.png').open('rb') as f:
        r=c.post('/api/ocr?language=en',files={'file':('demo_sms.png',f,'image/png')})
    if r.status_code==200:
        a=c.post('/api/analyze',json={'text':r.json()['text'],'channel':'image'}); assert a.json()['level']=='high'
        print('PASS: actual English OCR and subsequent detection')
    else:
        print('CHECK REQUIRED: OCR unavailable:',r.status_code,r.json().get('detail'))
    print('Offline smoke check complete. Live browser/provider tests are separate.')

if __name__=='__main__':main()
