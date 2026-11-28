"""Optional Chromium DOM smoke with an in-process HTTP bridge, not live providers.
Developer only: pip install playwright; playwright install chromium, or set
CHROMIUM_PATH to an existing binary. No public network or API credentials used.
"""
import os, sys, re, json, base64, shutil
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from scamshield import main, cloud
import httpx
from playwright.sync_api import sync_playwright, expect

BOOT=r'''
window.testOnline=true;
Object.defineProperty(navigator,'onLine',{get:()=>window.testOnline,configurable:true});
window.testCopyWorks=true;window.copied='';
Object.defineProperty(navigator,'clipboard',{value:undefined,configurable:true});
document.execCommand=(cmd)=>{window.copied=document.activeElement.value;return window.testCopyWorks};
window.SpeechRecognition=class {start(){window.testMic=this} stop(){this.onend()} abort(){this.onend()}};
window.fetch=async (path,options={})=>{
 const payload={path,method:options.method||'GET',headers:options.headers||{}};
 if(options.body instanceof FormData){payload.fields={};payload.files=[];for(const [key,val] of options.body){if(val instanceof File)payload.files.push([key,val.name,val.type,Array.from(new Uint8Array(await val.arrayBuffer()))]);else payload.fields[key]=val;}}
 else if(options.body)payload.body=options.body;
 const r=await py_http(payload);
 const bytes=Uint8Array.from(atob(r.body),c=>c.charCodeAt(0));
 return new Response([204,205,304].includes(r.status)||payload.method==='HEAD'?null:bytes,{status:r.status,headers:{'Content-Type':r.type}});
};
// Actual metadata and decoding for selected recordings use the native Audio.
// Warning playback URLs are bridged to bytes, avoiding browser navigation.
const NativeAudio=window.Audio;
window.Audio=function(src){if(!src||!src.startsWith('/'))return new NativeAudio(src);const a=new NativeAudio();let active=true;const play=a.play.bind(a),pause=a.pause.bind(a);let blob;
 a.play=async()=>{const response=await fetch(src);if(!response.ok)throw Error('audio missing');if(!active)return;blob=URL.createObjectURL(await response.blob());a.src=blob;return play()};a.pause=()=>{active=false;pause();if(blob)URL.revokeObjectURL(blob)};return a;};
'''

def main_test():
    os.environ.pop('GROQ_API_KEY',None); os.environ.pop('SARVAM_API_KEY',None)
    client=TestClient(main.app); calls=[]; providers=[]; status={'failure':False,'backup':False}
    def bridge(payload):
        path=payload['path']; method=payload['method']; calls.append((method,path,payload.get('body')))
        kw={'headers':payload['headers']}
        if 'files' in payload:
            kw['files']=[(k,(n,bytes(v),mime)) for k,n,mime,v in payload['files']];kw['data']=payload['fields']
        elif 'body' in payload:kw['content']=payload['body']
        r=client.request(method,path,**kw)
        return {'status':r.status_code,'body':base64.b64encode(r.content).decode(),'type':r.headers.get('content-type','application/octet-stream')}
    def provider(url,**kwargs):
        if 'sarvam' in url:
            providers.append('sarvam');return httpx.Response(200,request=httpx.Request('POST',url),json={'transcript':'Enter your UPI PIN to receive your refund immediately.'})
        model=kwargs['json']['model'];providers.append(model)
        if status['failure'] or (status['backup'] and model==cloud.MODEL):return httpx.Response(503,request=httpx.Request('POST',url),json={})
        payload={'level':'no_clear_signal','category':'','findings':[]}
        return httpx.Response(200,request=httpx.Request('POST',url),json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(payload)}}]})
    html=(ROOT/'static/index.html').read_text();css=(ROOT/'static/styles.css').read_text();js=(ROOT/'static/app.js').read_text()
    html=re.sub(r'<link rel="stylesheet"[^>]+/>',lambda _: '<style>'+css+'</style>',html)
    html=re.sub(r'<script src="/static/app.js[^>]+></script>',lambda _: '<script>'+BOOT+'\n'+js+'</script>',html)
    with patch.dict(os.environ,{'GROQ_API_KEY':'test-not-real','SARVAM_API_KEY':'test-not-real'}),patch.object(cloud.httpx,'post',provider),sync_playwright() as p:
        path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
        browser=p.chromium.launch(executable_path=path,args=['--no-sandbox','--disable-dev-shm-usage']);page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(7000)
        page.expose_function('py_http',bridge);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html,wait_until='domcontentloaded');loc=page.locator
        expect(loc('#cloud-consent')).to_be_enabled();expect(loc('#cloud-consent')).not_to_be_checked()
        def analyze(text=None):
            if text is not None:loc('#message').fill(text)
            loc('#analyze-btn').click();expect(loc('#status')).to_contain_text('Analysis complete');expect(loc('#results')).to_be_visible()
        analyze('Your OTP is 482193. Do not share it with anyone.');expect(loc('#risk-level')).to_have_text('NO CLEAR SIGNAL');expect(loc('#safety-note')).to_be_visible();assert not providers
        loc('#copy-report').click();expect(loc('#status')).to_have_text('Safety summary copied.');assert 'does not prove' in page.evaluate('copied')
        page.evaluate('testCopyWorks=false');loc('#copy-report').click();expect(loc('#status')).to_contain_text('Copy failed');page.evaluate('testCopyWorks=true')
        loc('#copy-complaint').click();expect(loc('#status')).to_contain_text('Complaint draft copied');print('PASS: neutral warning, clipboard success and denied-copy feedback')
        analyze('Send your OTP immediately to claim your lottery prize.');expect(loc('#risk-level')).to_have_text('HIGH RISK');expect(loc('#listen-warning')).to_be_enabled();loc('#listen-warning').click();expect(loc('#stop-warning')).to_be_enabled();loc('#stop-warning').click();expect(loc('#stop-warning')).to_be_disabled()
        for value in ('none','link','credentials','money','app'):
            loc(f'input[name=rescue][value={value}]').check();assert loc('#rescue-steps li').count()>=3
        print('PASS: high-risk UI, warning play/stop controls, five rescue scenarios')
        loc('#cloud-consent').check();analyze();expect(loc('#analysis-mode')).to_contain_text('GPT-OSS 120B');assert providers[-1]==cloud.MODEL
        status['backup']=True;analyze();expect(loc('#analysis-mode')).to_contain_text('GPT-OSS 20B');assert providers[-1]==cloud.BACKUP_MODEL
        status['failure']=True;analyze();expect(loc('#analysis-mode')).to_contain_text('Local assessment only');status['failure']=False;status['backup']=False
        n=len(providers);page.evaluate("testOnline=false;dispatchEvent(new Event('offline'))");expect(loc('#cloud-consent')).to_be_disabled();analyze();assert len(providers)==n
        page.evaluate("testOnline=true;dispatchEvent(new Event('online'))");expect(loc('#cloud-consent')).to_be_enabled();assert len(providers)==n
        loc('#cloud-consent').uncheck();print('PASS: explicit cloud choice, mocked primary/backup/failure, offline transition without automatic requests')
        loc('#tab-image').click();loc('#image-input').set_input_files(str(ROOT/'demo_assets/demo_sms.png'));expect(loc('#status')).to_contain_text('Screenshot text extracted');expect(loc('#results')).not_to_be_visible();analyze();expect(loc('#risk-level')).to_have_text('HIGH RISK');print('PASS: real OCR upload, manual review and analysis')
        loc('#clear-btn').click();loc('#tab-voice').click();loc('#voice-btn').click();page.evaluate("()=>{const result=[{transcript:'Enter your UPI PIN to receive your refund immediately.'}];result.isFinal=true;testMic.onresult({resultIndex:0,results:[result]})}");loc('#voice-btn').click();expect(loc('#status')).to_contain_text('Transcription ended');analyze();expect(loc('#risk-level')).to_have_text('HIGH RISK');print('PASS: simulated microphone events, stop and review')
        loc('#clear-btn').click();loc('#tab-audio').click();loc('#audio-input').set_input_files(str(ROOT/'demo_assets/synthetic_call.wav'));expect(loc('#status')).to_contain_text('Recording selected');expect(loc('#transcribe-audio-btn')).to_be_disabled();loc('#audio-consent').check();loc('#transcribe-audio-btn').click();expect(loc('#status')).to_contain_text('Transcription complete');expect(loc('#results')).not_to_be_visible();assert providers[-1]=='sarvam';analyze();expect(loc('#risk-level')).to_have_text('HIGH RISK');print('PASS: actual WAV metadata and upload, mocked Sarvam transcription, manual analysis')
        for lang in ('en','hi','bn','kn','te','or','mr','ta','ml','gu','pa'):
            loc('#language').select_option(lang);analyze();expect(loc('#listen-warning')).to_be_enabled();expect(loc('#spoken-preview')).not_to_be_empty()
        loc('#clear-btn').click();expect(loc('#results')).not_to_be_visible();expect(loc('#message')).to_have_value('');assert not errors,errors
        print('PASS: all eleven response-language selections, voice availability and Clear; no uncaught JS errors')
        browser.close()
if __name__=='__main__':main_test()
