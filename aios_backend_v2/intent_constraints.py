from __future__ import annotations

import re
from typing import Dict, List, Optional

_HINT_TEMPLATE = {
    "min": None,
    "max": None,
    "gt": None,
    "lt": None,
    "odd": False,
    "even": False,
}


def extract_number_hints(text: Optional[str]) -> Dict[str, Optional[int] | bool]:
    hints = dict(_HINT_TEMPLATE)
    if not text:
        return hints

    t = text.lower()
    range_match = re.search(r"(?:between|from)\s+(-?\d+)\s+(?:and|to)\s+(-?\d+)", t)
    if range_match:
        a, b = sorted([int(range_match.group(1)), int(range_match.group(2))])
        hints["min"], hints["max"] = a, b
    range_match = re.search(r"(-?\d+)\s*(?:\.\.|-)\s*(-?\d+)", t)
    if range_match:
        a, b = sorted([int(range_match.group(1)), int(range_match.group(2))])
        hints["min"] = max(hints["min"], a) if hints["min"] is not None else a
        hints["max"] = min(hints["max"], b) if hints["max"] is not None else b

    gt_match = re.search(r"(?:greater|more)\s+than\s+(-?\d+)", t)
    if not gt_match:
        gt_match = re.search(r"over\s+(-?\d+)", t)
    if not gt_match:
        gt_match = re.search(r">\s*(-?\d+)", t)
    if gt_match:
        hints["gt"] = max(hints["gt"], int(gt_match.group(1))) if hints["gt"] is not None else int(
            gt_match.group(1)
        )

    lt_match = re.search(r"(?:less|under)\s+than\s+(-?\d+)", t)
    if not lt_match:
        lt_match = re.search(r"<\s*(-?\d+)", t)
    if lt_match:
        hints["lt"] = min(hints["lt"], int(lt_match.group(1))) if hints["lt"] is not None else int(
            lt_match.group(1)
        )

    if "odd" in t:
        hints["odd"] = True
        hints["even"] = False
    if "even" in t:
        hints["even"] = True
        hints["odd"] = False

    return hints


def merge_hints(*hint_dicts: Dict[str, Optional[int] | bool]) -> Dict[str, Optional[int] | bool]:
    merged = dict(_HINT_TEMPLATE)
    for hints in hint_dicts:
        for key in ("min", "gt"):
            val = hints.get(key)
            if val is not None:
                merged[key] = max(merged[key], val) if merged[key] is not None else val
        for key in ("max", "lt"):
            val = hints.get(key)
            if val is not None:
                merged[key] = min(merged[key], val) if merged[key] is not None else val
        if hints.get("odd"):
            merged["odd"] = True
            merged["even"] = False
        if hints.get("even"):
            merged["even"] = True
            merged["odd"] = False
    return merged


def hints_active(hints: Dict[str, Optional[int] | bool]) -> bool:
    for field in ("min", "max", "gt", "lt"):
        if hints.get(field) is not None:
            return True
    return bool(hints.get("odd") or hints.get("even"))


def verify_number_reply(draft: str, hints: Dict[str, Optional[int] | bool]) -> str:
    normalized = _normalize_hints(hints)
    if not normalized["active"]:
        return draft

    numbers = [int(match) for match in re.findall(r"-?\d+", draft)]
    for number in numbers:
        if _satisfies(number, normalized):
            return draft

    contradiction = bool(numbers)
    if not contradiction:
        contradiction = _parity_word_violation(draft.lower(), normalized)

    if not contradiction:
        return draft

    candidates = _candidate_numbers(normalized)
    description = _describe_constraints(normalized)
    if candidates:
        if len(candidates) == 1:
            options = str(candidates[0])
        elif len(candidates) == 2:
            options = f"{candidates[0]} or {candidates[1]}"
        else:
            options = ", ".join(map(str, candidates[:-1])) + f", or {candidates[-1]}"
        return f"Given the constraints ({description}), the consistent options are {options}. Could it be {candidates[0]}?"

    return f"I'm keeping the constraints ({description}) in mind—could you clarify which number fits them?"


def _normalize_hints(hints: Dict[str, Optional[int] | bool]) -> Dict[str, Optional[int] | bool]:
    min_bound = hints.get("min")
    max_bound = hints.get("max")
    gt = hints.get("gt")
    lt = hints.get("lt")
    if gt is not None:
        min_bound = max(min_bound or (gt + 1), gt + 1)
    if lt is not None:
        max_bound = min(max_bound or (lt - 1), lt - 1)
    normalized = dict(hints)
    normalized["min_bound"] = min_bound
    normalized["max_bound"] = max_bound
    normalized["active"] = hints_active(normalized)
    return normalized


def _satisfies(number: int, hints: Dict[str, Optional[int] | bool]) -> bool:
    min_bound = hints.get("min_bound")
    max_bound = hints.get("max_bound")
    if min_bound is not None and number < min_bound:
        return False
    if max_bound is not None and number > max_bound:
        return False
    if hints.get("odd") and number % 2 == 0:
        return False
    if hints.get("even") and number % 2 != 0:
        return False
    if hints.get("gt") is not None and number <= hints["gt"]:
        return False
    if hints.get("lt") is not None and number >= hints["lt"]:
        return False
    return True


def _parity_word_violation(draft: str, hints: Dict[str, Optional[int] | bool]) -> bool:
    if hints.get("odd") and "even" in draft:
        return True
    if hints.get("even") and "odd" in draft:
        return True
    return False


def _candidate_numbers(hints: Dict[str, Optional[int] | bool]) -> List[int]:
    min_bound = hints.get("min_bound")
    max_bound = hints.get("max_bound")

    if min_bound is None and max_bound is None:
        min_bound, max_bound = 1, 10
    elif min_bound is None:
        min_bound = max((max_bound or 0) - 9, 1)
    elif max_bound is None:
        max_bound = min_bound + 9

    if max_bound < min_bound:
        max_bound = min_bound

    numbers = []
    for number in range(min_bound, min(max_bound, min_bound + 25) + 1):
        if _satisfies(number, hints):
            numbers.append(number)
        if len(numbers) >= 5:
            break
    return numbers


def _describe_constraints(hints: Dict[str, Optional[int] | bool]) -> str:
    parts: List[str] = []
    if hints.get("min_bound") is not None or hints.get("max_bound") is not None:
        lower = hints.get("min_bound")
        upper = hints.get("max_bound")
        if lower is not None and upper is not None:
            parts.append(f"between {lower} and {upper}")
        elif lower is not None:
            parts.append(f">= {lower}")
        elif upper is not None:
            parts.append(f"<= {upper}")
    if hints.get("gt") is not None:
        parts.append(f"> {hints['gt']}")
    if hints.get("lt") is not None:
        parts.append(f"< {hints['lt']}")
    if hints.get("odd"):
        parts.append("odd")
    if hints.get("even"):
        parts.append("even")
    return ", ".join(parts) or "the stated rules"
