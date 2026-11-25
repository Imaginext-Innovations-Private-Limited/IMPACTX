"""Development regressions from the user's synthetic round; not holdout accuracy."""
import pytest
from scamshield.engine import analyze

ROUND = [
('Your electricity bill for November is available. Please view your outstanding balance through your electricity provider\'s official app. Ignore this message if already paid.', 'no_clear_signal'),
('We have shortlisted your profile for a work-from-home position. A refundable security deposit of ₹1,499 is required before your appointment letter can be issued.', 'high'),
('Your shipment could not be delivered because the house number is missing. Confirm your details at delivery-check.example within 12 hours to prevent cancellation.', 'high'),
('Cybercrime awareness reminder: Police will never place you under digital arrest or demand money to avoid imprisonment. Never share your OTP.', 'no_clear_signal'),
('Congratulations! Your investment of ₹5,000 can generate ₹1,200 every day with guaranteed returns and zero risk. Contact our investment manager for activation.', 'high'),
('Your credit card ending in 1234 has outstanding dues of ₹2,450. Please review your statement in your official banking app.', 'no_clear_signal'),
('Hi, this is your college placement coordinator. Tomorrow\'s interview has been rescheduled to 10 AM. Bring your resume and college ID.', 'no_clear_signal'),
('Your mobile number will be permanently disconnected tonight because your identity verification is incomplete. Install the verification APK sent with this message.', 'high'),
('Maa, mera phone kharab ho gaya hai. Ye mera naya number hai. Mujhe abhi ₹8,000 chahiye. Purane number par call mat karna.', 'high'),
('Your refund has been approved. Scan the QR code sent by our representative and enter your UPI PIN to receive the amount.', 'high'),
('Please forward the project_backup.zip file to our professor for tomorrow\'s presentation. It contains our source code and documentation.', 'no_clear_signal'),
('Your bank reward points expire tonight. Redeem them by entering your card details at rewards-claim.example.', 'high'),
('Please pay ₹250 for tomorrow\'s college event registration. The payment details are available on the official college notice board.', 'no_clear_signal'),
('আপনার ব্যাংক অ্যাকাউন্ট বন্ধ হয়ে যাবে। অ্যাকাউন্ট চালু রাখতে এখনই আপনার ওটিপি আমাদের জানান।', 'high'),
('Your loan application has been approved. Before disbursement, transfer ₹3,500 as a refundable processing charge to our agent.', 'high'),
]

@pytest.mark.parametrize('message,expected', ROUND)
def test_reported_round(message, expected):
    d=analyze(message)
    assert d['level']==expected, (d['level'],d['score'],[i['id'] for i in d['indicators']])

@pytest.mark.parametrize('message,indicator', [
('Employment offer: a refundable onboarding deposit is mandatory before you start.', 'job_deposit_context'),
('Courier delivery failed. Provide your postal code at parcel-review.example to arrange another attempt.', 'delivery_context'),
('Our trading plan promises assured profits with zero risk. Contact the agent to activate your account.', 'investment_context'),
('Dad, this is my new phone number. I need money urgently. Please do not call the old number.', 'family_context'),
('Your credit card loyalty points are expiring. Claim them at points-check.example.', 'reward_context'),
('Personal loan approved. Pay a release fee to our agent to unlock the funds.', 'loan_fee_context'),
('আপনার ব্যাংক অ্যাকাউন্ট ব্লক হবে। আপনার ওটিপি আমাদের বলুন।', 'bn_bank_credential_context'),
])
def test_wording_variants(message,indicator):
    d=analyze(message)
    assert d['level']=='high', (d['level'], d['indicators'])
    assert indicator in {i['id'] for i in d['indicators']}
    for i in d['indicators']:
        assert 0<=i['start']<i['end']<=len(message)

@pytest.mark.parametrize('message', [
'Job offer: no joining fee is required. The appointment letter will be issued after the interview.',
'For the vacancy, do not pay any security deposit before joining.',
'Your employment offer is ready. A refundable security deposit is not required before joining.',
'Your parcel address is incomplete. Confirm your delivery address at www.indiapost.gov.in within 24 hours.',
'Your parcel delivery failed. Contact the carrier through its official app.',
'Investment returns are not guaranteed; there is no risk-free investment. Read the official risk disclosure.',
'Your bank offers a fixed deposit with guaranteed returns. Contact our investment manager to learn more.',
'Mom, this is my new number. Please save it and call me on the old number to confirm.',
'Your bank reward points expire today. Redeem them at www.axisbank.com.',
'Loan processing fee details are available in the official bank app. No payment to any agent is required.',
'Police will never place you under digital arrest. Never share your OTP.',
'আপনার ব্যাংক অ্যাকাউন্টের ওটিপি কাউকে বলবেন না।',
])
def test_benign_contrast(message):
    d=analyze(message)
    assert d['level'] in {'no_clear_signal','review'}, (d['level'], d['indicators'])

@pytest.mark.parametrize('message', [
'Scam alert: never share your OTP. Please send your OTP to our verification desk immediately.',
'Never share your OTP. Your shipment could not be delivered. Confirm your address at delivery-check.example within 12 hours.',
])
def test_safety_text_not_blanket_exemption(message):
    assert analyze(message)['level']=='high'


def test_family_urgent_request_without_avoidance_is_caution():
    d=analyze('Mum, this is my new number. I need money urgently for hospital.')
    assert d['level']=='caution'
    assert 'family_request_context' in {i['id'] for i in d['indicators']}

def test_negated_job_fee_does_not_hide_second_demand():
    d=analyze('No joining fee is required, but pay a refundable security deposit before your job starts.')
    assert d['level']=='high'
