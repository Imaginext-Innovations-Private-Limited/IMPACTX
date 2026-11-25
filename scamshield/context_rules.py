"""Local, explainable combinations of corroborating scam signals.

No network lookups, attachment execution or fraud probabilities. Evidence spans
refer to the original OCR/text input (line breaks are replaced one-for-one).
"""
import re

# Mask only the negated fee phrase, never the entire message. Keep offsets.
NEGATED_FEE = re.compile(
    r"\b(?:no\s+(?:(?:refundable|upfront|joining|registration|security|training|processing|onboarding|placement|advance)\s+){0,3}(?:fee|deposit|charge|payment)\b(?:\s+is\s+required)?|"
    r"(?:(?:refundable|upfront|joining|registration|security|training|processing|onboarding|placement|advance)\s+){1,3}(?:fee|deposit|charge|payment)\s+(?:is\s+)?not\s+required|"
    r"(?:do\s+not|don't|never|not\s+required\s+to|no\s+need\s+to)\s+(?:pay|deposit|transfer|send)\s+(?:(?:any|a|an|the|your|refundable|upfront|joining|registration|security|training|processing|onboarding|placement|advance)\s+){0,5}(?:fee|deposit|charge|payment))\b", re.I)


def mask_negated_fees(text):
    return NEGATED_FEE.sub(lambda m: ' ' * len(m.group()), text)


def contextual_findings(text, is_official):
    """Return bounded-context findings; a single generic keyword is insufficient."""
    found = []
    # A bare domain is accepted only when paired with the relevant request.
    link = re.compile(r'(?:https?://\s*|www\.)?(?P<host>[a-z0-9][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*)+)(?:\s*/[^\s]*)?', re.I)
    def add(code, title, weight, category, explanation, advice, patterns, external=False):
        anchor, *others = patterns
        scan = mask_negated_fees(text) if code in {'job_fee_context','job_deposit_context','loan_fee_context'} else text
        if code == 'investment_context':
            scan = re.sub(r'\b(?:no|not\s+a|not)\s+risk[ -]free\b', lambda m: ' '*len(m.group()), scan, flags=re.I)
        for a in re.finditer(anchor, scan, re.I):
            # Restrict combinations to one nearby message-sized window, not the whole transcript.
            lo, hi = max(0,a.start()-160), min(len(text),a.end()+360)
            window = scan[lo:hi]
            matches = [re.search(p, window, re.I) for p in others]
            if any(m is None for m in matches):
                continue
            if external:
                candidates = [m for m in link.finditer(window)
                              if not is_official(m['host'].lower())
                              and (m['host'].lower().split('.')[-1].isalpha())
                              and (m.group().lower().startswith(('http://','https://','www.')) or '/' in m.group()
                                   or (not m['host'].lower().endswith(('.zip','.rar','.apk','.exe','.pdf','.docx','.png','.jpg','.txt'))
                                       and re.search(r'\b(?:at|visit|via|link|website|site|to)\s*[:=]?\s*$', window[max(0,m.start()-35):m.start()], re.I)))
                              and (m.start()==0 or window[m.start()-1] != '@')]
                if not candidates:
                    continue
                matches.append(candidates[0])
            start = min([a.start()] + [lo+m.start() for m in matches])
            end = max([a.end()] + [lo+m.end() for m in matches])
            found.append(dict(id=code,title=title,weight=weight,explanation=explanation,
                              advice=advice,evidence=text[start:end][:160],start=start,end=end,_category=category))
            break

    add('utility_context','Utility cutoff threat with a callback request',7,'Utility scam',
        'An alleged overdue utility bill, a timed cutoff and a number supplied in the message create a strong impersonation risk.',
        'Do not call or pay using the message. Check the bill in the utility provider’s official app or on its published number.',
        [r'\b(?:electricity|power\s+supply|electric\s+meter|gas\s+supply|water\s+supply|utility)\b',
         r'\b(?:disconnect(?:ed|ion)?|cut\s*off|susp[\s,.-]*ended|suspend(?:ed)?|blocked|deactivated)\b',
         r'\b(?:today|tonight|within\s+\d+\s+hours?|\d{1,2}[:.]\d{2}\s*(?:am|pm)|\d{1,2}\s*(?:am|pm))\b',
         r'\b(?:bill|dues?|outstanding|arrears|unpaid)\b',
         r'\b(?:call|contact|cntct|contct|whatsapp)\b.{0,35}(?:\+?91[ -]?)?[6-9]\d{9}\b'])
    add('delivery_context','Delivery address request through an unverified website',7,'Delivery phishing',
        'A parcel problem, an address-update request, a return deadline and a non-official-looking link together indicate possible delivery phishing.',
        'Do not enter address or payment details through the message. Track the parcel using the courier’s official website or app.',
        [r'\b(?:india\s*post|postal|courier|parcel|package|shipment|delivery)\b',
         r'\b(?:update|confirm|correct|verify|complete|submit|provide)\b.{0,45}\b(?:address|(?:shipping|delivery|your)\s+details|house\s+number|postcode|postal\s+code)\b',
         r'\b(?:returned|return\s+to\s+sender|failed\s+delivery|unable\s+to\s+deliver|could\s+not\s+be\s+delivered|incomplete\s+address|missing\s+address|within\s+\d+\s+hours?|cancel(?:led|lation)|delivery\s+failed)\b'],external=True)
    add('government_apk_context','Official-looking traffic fine asks for an APK',3,'Malware / remote access',
        'A traffic enforcement claim directing the recipient to an attached Android app is especially risky. The actual file has not been scanned.',
        'Do not install the APK. Independently check any fine through the official government e-challan service.',
        [r'\b(?:e[ -]?challan|traffic\s+(?:fine|challan|police)|regional\s+transport\s+office|rto)\b',
         r'\b(?:install|download|access|open|use)\b.{0,95}\b(?:app|application|apk)\b',
         r'\.\s*apk\b'])
    add('job_fee_context','Recruitment offer demands an advance payment',7,'Job / task scam',
        'An employment offer combined with an instruction to pay before getting the job is a strong advance-fee warning sign.',
        'Do not pay a recruitment deposit or upfront fee. Verify the employer through its independently found careers page.',
        [r'\b(?:recruitment|recruiter|job|employment|vacancy|hiring|interview)\b',
         r'(?<!not\s)(?<!never\s)(?<!to\s)\b(?:pay|deposit|transfer|send)\s+(?:(?:the|an?|your|a\s+refundable)\s+)?(?:up[ -]?front|joining|registration|placement|processing|training|security|advance)\s+(?:fee|fees|deposit|charge|payment|amount)\b'])
    add('job_offer_context','Easy-income recruitment offer',3,'Job / task scam',
        'An unsolicited-looking job offer with easy or flexible earnings and a monetary range deserves verification even if no fee is requested yet.',
        'Verify the recruiter using the employer’s official careers page. Do not pay deposits or share financial information.',
        [r'\b(?:offer\s+you|recruitment|recruiter|hiring|job\s+offer)\b',
         r'\b(?:part\s*-?\s*time\s+job|work(?:ing)?\s+from\s+home|simple\s+job|free\s+time)\b',
         r'\b(?:earn|income|make)\s+(?:rs\.?\s*|inr\s*|₹\s*)?\d[\d,]*\s*[-–]\s*\d[\d,]*(?:k)?\b'])
    add('reward_context','Bank reward expiry with an unverified update link',4,'Bank reward phishing',
        'A card reward claim combined with expiry pressure and a link outside known official domains suggests phishing.',
        'Do not redeem rewards through the message. Check points and offers in the bank’s official app.',
        [r'\b(?:bank|card\s+user|credit\s+card|debit\s+card|axis\s+card|sbi\s+card)\b',
         r'\b(?:cash\s+points|reward\s+points|loyalty\s+points|rewards?|cashback)\b',
         r'\b(?:expire(?:s|d)?|expiring|lapse|last\s+chance)\b',
         r'\b(?:update|claim|redeem|activate|verify|visit)\b'],external=True)
    add('job_deposit_context','Job or appointment offer conditional on a deposit',7,'Job / task scam',
        'An employment opportunity tied to a required fee before joining or receiving an offer is a strong advance-fee indicator.',
        'Do not pay to secure a job. Confirm the recruiter and any stated fee through an independently found employer contact.',
        [r'\b(?:job|work[ -]from[ -]home|employment|recruitment|position|vacancy|hiring|appointment\s+letter|offer\s+letter|shortlisted)\b',
         r'\b(?:security|refundable|joining|registration|placement|training|processing|advance|up[ -]?front|onboarding)\s+(?:fee|deposit|charge|payment|amount)\b',
         r'\b(?:required\s+before|mandatory|must\s+(?:be\s+paid|pay|deposit|transfer|send)|(?:pay|transfer|deposit|send)\b.{0,75}\b(?:before|to\s+secure|to\s+confirm|to\s+release)|before\b.{0,65}\b(?:issued|joining|appointment|offer|start)|(?:fee|deposit|charge)\b.{0,55}\b(?:is\s+required|is\s+mandatory))\b'])
    add('investment_context','Investment promise of guaranteed or risk-free returns',7,'Investment scam',
        'An investment solicitation promising guaranteed or unusually frequent returns with an activation or payment request is a strong warning sign.',
        'Do not send investment funds on the basis of a guaranteed-return claim. Independently verify the provider and its regulatory status.',
        [r'\b(?:investment|invest(?:ing)?|trading|crypto(?:currency)?|profit\s+plan)\b',
         r'\b(?:guaranteed\s+(?:returns?|profits?|income|earnings?)|(?:zero|no|without)\s+risk|risk[ -]free|assured\s+(?:returns?|profits?))\b',
         r'\b(?:every\s+day|per\s+day|daily|weekly|double\s+your\s+money|(?:zero|no|without)\s+risk|risk[ -]free)\b',
         r'\b(?:contact|activation|activate|deposit|transfer|send\s+money|earn|generate|double\s+your\s+money)\b'])
    add('family_context','New-number impersonation with an urgent money request',7,'Family impersonation',
        'An apparent family member using a new number, asking for money and discouraging contact through the previous number is a strong impersonation warning.',
        'Do not send money yet. Call the family member on their previously known number or verify through another trusted person.',
        [r'\b(?:new\s+(?:phone\s+)?number|different\s+number|naya\s+number|nayi\s+number|number\s+badal\s+gaya)\b',
         r'\b(?:mum|mom|mother|dad|father|son|daughter|maa|mummy|papa|beta|bete|bhai|didi|sister|brother)\b',
         r'(?:₹\s*\d|\b(?:rs\.?|inr)\s*\d|\b(?:money|cash|paise|paisa|rupaye|rupees)\b)',
         r'\b(?:don.t\s+call|do\s+not\s+call|can.t\s+call|cannot\s+call|call\s+mat\s+kar(?:na|o|en)?|purane\s+number\b.{0,25}\bmat)\b'])
    add('family_request_context','New-number message asks a relative for urgent money',3,'Family impersonation',
        'A money request from a new number could be genuine or an impersonation attempt. Verify the person before paying.',
        'Call the person using a previously known number or check with a trusted family member.',
        [r'\b(?:new\s+(?:phone\s+)?number|different\s+number|naya\s+number|nayi\s+number)\b',
         r'\b(?:mum|mom|mother|dad|father|son|daughter|maa|mummy|papa|beta|bete|bhai|didi|sister|brother)\b',
         r'(?:₹\s*\d|\b(?:rs\.?|inr)\s*\d|\b(?:money|cash|paise|paisa|rupaye|rupees)\b)',
         r'\b(?:abhi\b.{0,30}\bchahiye|urgent(?:ly)?|emergency|need\b.{0,35}\b(?:now|today|asap))\b'])
    add('loan_fee_context','Loan release conditional on an advance fee',7,'Advance-fee loan scam',
        'A loan promise with a separate payment to release funds, especially to an agent or described as refundable, is a strong advance-fee warning.',
        'Do not transfer a release fee to an agent. Verify the lender and any disclosed charges independently through its official channels.',
        [r'\b(?:loan|credit\s+facility|personal\s+finance|lending)\b',
         r'\b(?:processing|refundable|advance|up[ -]?front|release|verification|security|insurance)\s+(?:fee|charge|deposit|payment|amount)\b',
         r'\b(?:before\s+(?:disbursement|release|funds|credit)|to\s+(?:release|unlock|disburse|activate)|(?:loan|funds)\s+will\s+be\s+(?:released|credited))\b',
         r'\b(?:transfer|send|pay|deposit|remit)\b',
         r'\b(?:agent|personal\s+account|refundable|wallet|upi\s+id|advance)\b'])
    add('bn_bank_credential_context','Bank account threat combined with an OTP request (Bangla)',7,'Credential theft',
        'A bank-account restriction claim combined with a request to reveal a secret code is a strong credential-theft warning.',
        'Never disclose an OTP or PIN. Check your account through the bank’s official app or independently found number.',
        [r'(?:ব্যাংক|ব্যাঙ্ক|অ্যাকাউন্ট|একাউন্ট|খাতা)',
         r'(?:বন্ধ|ব্লক|স্থগিত|নিষ্ক্রিয়).{0,30}(?:হবে|যাবে|করা হবে|করে দেব)',
         r'(?:ওটিপি|ও\s*টি\s*পি|পিন|\bOTP\b).{0,45}(?:জানান|বলুন|পাঠান|শেয়ার\s*করুন)(?!\s*না)'])
    if any(f['id']=='job_fee_context' for f in found):
        found = [f for f in found if f['id'] != 'job_deposit_context']
    if any(f['id']=='family_context' for f in found):
        found = [f for f in found if f['id'] != 'family_request_context']
    return found
