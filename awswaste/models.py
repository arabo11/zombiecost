from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass
class Finding:
    """One wasteful resource discovered by a check."""

    check: str
    resource_id: str
    region: str
    description: str
    monthly_cost_estimate: float
    recommendation: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScanResult:
    account_id: str
    regions: list[str]
    lookback_days: int
    findings: list[Finding]

    @property
    def total_monthly_estimate(self) -> float:
        return round(sum(f.monthly_cost_estimate for f in self.findings), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "regions": self.regions,
            "lookback_days": self.lookback_days,
            "total_monthly_estimate": self.total_monthly_estimate,
            "findings": [f.to_dict() for f in self.findings],
        }
