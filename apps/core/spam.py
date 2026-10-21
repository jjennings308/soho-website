"""
Spam checks for the public contact and event inquiry forms.

Layers (cheapest first):
  1. Honeypot field — core.utils.honeypot_tripped; filled = bot, dropped.
  2. Per-IP rate limit — core.utils.is_throttled.
  3. spam_reasons() below — form filled implausibly fast, no form token,
     links in the text, or mostly non-Latin text. Flagged submissions are
     kept (inquiries saved with status 'spam'; contact emails tagged), never
     silently discarded, so staff can rescue a false positive.
  4. Sitewide caps in the views, for floods spread across many IPs.
"""
import re
import time
import unicodedata

from django.core import signing

FORM_TOKEN_FIELD = 'ft'
_FORM_TOKEN_SALT = 'core.public-form-started'

# People take far longer than this to fill in a form; bots post instantly.
MIN_FILL_SECONDS = 3

# Real web addresses only — not bare domains, so "pat@gmail.com" in a message is fine.
_LINK_RE = re.compile(r'https?://|www\.|\[url|<a\s', re.IGNORECASE)


def form_started_token(started=None):
    """Signed page-load timestamp for the hidden FORM_TOKEN_FIELD input."""
    return signing.dumps(time.time() if started is None else started, salt=_FORM_TOKEN_SALT)


def form_started_at(token):
    """The timestamp inside a valid token, or None if missing/forged."""
    try:
        return float(signing.loads(token or '', salt=_FORM_TOKEN_SALT))
    except (signing.BadSignature, TypeError, ValueError):
        return None


def _mostly_non_latin(text):
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 20:
        return False
    latin = sum(1 for c in letters if 'LATIN' in unicodedata.name(c, ''))
    return latin / len(letters) < 0.5


def spam_reasons(request, *texts):
    """
    Reasons a submission looks like spam (empty list = looks fine).
    `texts` are the free-text fields to inspect (name, message, ...).
    """
    reasons = []

    started = form_started_at(request.POST.get(FORM_TOKEN_FIELD))
    if started is None:
        reasons.append('no form token')
    elif time.time() - started < MIN_FILL_SECONDS:
        reasons.append(f'sent {time.time() - started:.1f}s after page load')

    combined = '\n'.join(t for t in texts if t)
    if _LINK_RE.search(combined):
        reasons.append('link in text')
    if _mostly_non_latin(combined):
        reasons.append('mostly non-Latin text')

    return reasons
