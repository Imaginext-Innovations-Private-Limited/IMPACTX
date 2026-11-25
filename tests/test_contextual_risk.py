"""Regression and contrast cases, not an independent accuracy benchmark.

Reported screenshot wording is reproduced with neutral placeholder contacts/URLs.
"""
import pytest
from fastapi.testclient import TestClient
from scamshield.main import app
from scamshield.engine import analyze

CASES = [
    ('Dear Sir.\nYour Power supply meter\nconnection wili be\nsusp,ended 07.15 pm Due\nTO nOt complete last bill\nCntct Office 9000000000', 'utility_context', 'high'),
    ('Electricity connection will be cut off tonight due to outstanding bill. Contact our office 9000000000', 'utility_context', 'high'),
    ('India Post: Your package has arrived at the warehouse. Please update your address details within 48 hours, otherwise your package will be returned. Please update the address in the link:https://\nparcel-check.example/abc', 'delivery_context', 'high'),
    ('Courier shipment: incomplete address. Confirm the delivery address within 24 hours at https://\naddress-check.example/track', 'delivery_context', 'high'),
    ('Challan No: 123. To verify and view evidence please access the E-Challan (RTO) Details mobile application. Regional Transport Office (RTO). E-Challan Details (RTO).apk', 'government_apk_context', 'high'),
    ('Indian Traffic Police: traffic challan issued. Please install the traffic Challan (RTO) app. Challan.apk', 'government_apk_context', 'high'),
    ('Traffic fine: download this application. details. apk', 'government_apk_context', 'high'),
    ('Recruitment online part - time job, you can earn 500- 6000 rupees per day, please click the link. Pay the upfront fee and get the job!', 'job_fee_context', 'high'),
    ('Job offer: deposit a refundable training fee to confirm the position.', 'job_fee_context', 'high'),
    ('Would like to offer you a part-time job. You are not required to pay any joining fee. You can earn 150-5000 in your free time.', 'job_offer_context', 'caution'),
    ('Dear AXIS CARD USER. Your ORDER CASH POINTS 7800 EXPIRE TODAY is pending due to wrong SHIPPING ADD. Visit for update rewards-check.site/ax', 'reward_context', 'high'),
    ('Credit card reward points expire today. Redeem your rewards at https://rewards-check.example/claim', 'reward_context', 'high'),
]

@pytest.mark.parametrize('message,indicator,level', CASES)
def test_contextual_combinations(message, indicator, level):
    d = analyze(message, channel='image')
    assert d['level'] == level, d
    item = next(i for i in d['indicators'] if i['id'] == indicator)
    assert 0 <= item['start'] < item['end'] <= len(message)
    assert item['explanation'] and item['advice']
    assert d['actions'][0] != ''

@pytest.mark.parametrize('message', [
    'Your electricity bill is due on Friday. Pay in the official provider app.',
    'Scheduled electricity outage tonight from 7 pm for maintenance. No payment required.',
    'Your package has been delivered. Thank you.',
    'India Post: please update your address within 48 hours at https://www.indiapost.gov.in/track',
    'Traffic challan issued. Check the fine at https://echallan.parivahan.gov.in/ and use the official app.',
    'Our Android team built a test app. Install debug.apk on the development device.',
    'The college has a part-time job opening at the library. Apply through the placement office.',
    'For this job you are not required to pay any joining fee.',
    'Recruitment notice: do not pay the upfront fee requested by fake recruiters.',
    'Your credit card reward points expire today. Redeem in the official banking app.',
    'Your credit card rewards expire today. Redeem at https://www.axisbank.com/rewards',
])
def test_contextual_negative_controls(message):
    d = analyze(message, channel='image')
    assert d['level'] != 'high', d
    assert not any(i['id'] in {'utility_context','delivery_context','government_apk_context','job_fee_context','job_offer_context','reward_context'} for i in d['indicators']), d

@pytest.mark.parametrize('message,indicator,level', CASES[:1]+CASES[2:3]+CASES[4:5]+CASES[7:8]+CASES[10:11])
def test_contextual_api(message, indicator, level):
    d=TestClient(app).post('/api/analyze',json={'text':message,'channel':'image','language':'en'})
    assert d.status_code == 200
    assert d.json()['level'] == level
    assert indicator in {i['id'] for i in d.json()['indicators']}

@pytest.mark.parametrize('language',['hi','bn','kn','te','or','mr'])
def test_new_findings_localize_without_invented_translations(language):
    d=analyze(CASES[0][0],channel='image',language=language)
    assert d['level']=='high' and d['voice_context']['text']
    item=next(i for i in d['indicators'] if i['id']=='utility_context')
    assert item['indicator_language']=='en'
