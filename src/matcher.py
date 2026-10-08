"""Turns human-written criteria into regular expressions and matches them against ad text.

Criterion syntax (case-insensitive):
  32gb            matches "32GB", "32 GB", "32-gb"   (spaces/dashes between letters and digits are optional)
  m1 pro|m1 max   alternatives separated by "|"
  re:<regex>      raw regular expression for advanced users
Words are matched as whole tokens: "m1" does not match "m12", "pro" does not match "produkt".
"""
import re
from functools import lru_cache
from typing import List, Optional, Pattern, Tuple

_TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)?|[^\W\d_]+|[^\w\s]", re.UNICODE)
_SEPARATOR = r"[\s\-_/]*"


@lru_cache(maxsize=1024)
def compile_criterion(criterion: str) -> Optional[Pattern]:
    """Returns a compiled pattern, or None for empty/invalid criteria."""
    text = (criterion or "").strip()
    if not text:
        return None
    if text.lower().startswith("re:"):
        try:
            return re.compile(text[3:].strip(), re.IGNORECASE)
        except re.error:
            return None

    alternatives = []
    for alt in text.split("|"):
        tokens = _TOKEN_RE.findall(alt.lower())
        if tokens:
            alternatives.append(_SEPARATOR.join(re.escape(t) for t in tokens))
    if not alternatives:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(alternatives) + r")(?!\w)", re.IGNORECASE)


def is_valid_criterion(criterion: str) -> bool:
    return compile_criterion(criterion) is not None


def matches(text: str, criterion: str) -> bool:
    pattern = compile_criterion(criterion)
    return bool(pattern and pattern.search(text or ""))


def split_criteria(text: str, criteria: List[str]) -> Tuple[List[str], List[str]]:
    """Returns (matched, missing) keeping the original order of criteria."""
    matched, missing = [], []
    for criterion in criteria:
        if not is_valid_criterion(criterion):
            continue
        (matched if matches(text, criterion) else missing).append(criterion)
    return matched, missing


def first_excluded(text: str, excludes: List[str]) -> Optional[str]:
    for word in excludes:
        if matches(text, word):
            return word
    return None
