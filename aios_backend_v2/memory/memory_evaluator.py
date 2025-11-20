from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Literal, Optional

from .profile import extract_profile_fields

# TODO(aios-context): Replace heuristic scoring with an LLM-based evaluator once the
#                     memory pipeline is fully wired.


MemoryType = Literal["user_profile", "preference", "project_fact", "misc_fact"]


@dataclass
class MemoryCandidate:
    user_message: str
    assistant_message: str
    goal: Optional[str] = None


@dataclass
class MemoryDecision:
    should_store: bool
    type: Optional[MemoryType] = None
    summary: Optional[str] = None
    strength: float = 0.0


META_PREFIXES = (
    r"^(?:let['’]s|let us)\s+reset[:\-\s]*",
    r"^(?:please\s+)?remember(?: that)?[:\-\s]*",
    r"^(?:please\s+)?save this(?: preference)?[:\-\s]*",
    r"^(?:hey|hi)[,!\s]+please remember[:\-\s]*",
    r"^user requested to be addressed as[:\-\s]*",
)

PREFERENCE_REGEX = re.compile(
    r"(?:i\s+(?:really\s+)?(?:prefer|like|love)\s+)(?P<object>[^.?!,]+)",
    re.IGNORECASE,
)
PROJECT_REGEX = re.compile(
    r"(?:i['’]?m|i am)\s+(?P<verb>building|working on|developing|creating)\s+(?P<project>[^.?!,]+)",
    re.IGNORECASE,
)


def evaluate_memory(candidate: MemoryCandidate) -> MemoryDecision:
    # TODO(aios-memory): Replace these heuristic rules with an LLM-based judge that
    # takes STM, goals, and project context into account.
    user_text = (candidate.user_message or "").strip()
    if not user_text:
        return MemoryDecision(False)

    clean_text = _clean_user_text(user_text)
    if not clean_text:
        return MemoryDecision(False)

    profile_fields = extract_profile_fields(user_text)
    if profile_fields:
        summary = _profile_summary(profile_fields, clean_text)
        return MemoryDecision(True, "user_profile", summary, 0.9)

    preference_summary = _preference_summary(clean_text)
    if preference_summary:
        return MemoryDecision(True, "preference", preference_summary, 0.8)

    project_summary = _project_summary(clean_text)
    if project_summary:
        return MemoryDecision(True, "project_fact", project_summary, 0.65)

    if "aios" in clean_text.lower():
        summary = _limit(f"User mentioned AIOS context: {clean_text}")
        return MemoryDecision(True, "project_fact", summary, 0.6)

    # Fallback: keep a trimmed factual snippet but treat as weak signal.
    fallback = _limit(clean_text)
    return MemoryDecision(False, "misc_fact", fallback, 0.4)


def _limit(text: str, max_len: int = 200) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _clean_user_text(text: str) -> str:
    cleaned = text.strip()
    for pattern in META_PREFIXES:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(" \"'").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _profile_summary(fields: Dict[str, str], clean_text: str) -> str:
    parts = []
    name = fields.get("name")
    nickname = fields.get("nickname")
    location = fields.get("location_current")
    origin = fields.get("country_from")

    if name and nickname:
        parts.append(f"User's name is {name} (nickname {nickname})")
    elif name:
        parts.append(f"User's name is {name}")
    elif nickname:
        parts.append(f"User's nickname is {nickname}")

    if location and origin:
        parts.append(f"User lives in {location} but is originally from {origin}")
    elif location:
        parts.append(f"User lives in {location}")
    elif origin:
        parts.append(f"User is originally from {origin}")

    project_clause = _project_clause(clean_text)
    if project_clause:
        if parts:
            parts[-1] = parts[-1].rstrip(".")
            parts.append(f"User {project_clause}")
        else:
            parts.append(f"User {project_clause}")

    if not parts:
        # Should not happen (extract_profile_fields would be empty), but guard anyway.
        return "User profile update."
    if len(parts) == 1:
        summary = parts[0]
    else:
        summary = ", ".join(parts[:-1]) + f", and {parts[-1]}"
    if not summary.endswith("."):
        summary += "."
    return _limit(summary)


def _preference_summary(text: str) -> Optional[str]:
    match = PREFERENCE_REGEX.search(text)
    if not match:
        return None
    preference = match.group("object").strip(" .!")
    if not preference:
        return None
    return _limit(f"User prefers {preference}.")


def _project_summary(text: str) -> Optional[str]:
    clause = _project_clause(text)
    if not clause:
        return None
    return _limit(f"User {clause}.")


def _project_clause(text: str) -> Optional[str]:
    match = PROJECT_REGEX.search(text)
    if not match:
        return None
    verb = match.group("verb").strip().lower()
    project = match.group("project").strip(" .!")
    if not project:
        return None
    if verb == "building":
        verb_phrase = "is building"
    elif verb == "developing":
        verb_phrase = "is developing"
    elif verb == "creating":
        verb_phrase = "is creating"
    else:
        verb_phrase = "is working on"
    return f"{verb_phrase} {project}"
