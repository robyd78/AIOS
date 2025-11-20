from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class UserProfile:
    name: Optional[str] = None
    nickname: Optional[str] = None
    country_from: Optional[str] = None
    location_current: Optional[str] = None


_NAME_REGEX = re.compile(r"(?:my name is|i(?:'m| am) called)\s+([A-Za-z][A-Za-z\-\s']{1,50})", re.IGNORECASE)
_NICK_REGEX = re.compile(r"(?:call me|you can call me|nickname is)\s+([A-Za-z][A-Za-z\-\s']{1,50})", re.IGNORECASE)
_FROM_REGEX = re.compile(
    r"(?:i(?:'| a)m\s+from|i was born in|i['’]?m\s+originally\s+from)\s+([A-Za-z][A-Za-z\-\s']{1,60})",
    re.IGNORECASE,
)
_LOCATION_REGEX = re.compile(r"(?:i live in|i'm in|i am in|i reside in)\s+([A-Za-z][A-Za-z\-\s']{1,60})", re.IGNORECASE)


def extract_profile_fields(text: str) -> Dict[str, str]:
    """Return normalized profile fields parsed from free-form text."""
    fields: Dict[str, str] = {}
    if not text:
        return fields

    def _clean(match: Optional[re.Match[str]]) -> Optional[str]:
        if not match:
            return None
        value = match.group(1).strip()
        return value if value else None

    name = _clean(_NAME_REGEX.search(text))
    if name:
        fields["name"] = name

    nickname = _clean(_NICK_REGEX.search(text))
    if nickname:
        fields["nickname"] = nickname

    from_value = _clean(_FROM_REGEX.search(text))
    if from_value:
        fields["country_from"] = from_value

    location = _clean(_LOCATION_REGEX.search(text))
    if location:
        fields["location_current"] = location

    return fields


FIELD_LABELS = {
    "name": "Name",
    "nickname": "Nickname",
    "country_from": "From",
    "location_current": "Location",
}


def format_profile_summary(profile: Dict[str, str]) -> str:
    details = []
    for key, label in FIELD_LABELS.items():
        value = profile.get(key)
        if value:
            details.append(f"{label}: {value}")
    if not details:
        return "User profile (no details provided)."
    return "User profile — " + "; ".join(details)
