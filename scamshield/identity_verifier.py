"""Offline email (.eml / plain text) parsing and identity verification.

Extracts sender, Reply-To, claimed organisations, hyperlink destinations,
and unverified authentication header claims (SPF/DKIM/DMARC).
Never renders active HTML or fetches remote resources.
"""
from __future__ import annotations

import email
import email.policy
import re
import unicodedata
from email.utils import parseaddr
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

from .url_classifier import registered_domain

# Curated organisation-to-official-domain registry (authoritative public domains).
# An official-domain match is NOT independent proof of sender authentication.
ORG_DOMAIN_REGISTRY: dict[str, dict[str, Any]] = {
    "State Bank of India": {
        "aliases": ("state bank of india", "sbi", "onlinesbi", "yono sbi"),
        "domains": {"sbi.co.in", "onlinesbi.sbi", "onlinesbi.com", "sbi.bank.in"},
        "source": "Reserve Bank of India / SBI official portal",
    },
    "HDFC Bank": {
        "aliases": ("hdfc bank", "hdfc"),
        "domains": {"hdfcbank.com", "hdfcbank.net"},
        "source": "HDFC Bank official website",
    },
    "ICICI Bank": {
        "aliases": ("icici bank", "icici"),
        "domains": {"icicibank.com"},
        "source": "ICICI Bank official website",
    },
    "Axis Bank": {
        "aliases": ("axis bank", "axisbank"),
        "domains": {"axisbank.com"},
        "source": "Axis Bank official website",
    },
    "Kotak Mahindra Bank": {
        "aliases": ("kotak mahindra", "kotak bank", "kotak"),
        "domains": {"kotak.com", "kotakbank.com"},
        "source": "Kotak Mahindra Bank official website",
    },
    "Reserve Bank of India": {
        "aliases": ("reserve bank of india", "rbi"),
        "domains": {"rbi.org.in"},
        "source": "RBI official website",
    },
    "NPCI / BHIM": {
        "aliases": ("npci", "bhim upi", "bhim"),
        "domains": {"npci.org.in", "bhimupi.org.in"},
        "source": "NPCI official website",
    },
    "Paytm": {
        "aliases": ("paytm", "paytm payments"),
        "domains": {"paytm.com", "paytmbank.com"},
        "source": "Paytm official website",
    },
    "PhonePe": {
        "aliases": ("phonepe",),
        "domains": {"phonepe.com"},
        "source": "PhonePe official website",
    },
    "IRCTC": {
        "aliases": ("irctc",),
        "domains": {"irctc.co.in"},
        "source": "Indian Railways IRCTC official website",
    },
    "India Post": {
        "aliases": ("india post", "indiapost"),
        "domains": {"indiapost.gov.in", "indiapost.in"},
        "source": "India Post Government portal",
    },
    "Income Tax Department": {
        "aliases": ("income tax department", "incometax", "e-filing"),
        "domains": {"incometax.gov.in", "incometaxindia.gov.in"},
        "source": "Government of India Income Tax portal",
    },
    "UIDAI / Aadhaar": {
        "aliases": ("uidai", "aadhaar"),
        "domains": {"uidai.gov.in"},
        "source": "UIDAI official portal",
    },
    "EPFO": {
        "aliases": ("epfo", "employees provident fund"),
        "domains": {"epfindia.gov.in"},
        "source": "EPFO Government portal",
    },
    "Amazon": {
        "aliases": ("amazon",),
        "domains": {"amazon.in", "amazon.com"},
        "source": "Amazon official website",
    },
    "Flipkart": {
        "aliases": ("flipkart",),
        "domains": {"flipkart.com"},
        "source": "Flipkart official website",
    },
    "FedEx": {
        "aliases": ("fedex",),
        "domains": {"fedex.com"},
        "source": "FedEx official website",
    },
    "DHL": {
        "aliases": ("dhl",),
        "domains": {"dhl.com"},
        "source": "DHL official website",
    },
    "Microsoft": {
        "aliases": ("microsoft", "office 365", "outlook"),
        "domains": {"microsoft.com", "live.com", "office.com"},
        "source": "Microsoft official website",
    },
    "PayPal": {
        "aliases": ("paypal",),
        "domains": {"paypal.com"},
        "source": "PayPal official website",
    },
}

_BRAND_SHORT_TOKENS = (
    "sbi", "hdfc", "icici", "axis", "kotak", "rbi", "npci", "bhim",
    "paytm", "phonepe", "irctc", "indiapost", "incometax", "uidai",
    "epfo", "amazon", "flipkart", "fedex", "dhl", "microsoft", "paypal",
)

_URL_IN_TEXT_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"'()]+", re.I)
_MD_LINK_RE = re.compile(r"\[([^\]]{1,200})\]\((https?://[^)\s]+)\)", re.I)
_ACTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sign in or verify account", re.compile(r"\b(?:sign\s*in|log\s*in|verify|re-?authenticate|confirm\s+your\s+account|update\s+kyc)\b", re.I)),
    ("click a link", re.compile(r"\b(?:click|open|visit|follow)\s+(?:the\s+|this\s+|below\s+)?(?:link|button|portal|url)\b", re.I)),
    ("reply or contact sender", re.compile(r"\b(?:reply\s+to|contact\s+us|call\s+back|respond\s+immediately)\b", re.I)),
    ("make a payment or transfer", re.compile(r"\b(?:pay|transfer|remit|settle|deposit|invoice|wire)\b", re.I)),
    ("open an attachment", re.compile(r"\b(?:attachment|attached|invoice\.pdf|document|download)\b", re.I)),
)


class _SafeHTMLTextAndLinks(HTMLParser):
    """Extract visible text and <a href> links without executing or fetching."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._text_parts: list[str] = []
        self._current_href: str | None = None
        self._current_label: list[str] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in {"script", "style", "head"}:
            self._skip_depth += 1
            return
        if t == "a":
            attr_map = dict(attrs)
            href = (attr_map.get("href") or "").strip()
            if href:
                self._current_href = href
                self._current_label = []
        elif t in {"p", "br", "div", "li", "tr"}:
            self._text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in {"script", "style", "head"} and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if t == "a" and self._current_href is not None:
            label = " ".join("".join(self._current_label).split())
            self.links.append({"label": label, "href": self._current_href})
            self._current_href = None
            self._current_label = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        self._text_parts.append(data)
        if self._current_href is not None:
            self._current_label.append(data)

    def visible_text(self) -> str:
        raw = "".join(self._text_parts)
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


def _extract_host(url_or_domain: str) -> str:
    raw = (url_or_domain or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "http://" + raw
    return (urlparse(raw).hostname or "").lower().rstrip(".")


def _has_homograph_or_punycode(host: str) -> tuple[bool, str]:
    h = (host or "").strip().lower()
    if not h:
        return False, ""
    if "xn--" in h:
        return True, "punycode (xn--) domain"
    scripts: set[str] = set()
    for ch in h:
        if ord(ch) > 127 and ch.isalpha():
            name = unicodedata.name(ch, "")
            if name:
                scripts.add(name.split()[0])
    if scripts:
        return True, f"non-ASCII homograph characters ({', '.join(sorted(scripts))})"
    return False, ""


def _parse_auth_headers(headers_text: str) -> dict[str, Any]:
    """Parse SPF/DKIM/DMARC tokens as unverified header claims."""
    out: dict[str, str] = {}
    for proto in ("spf", "dkim", "dmarc"):
        m = re.search(rf"\b{proto}\s*=\s*(pass|fail|softfail|neutral|none|temperror|permerror)\b", headers_text, re.I)
        if m:
            out[proto] = m.group(1).lower()
    return {
        "claims": out,
        "verified_independently": False,
        "note": "Header claims only (SPF/DKIM/DMARC in uploaded text or .eml are not independently verified).",
    }


def parse_eml_bytes(raw_bytes: bytes) -> dict[str, Any]:
    """Safely parse a .eml file into headers, body text, and hyperlinks."""
    msg = email.parser.BytesParser(policy=email.policy.default).parsebytes(raw_bytes)
    from_raw = str(msg.get("From") or "")
    reply_to_raw = str(msg.get("Reply-To") or "")
    subject = str(msg.get("Subject") or "")
    auth_raw = "\n".join(
        str(v) for k in ("Authentication-Results", "Received-SPF") for v in msg.get_all(k, [])
    )

    plain_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            disp = (part.get_content_disposition() or "").lower()
            fname = part.get_filename()
            if disp == "attachment" or fname:
                if fname:
                    attachments.append(str(fname))
                continue
            ctype = part.get_content_type()
            try:
                content = part.get_content()
            except Exception:
                payload = part.get_payload(decode=True) or b""
                content = payload.decode("utf-8", errors="replace")
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            if ctype == "text/plain":
                plain_parts.append(content)
            elif ctype == "text/html":
                html_parts.append(content)
    else:
        ctype = msg.get_content_type()
        try:
            content = msg.get_content()
        except Exception:
            payload = msg.get_payload(decode=True) or b""
            content = payload.decode("utf-8", errors="replace")
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        if ctype == "text/html":
            html_parts.append(content)
        else:
            plain_parts.append(content)

    links: list[dict[str, str]] = []
    html_text = ""
    if html_parts:
        parser = _SafeHTMLTextAndLinks()
        parser.feed("\n".join(html_parts))
        parser.close()
        links.extend(parser.links)
        html_text = parser.visible_text()

    body = "\n".join(p.strip() for p in plain_parts if p.strip()) or html_text
    if subject and subject not in body:
        combined_text = f"Subject: {subject}\n{body}".strip()
    else:
        combined_text = body

    return {
        "from_raw": from_raw,
        "reply_to_raw": reply_to_raw,
        "subject": subject,
        "auth_raw": auth_raw,
        "body": body,
        "combined_text": combined_text,
        "links": links,
        "attachments": attachments,
    }


def _extract_plain_headers(text: str) -> dict[str, Any]:
    """Extract optional From / Reply-To / Subject / Auth headers from pasted text."""
    from_m = re.search(r"(?im)^from:\s*(.+)$", text)
    reply_m = re.search(r"(?im)^reply-to:\s*(.+)$", text)
    subj_m = re.search(r"(?im)^subject:\s*(.+)$", text)
    auth_lines = re.findall(r"(?im)^(?:authentication-results|received-spf):\s*.+$", text)
    links: list[dict[str, str]] = []
    for m in _MD_LINK_RE.finditer(text):
        links.append({"label": m.group(1).strip(), "href": m.group(2).strip()})
    if "<a " in text.lower():
        parser = _SafeHTMLTextAndLinks()
        parser.feed(text)
        parser.close()
        links.extend(parser.links)
    return {
        "from_raw": from_m.group(1).strip() if from_m else "",
        "reply_to_raw": reply_m.group(1).strip() if reply_m else "",
        "subject": subj_m.group(1).strip() if subj_m else "",
        "auth_raw": "\n".join(auth_lines),
        "links": links,
    }


def verify_identity(
    text: str,
    email_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run structured offline identity and hyperlink verification."""
    meta = email_meta if email_meta is not None else _extract_plain_headers(text)
    from_display, from_addr = parseaddr(meta.get("from_raw") or "")
    _, reply_addr = parseaddr(meta.get("reply_to_raw") or "")
    from_addr = from_addr.lower().strip()
    reply_addr = reply_addr.lower().strip()

    from_domain = from_addr.split("@", 1)[1] if "@" in from_addr else ""
    reply_domain = reply_addr.split("@", 1)[1] if "@" in reply_addr else ""
    from_reg = registered_domain(from_domain) if from_domain else ""
    reply_reg = registered_domain(reply_domain) if reply_domain else ""

    # Identify claimed organisations from sender display name, subject, and body
    search_blob = f"{from_display} {meta.get('subject', '')} {text}".lower()
    claimed_orgs: list[str] = []
    for org, info in ORG_DOMAIN_REGISTRY.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", search_blob) for alias in info["aliases"]):
            claimed_orgs.append(org)

    # Extract hyperlinks + plain URLs
    links = list(meta.get("links") or [])
    seen_hrefs = {l["href"] for l in links}
    for m in _URL_IN_TEXT_RE.finditer(text):
        u = m.group(0).rstrip(".,;:!?")
        if u not in seen_hrefs:
            seen_hrefs.add(u)
            links.append({"label": "", "href": u})

    parsed_links: list[dict[str, str]] = []
    for item in links:
        href = item["href"]
        h = _extract_host(href)
        parsed_links.append({
            "label": item.get("label", ""),
            "href": href,
            "host": h,
            "registered_domain": registered_domain(h) if h else "",
        })

    requested_actions = [name for name, pat in _ACTION_PATTERNS if pat.search(text)]
    auth_info = _parse_auth_headers(meta.get("auth_raw") or "")

    indicators: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def add_ind(fid: str, title: str, explanation: str, weight: int, evidence: str, advice: str) -> None:
        if fid in seen_ids:
            return
        seen_ids.add(fid)
        indicators.append({
            "id": fid,
            "title": title,
            "explanation": explanation,
            "weight": weight,
            "evidence": evidence[:160],
            "start": 0,
            "end": 0,
            "advice": advice,
            "_category": "Identity / phishing",
        })

    # 1. Sender domain vs claimed organisation
    official_domain_match = False
    if from_reg and claimed_orgs:
        allowed_domains: set[str] = set()
        for org in claimed_orgs:
            allowed_domains |= ORG_DOMAIN_REGISTRY[org]["domains"]
        if from_reg in allowed_domains:
            official_domain_match = True
        else:
            add_ind(
                "identity_sender_mismatch",
                "Sender domain does not match claimed organisation",
                f"Message references {', '.join(claimed_orgs[:2])}, but sender address uses '{from_reg}' instead of an official domain.",
                6,
                f"From: {from_addr} (claimed: {', '.join(claimed_orgs[:2])})",
                "Do not trust the display name. Verify through the organisation's official app or website.",
            )

    # 2. Reply-To domain mismatch
    if from_reg and reply_reg and reply_reg != from_reg:
        add_ind(
            "identity_reply_to_mismatch",
            "Reply-To address uses a different domain than From",
            f"Replies go to '{reply_reg}' rather than the sender's domain '{from_reg}', a common phishing tactic.",
            5,
            f"From: {from_addr} | Reply-To: {reply_addr}",
            "Do not reply to this message; contact the organisation independently.",
        )

    # 3. Homograph / Punycode & Misleading subdomains (sender + links)
    hosts_to_check = ([("sender", from_domain)] if from_domain else []) + [
        ("link", l["host"]) for l in parsed_links if l["host"]
    ]
    for kind, host in hosts_to_check:
        is_homo, reason = _has_homograph_or_punycode(host)
        if is_homo:
            add_ind(
                "identity_homograph_or_punycode",
                "Domain uses Punycode or look-alike homograph characters",
                f"The {kind} domain '{host}' contains {reason}, which can disguise an impersonation domain.",
                6,
                host,
                "Do not open links or trust senders using look-alike non-ASCII domains.",
            )
        reg = registered_domain(host)
        sub_part = host[: -len(reg)].rstrip(".") if reg and host.endswith(reg) and len(host) > len(reg) else ""
        if sub_part:
            official_all = {d for info in ORG_DOMAIN_REGISTRY.values() for d in info["domains"]}
            if reg not in official_all:
                sub_tokens = set(re.split(r"[.\-_]", sub_part))
                if any(b in sub_tokens for b in _BRAND_SHORT_TOKENS) or any(d in sub_part for d in official_all):
                    add_ind(
                        "identity_misleading_subdomain",
                        "Misleading brand subdomain on an unrelated domain",
                        f"'{host}' places a trusted brand name in a subdomain, while the actual registered domain is '{reg}'.",
                        5,
                        host,
                        "Read the registered domain right before the first slash; ignore brand names in subdomains.",
                    )

    # 4. Deceptive hyperlink labels
    for l in parsed_links:
        label = l["label"]
        if not label:
            continue
        label_url_m = _URL_IN_TEXT_RE.search(label) or re.search(r"\b([a-z0-9\-]+\.(?:com|in|co\.in|org|org\.in|net|gov\.in))\b", label, re.I)
        if label_url_m:
            label_host = _extract_host(label_url_m.group(0))
            label_reg = registered_domain(label_host)
            if label_reg and l["registered_domain"] and label_reg != l["registered_domain"]:
                add_ind(
                    "identity_deceptive_hyperlink",
                    "Hyperlink text shows a different website than its destination",
                    f"Link text displays '{label_reg}', but actually points to '{l['registered_domain']}'.",
                    6,
                    f"Text '{label[:60]}' -> {l['href'][:90]}",
                    "Do not click mismatched hyperlinks. Type the official website address yourself.",
                )

    # 5. Unverified header auth failures (if explicitly present)
    claims = auth_info["claims"]
    failed_auth = [k.upper() for k, v in claims.items() if v in {"fail", "softfail"}]
    if failed_auth:
        add_ind(
            "identity_auth_fail",
            "Email authentication header reports failure",
            f"Provided header claims {', '.join(failed_auth)} failed (note: arbitrary uploaded headers are unverified).",
            4,
            ", ".join(f"{k}={v}" for k, v in claims.items()),
            "Treat this message as untrusted and verify independently.",
        )

    return {
        "from_address": from_addr,
        "from_display": from_display,
        "from_domain": from_domain,
        "from_registered_domain": from_reg,
        "reply_to_address": reply_addr,
        "reply_to_registered_domain": reply_reg,
        "claimed_organisations": claimed_orgs,
        "official_domain_match": official_domain_match,
        "sender_authenticated": False,
        "authentication_headers": auth_info,
        "hyperlinks": parsed_links,
        "requested_actions": requested_actions,
        "indicators": indicators,
    }
