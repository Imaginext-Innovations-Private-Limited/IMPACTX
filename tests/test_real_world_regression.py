"""Regression checks for observed failures; not a real-world accuracy benchmark."""
import pytest
from fastapi.testclient import TestClient
from scamshield.main import app
from scamshield.engine import analyze

WRAPPED = ('Dear Customer your Icici\nbank Accounts KYC has\nbeen suspended please\n'
           'update your KYC click in link\nand activate your icici bank\nAccounts https://is.gd/\nexample')
ATTACHMENT = ('Attachment: document.zip\nPlease isko apni company ke finance manager ko '
              'verification ke liye forward kar dijiye. Please ise computer par open kijiye.')

@pytest.mark.parametrize('text', [WRAPPED, WRAPPED.replace('\n',' '), WRAPPED.replace('\n','\r\n'),
    'Your KYC has been suspended. Click on the link https://is.gd/example to update your bank account.'])
@pytest.mark.parametrize('channel', ['image','sms'])
def test_kyc_wrapping_and_short_link(text, channel):
    d=analyze(text, channel=channel)
    assert d['level']=='high'
    assert {'kyc','url_shortener','unverified_link','kyc_short_link_combo'} <= {i['id'] for i in d['indicators']}
    assert d['voice_context']['topic']=='kyc'
    for i in d['indicators']:
        assert 0 <= i['start'] < i['end'] <= len(text)

@pytest.mark.parametrize('text', [ATTACHMENT, 'Unknown sender: invoice.zip. Please open the file on your computer.',
 'Please forward invoice.rar to the finance department and open it on a PC for verification.'])
def test_suspicious_attachment(text):
    d=analyze(text, channel='whatsapp')
    assert d['level'] in {'caution','high'}
    assert 'attachment_context' in {i['id'] for i in d['indicators']}
    assert 'Do not open or forward' in d['actions'][0]

@pytest.mark.parametrize('text', [
 'Here is our college project.zip. Please open it on your computer.',
 'Please forward the monthly invoice.zip to the finance manager.',
 'Please open the report.zip for our team meeting.',
 'Your KYC is due. Please visit your nearest branch with ID proof.',
 'Here is the class survey: https://is.gd/example',
 'Your KYC is due. Open the official app to check your details.',
 'Your account has been debited by INR 500 for a UPI transaction.',
 'Your OTP is\n482913. Do not share your OTP with anyone.'])
def test_no_unnecessary_escalation(text):
    assert analyze(text)['level'] in {'no_clear_signal','review'}

def test_wrapped_otp_not_exposed():
    d=analyze('Share OTP\n482913 with our verification desk immediately.')
    assert d['level']=='high'
    assert '482913' not in str(d['indicators'])
    assert '482913' not in d['complaint']

def test_analysis_endpoint():
    d=TestClient(app).post('/api/analyze',json={'text':WRAPPED,'channel':'image','language':'en'})
    assert d.status_code==200 and d.json()['level']=='high'

def test_attachment_ocr_split_extension():
    text=('Phone number from India. Not a contact.\n20261111094727.4620\nB ATC zip &\n'
          'Please isko apni company ke finance manager ko verification ke liye forward kar dijye. '
          'Please ise cormputer per open Kiva')
    d=analyze(text,channel='image')
    assert d['level']=='caution'
    assert 'attachment_context' in {i['id'] for i in d['indicators']}

def test_attachment_ocr_benign_archive():
    assert analyze('class notes zip\nPlease open on your computer before our class.',channel='image')['level']=='no_clear_signal'


# Reproduces the Windows OCR output supplied during the live retest.
WINDOWS_OCR = ('a _lClcrhrUC*S\n+o jem\n>hone number from India + Not @ contact « No\n'
               'common groups\n© Safety tools\n© Block & Add\n|\n=== eo\nSaget 4\n2:15 pm\n'
               '20261111094727.4620\nB DA7Czip &\nPlease isko apni company ke &\n'
               'finance manager ko verification ke\nliye forward kar dijye. Please ise\n'
               'coriputer per open Kiva ”')

@pytest.mark.parametrize('text', [WINDOWS_OCR, WINDOWS_OCR.replace('DA7Czip', 'report42RAR'),
                                  WINDOWS_OCR.replace('DA7Czip', 'DA7C.zip')])
def test_ocr_attachment_missing_dot(text):
    d = analyze(text, channel='image')
    assert d['level'] == 'caution'
    finding = next(i for i in d['indicators'] if i['id'] == 'attachment_context')
    assert 0 <= finding['start'] < finding['end'] <= len(text)
    assert 'Do not open or forward' in d['actions'][0]

@pytest.mark.parametrize('text', [
    'AB7Czip here are our college notes. Please open them on your computer.',
    'Please forward report42zip to the finance manager for verification.',
    'Please open report42zip for verification with the finance team.',
    'Please forward the document to the finance manager for verification and open it.',
    'Use a zip code to verify the address.',
])
def test_ocr_joined_attachment_requires_context(text):
    d = analyze(text, channel='image')
    assert 'attachment_context' not in {i['id'] for i in d['indicators']}


def test_ocr_joined_attachment_endpoint():
    d = TestClient(app).post('/api/analyze', json={'text': WINDOWS_OCR, 'channel': 'image', 'language': 'en'})
    assert d.status_code == 200 and d.json()['level'] == 'caution'
