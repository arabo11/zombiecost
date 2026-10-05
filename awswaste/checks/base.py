from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

import boto3

from ..models import Finding


class Check(ABC):
    """A single waste detector. Subclasses implement `run` for one region."""

    name: str = "base"
    description: str = ""

    def __init__(self, session: boto3.Session, lookback_days: int = 14):
        self.session = session
        self.lookback_days = lookback_days

    @abstractmethod
    def run(self, region: str) -> list[Finding]:
        ...

    # Helpers shared by metric-based checks

    def _window(self) -> tuple[datetime, datetime]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self.lookback_days)
        return start, end

    def _metric_average(
        self, region: str, namespace: str, metric: str, dimensions: list[dict], stat: str = "Average"
    ) -> float | None:
        """Return the mean of a CloudWatch metric over the lookback window, or None if no data."""
        cw = self.session.client("cloudwatch", region_name=region)
        start, end = self._window()
        resp = cw.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric,
            Dimensions=dimensions,
            StartTime=start,
            EndTime=end,
            Period=86400,
            Statistics=[stat],
        )
        points = resp.get("Datapoints", [])
        if not points:
            return None
        return sum(p[stat] for p in points) / len(points)

    def _metric_sum(self, region: str, namespace: str, metric: str, dimensions: list[dict]) -> float | None:
        cw = self.session.client("cloudwatch", region_name=region)
        start, end = self._window()
        resp = cw.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric,
            Dimensions=dimensions,
            StartTime=start,
            EndTime=end,
            Period=86400,
            Statistics=["Sum"],
        )
        points = resp.get("Datapoints", [])
        if not points:
            return None
        return sum(p["Sum"] for p in points)
