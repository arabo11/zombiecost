"""Replace identifying strings in findings with stable placeholders.

The same real value always maps to the same placeholder within one report,
so a reader can still see that two findings refer to the same instance.
"""
from __future__ import annotations

import re

from .models import Finding

_PATTERNS = [
    ("i", re.compile(r"\bi-[0-9a-f]{8,17}\b")),
    ("vol", re.compile(r"\bvol-[0-9a-f]{8,17}\b")),
    ("snap", re.compile(r"\bsnap-[0-9a-f]{8,17}\b")),
    ("eipalloc", re.compile(r"\beipalloc-[0-9a-f]{8,17}\b")),
    ("nat", re.compile(r"\bnat-[0-9a-f]{8,17}\b")),
    ("vpc", re.compile(r"\bvpc-[0-9a-f]{8,17}\b")),
    ("subnet", re.compile(r"\bsubnet-[0-9a-f]{8,17}\b")),
    ("ip", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("acct", re.compile(r"\b\d{12}\b")),
]


class Redactor:
    def __init__(self) -> None:
        self._map: dict[str, str] = {}
        self._counts: dict[str, int] = {}

    def _placeholder(self, kind: str, value: str) -> str:
        if value not in self._map:
            self._counts[kind] = self._counts.get(kind, 0) + 1
            self._map[value] = f"{kind}-{'x' * 5}{self._counts[kind]:02d}"
        return self._map[value]

    def text(self, s: str) -> str:
        for kind, pattern in _PATTERNS:
            s = pattern.sub(lambda m, k=kind: self._placeholder(k, m.group(0)), s)
        # Quoted names (Name tags, bucket names, DB identifiers) are free text
        # chosen by humans and often reveal the company or project.
        s = re.sub(r"'([^']+)'", lambda m: f"'{self._placeholder('name', m.group(1))}'", s)
        return s

    def finding(self, f: Finding) -> Finding:
        rid = f.resource_id
        rid_redacted = self.text(rid)
        if rid_redacted == rid:
            # Free-form identifier (bucket, DB, load balancer name): placeholder it.
            rid_redacted = self._placeholder("res", rid)
        return Finding(
            check=f.check,
            resource_id=rid_redacted,
            region=f.region,
            description=self.text(f.description),
            monthly_cost_estimate=f.monthly_cost_estimate,
            recommendation=f.recommendation,
            details={},  # details carry raw identifiers; drop them when redacting
        )
