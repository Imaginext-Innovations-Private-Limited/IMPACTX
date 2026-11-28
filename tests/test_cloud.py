import json
import httpx
import pytest
from fastapi.testclient import TestClient
from scamshield import cloud
from scamshield.main import app

client = TestClient(app)
TEXT = 'Please send funds for an unfamiliar administrative service.'

def payload(level='high', evidence='send funds', category='Payment solicitation'):
    return {'level':level, 'category':category, 'findings':[{'title':'Payment demand', 'evidence':evidence, 'explanation':'The sender requests money.'}] if level in {'high','review','caution'} else []}

@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','fake-test-key')
    calls=[]
    def install(data=None, status=200, finish='stop'):
        def post(url, **kwargs):
            calls.append((url, kwargs))
            return httpx.Response(status, request=httpx.Request('POST',url), json={'choices':[{'finish_reason':finish,'message':{'content':json.dumps(data)}}]})
        monkeypatch.setattr(cloud.httpx,'post',post)
        return calls
    return install

def scan(text=TEXT, **kwargs):
    return client.post('/api/analyze',json={'text':text,'cloud_consent':True, **kwargs}).json()

def test_default_does_not_call_provider(provider):
    calls=provider(payload())
    result=client.post('/api/analyze',json={'text':TEXT}).json()
    assert result['analysis_mode']=='offline' and not calls

def test_valid_cloud_and_schema(provider):
    calls=provider(payload())
    result=scan()
    assert result['analysis_mode']=='hybrid' and result['level']=='high'
    assert result['indicators'][0]['evidence']=='send funds'
    assert result['score']==8 and result['voice_context']
    assert 'Payment solicitation' in result['complaint']
    url, kwargs=calls[0]
    assert url==cloud.URL and kwargs['json']['model']==cloud.MODEL
    assert kwargs['json']['response_format']['json_schema']['strict'] is True
    assert 'tools' not in kwargs['json'] and 'UNTRUSTED' in kwargs['json']['messages'][0]['content']
    assert kwargs['follow_redirects'] is False

@pytest.mark.parametrize('status',[401,429,500])
def test_http_failure_falls_back(provider,status):
    provider({},status=status)
    result=scan()
    assert result['analysis_mode']=='offline_fallback' and str(status) in result['analysis_note']
    assert 'fake-test-key' not in str(result)

@pytest.mark.parametrize('data',[payload(evidence='invented urgency'),payload(evidence=''),{'level':'high','category':'x','findings':[]},{'level':'safe','category':'','findings':[]},None])
def test_reject_invalid_model_output(provider,data):
    provider(data)
    assert scan()['analysis_mode']=='offline_fallback'

def test_truncated_falls_back(provider):
    provider(payload(),finish='length')
    assert scan()['analysis_mode']=='offline_fallback'

def test_high_local_cannot_be_downgraded(provider):
    provider(payload('no_clear_signal',category=''))
    result=scan('Enter your UPI PIN to receive your cashback refund immediately')
    assert result['level']=='high' and result['analysis_mode']=='hybrid'
    assert 'Conservative warning retained' in result['analysis_note']
    assert 'offline: high' not in result['analysis_note']

def test_missing_key(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    assert scan()['analysis_mode']=='offline_fallback'

def test_cross_site_rejected(provider):
    calls=provider(payload())
    r=client.post('/api/analyze',json={'text':TEXT,'cloud_consent':True},headers={'origin':'https://evil.example'})
    assert r.status_code==403 and not calls

def test_redaction_before_transmission(provider):
    calls=provider(payload(evidence='send funds'))
    scan(TEXT+' OTP 123456, +91 9876543210, hello@example.com, https://example.org/path?token=secret')
    sent=calls[0][1]['json']['messages'][1]['content']
    for secret in ('123456','9876543210','hello@example.com','token=secret'):
        assert secret not in sent
    assert 'example.org' in sent

@pytest.mark.parametrize('lang',['en','hi','bn','kn','te','or','mr'])
def test_output_language(provider,lang):
    calls=provider(payload())
    result=scan(language=lang)
    assert result['language']==lang and result['level']=='high'
    sent=json.loads(calls[0][1]['json']['messages'][1]['content'])
    assert sent['output_language']==cloud.LANGUAGE_NAMES[lang][0]

def test_timeout(provider,monkeypatch):
    provider(payload())
    def timeout(*a,**k): raise httpx.ReadTimeout('private error')
    monkeypatch.setattr(cloud.httpx,'post',timeout)
    result=scan()
    assert result['analysis_mode']=='offline_fallback' and 'private error' not in str(result)


@pytest.mark.parametrize('failure', [500, 503, 429, 422, 'invalid', 'truncated', 'timeout'])
def test_backup_recovers_eligible_failure(monkeypatch, failure):
    monkeypatch.setenv('GROQ_API_KEY','fake-test-key')
    calls=[]
    def post(url, **kwargs):
        model=kwargs['json']['model']; calls.append(model)
        if len(calls)==1:
            if failure=='timeout':
                raise httpx.ReadTimeout('PRIVATE EXCEPTION')
            status=failure if isinstance(failure,int) else 200
            data=payload(evidence='invented') if failure=='invalid' else payload()
            finish='length' if failure=='truncated' else 'stop'
        else:
            status=200; data=payload(); finish='stop'
        return httpx.Response(status, request=httpx.Request('POST',url),json={'choices':[{'finish_reason':finish,'message':{'content':json.dumps(data)}}]})
    monkeypatch.setattr(cloud.httpx,'post',post)
    result=scan()
    assert calls==[cloud.MODEL,cloud.BACKUP_MODEL]
    assert result['analysis_mode']=='hybrid' and result['analysis_model']==cloud.BACKUP_MODEL
    assert result['level']=='high' and 'GPT-OSS 20B' in result['analysis_note']
    assert 'PRIVATE EXCEPTION' not in str(result)


@pytest.mark.parametrize('status',[400,401,403,429])
def test_no_retry_for_auth_bad_request_or_cooldown(monkeypatch,status):
    monkeypatch.setenv('GROQ_API_KEY','fake-test-key')
    calls=[]
    def post(url,**kwargs):
        calls.append(kwargs['json']['model'])
        return httpx.Response(status,request=httpx.Request('POST',url),headers={'retry-after':'60'} if status==429 else {},json={'error':'PRIVATE PROVIDER TEXT'})
    monkeypatch.setattr(cloud.httpx,'post',post)
    result=scan()
    assert calls==[cloud.MODEL] and result['analysis_mode']=='offline_fallback'
    assert str(status) in result['analysis_note'] and 'PRIVATE PROVIDER TEXT' not in str(result)


def test_both_invalid_responses_fail_closed(provider,caplog):
    calls=provider(payload(evidence='PRIVATE INVENTED EVIDENCE'))
    result=scan()
    assert len(calls)==2 and result['analysis_mode']=='offline_fallback'
    assert 'response failed validation' in result['analysis_note']
    assert 'PRIVATE INVENTED EVIDENCE' not in caplog.text
    assert 'fake-test-key' not in caplog.text


def test_offline_connection_failure_does_not_repeat(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','fake-test-key')
    calls=[]
    def post(url, **kwargs):
        calls.append(kwargs['json']['model']); raise httpx.ConnectError('PRIVATE ERROR')
    monkeypatch.setattr(cloud.httpx,'post',post)
    result=scan()
    assert calls==[cloud.MODEL] and result['analysis_mode']=='offline_fallback'
    assert 'connection unavailable' in result['analysis_note']


def test_primary_success_does_not_use_backup(provider):
    calls=provider(payload())
    result=scan()
    assert len(calls)==1 and result['analysis_model']==cloud.MODEL
