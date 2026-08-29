"""Deterministic guardrail screens. Each returns a match string on catch, else None."""

import re

_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "skip further review",
    "pre-approved",
    "disregard",
]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD_RE = re.compile(r"\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b")

_CATEGORY_KEYWORDS = {
    "vendor_details": ["vendor", "acme", "globex", "supplier"],
    "contract_terms": ["standard terms", "payment net", "clause", "contract"],
    "budget_figures": ["budget", "limit", "quote", "amount"],
    "sanctions_data": ["sanction", "do-not-do-business", "blacklist"],
    "internal_notes": ["internal", "note to self", "reminder"],
}


def injection_screen(text: str):
    lowered = text.lower()
    for phrase in _INJECTION_PATTERNS:
        if phrase in lowered:
            return phrase
    return None


def pii_screen(text: str):
    for pattern in (_EMAIL_RE, _PHONE_RE, _SSN_RE, _CARD_RE):
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def role_policy_screen(text: str, allowed, categories=None):
    if allowed is None:
        return None
    if categories is not None:
        # The sender declared what it is sending (a verdict note is
        # internal_notes); enforce the declaration instead of guessing.
        for category in categories:
            if category not in allowed:
                return category
        return None
    lowered = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            if category not in allowed:
                return category
    return None
