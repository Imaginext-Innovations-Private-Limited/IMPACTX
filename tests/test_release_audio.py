"""Release regressions. Cloud responses are mocked; no account or credits needed."""
import sys
from pathlib import Path
from types import SimpleNamespace
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from scamshield import main, voice
from scamshield.engine import analyze

client = TestClient(main.app)

def upload(duration='12', consent='true', lang='en', name='demo.mp3', data=b'fake recording', headers=None):
    return client.post('/api/transcribe-audio', params={'language':lang},
        data={'duration_seconds':duration,'consent':consent},
        files={'file':(name,data,'audio/mpeg')}, headers=headers or {})

@pytest.mark.parametrize('duration,consent,lang,name,data,expected', [
    ('12','false','en','demo.mp3',b'x',400),
    ('12','true','xx','demo.mp3',b'x',422),
    ('181','true','en','demo.mp3',b'x',413),
    ('0','true','en','demo.mp3',b'x',413),
    ('nan','true','en','demo.mp3',b'x',413),
    ('inf','true','en','demo.mp3',b'x',413),
    ('12','true','en','demo.txt',b'x',415),
    ('12','true','en','demo.mp3',b'',422),
    ('12','true','en','demo.mp3',b'x'*(20*1024*1024+1),413),
])
def test_audio_validation_no_cloud(monkeypatch,duration,consent,lang,name,data,expected):
    monkeypatch.setenv('SARVAM_API_KEY','test-key')
    monkeypatch.setattr(main,'_sarvam_short_transcribe',lambda *a:pytest.fail('unexpected network call'))
    monkeypatch.setattr(main,'_sarvam_batch_transcribe',lambda *a:pytest.fail('unexpected network call'))
    assert upload(duration,consent,lang,name,data).status_code==expected

def test_cross_site_audio_rejected(monkeypatch):
    monkeypatch.setenv('SARVAM_API_KEY','test-key')
    assert upload(headers={'Origin':'https://untrusted.example'}).status_code==403

def test_audio_requires_key(monkeypatch):
    monkeypatch.delenv('SARVAM_API_KEY',raising=False)
    assert upload().status_code==503

@pytest.mark.parametrize('lang,provider',[('en','en-IN'),('hi','hi-IN'),('bn','bn-IN'),('kn','kn-IN'),('te','te-IN'),('or','od-IN'),('mr','mr-IN')])
def test_short_audio_request(monkeypatch,lang,provider):
    monkeypatch.setenv('SARVAM_API_KEY','test-key')
    def post(url,**kw):
        assert url=='https://api.sarvam.ai/speech-to-text'
        assert kw['headers']['api-subscription-key']=='test-key'
        assert kw['data']=={'model':'saaras:v4','mode':'transcribe','language_code':provider}
        assert kw['files']['file'][1]==b'fake recording'
        return httpx.Response(200,json={'transcript':'Enter your UPI PIN to receive your refund immediately.'})
    monkeypatch.setattr(main.httpx,'post',post)
    monkeypatch.setattr(main,'_sarvam_batch_transcribe',lambda *a:pytest.fail('short clip went to batch'))
    response=upload(lang=lang)
    assert response.status_code==200
    assert response.json()['language_code']==provider
    assert analyze(response.json()['text'])['level']=='high'

def test_long_batch_workflow(monkeypatch):
    monkeypatch.setenv('SARVAM_API_KEY','test-key')
    state={}
    class Job:
        def upload_files(self,file_paths):
            state['source']=Path(file_paths[0]); assert state['source'].read_bytes()==b'fake recording'
        def start(self): state['started']=True
        def wait_until_complete(self,**kwargs): assert state['started']; assert kwargs['timeout']==180
        def get_file_results(self): return {'successful':[{'file_name':'recording.mp3'}],'failed':[]}
        def download_outputs(self,output_dir):
            Path(output_dir,'recording.mp3.json').write_text(json.dumps({'transcript':'Example transcript'}))
    def create_job(**kw):
        assert kw=={'model':'saaras:v4','mode':'transcribe','language_code':'mr-IN'}
        return Job()
    def make_client(**kw):
        assert kw['api_subscription_key']=='test-key'
        return SimpleNamespace(speech_to_text_job=SimpleNamespace(create_job=create_job))
    monkeypatch.setitem(sys.modules,'sarvamai',SimpleNamespace(SarvamAI=make_client))
    assert upload(duration='31',lang='mr').json()['text']=='Example transcript'
    assert not state['source'].exists()

@pytest.mark.parametrize('response,expected',[(httpx.Response(403,text='test-key private provider response'),502),(httpx.Response(200,json={'transcript':''}),422),(httpx.Response(200,json={'transcript':None}),422)])
def test_audio_provider_errors(monkeypatch,response,expected):
    monkeypatch.setenv('SARVAM_API_KEY','test-key')
    monkeypatch.setattr(main.httpx,'post',lambda *a,**kw:response)
    result=upload()
    assert result.status_code==expected
    assert 'test-key' not in result.text
    assert 'private provider response' not in result.text

def test_batch_timeout(monkeypatch):
    monkeypatch.setenv('SARVAM_API_KEY','test-key')
    def timeout(*a): raise TimeoutError('secret')
    monkeypatch.setattr(main,'_sarvam_batch_transcribe',timeout)
    assert upload(duration='60').status_code==504

def test_safety_education_and_real_request():
    assert analyze('Never enter your UPI PIN to receive money. Beware of fraud.')['level'] in {'review','no_clear_signal'}
    assert analyze('Never enter your UPI PIN to receive money. Enter your UPI PIN to receive your refund now.')['level']=='high'

def test_ui_consent_and_review():
    html=client.get('/').text
    assert 'id="audio-consent"' in html
    js=client.get('/static/app.js').text
    assert 'fd.append("consent","true")' in js
    assert 'Review and correct the text' in js
