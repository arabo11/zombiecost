from __future__ import annotations

from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from ..models import Finding
from .. import pricing
from .base import Check


def _human_size(num_bytes: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if num_bytes < 1024 or unit == "TiB":
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TiB"


class StaleS3Buckets(Check):
    """Buckets nobody has written to in a long time.

    Reads cannot be seen without paid request metrics or data-event logging,
    so this check is explicit about what it knows: the newest object's age
    and what the bucket costs to keep. Each bucket is reported from the
    region it lives in, so the parallel per-region scan never duplicates it.
    """

    name = "s3-stale"
    description = "Buckets whose newest object is older than the threshold, priced by storage class."

    max_age_days = 180
    sample_limit = 5000  # objects inspected per bucket before giving up on an exact answer
    ignore_prefixes = ("cf-templates-", "aws-cloudtrail-logs-", "elasticbeanstalk-")

    def run(self, region: str) -> list[Finding]:
        s3 = self.session.client("s3", region_name=region)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.max_age_days)
        findings: list[Finding] = []

        for bucket in s3.list_buckets().get("Buckets", []):
            name = bucket["Name"]
            if name.startswith(self.ignore_prefixes):
                continue
            try:
                loc = s3.get_bucket_location(Bucket=name).get("LocationConstraint") or "us-east-1"
                if loc == "EU":
                    loc = "eu-west-1"
            except ClientError:
                continue
            if loc != region:
                continue

            newest, inspected, exhausted = self._newest_object(name, loc)
            if newest is None:
                if bucket["CreationDate"] > cutoff:
                    continue
                findings.append(
                    Finding(
                        check=self.name,
                        resource_id=name,
                        region=region,
                        description=f"empty bucket created {(now - bucket['CreationDate']).days} days ago",
                        monthly_cost_estimate=0.0,
                        recommendation="Delete it if nothing is going to use it.",
                        details={"objects_inspected": 0, "exact": True},
                    )
                )
                continue
            if newest > cutoff:
                continue

            sizes = self._size_by_storage_type(name, loc)
            total_bytes = sum(sizes.values())
            age_days = (now - newest).days
            qualifier = "" if exhausted else f" (first {inspected} objects inspected)"
            findings.append(
                Finding(
                    check=self.name,
                    resource_id=name,
                    region=region,
                    description=(
                        f"{_human_size(total_bytes)}, nothing written for {age_days} days{qualifier}; "
                        f"reads unknown without request metrics"
                    ),
                    monthly_cost_estimate=pricing.s3_monthly(sizes),
                    recommendation=(
                        "Add a lifecycle rule to Glacier Deep Archive if it must be kept, "
                        "or delete it. Enable request metrics first if you need proof nobody reads it."
                    ),
                    details={
                        "newest_object": newest.isoformat(),
                        "days_since_last_write": age_days,
                        "size_bytes_by_storage_type": {k: int(v) for k, v in sizes.items()},
                        "objects_inspected": inspected,
                        "exact": exhausted,
                    },
                )
            )
        return findings

    def _newest_object(self, bucket: str, region: str) -> tuple[datetime | None, int, bool]:
        s3 = self.session.client("s3", region_name=region)
        newest: datetime | None = None
        inspected = 0
        try:
            for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
                for obj in page.get("Contents", []):
                    inspected += 1
                    lm = obj["LastModified"]
                    if newest is None or lm > newest:
                        newest = lm
                    if inspected >= self.sample_limit:
                        return newest, inspected, False
        except ClientError:
            return None, inspected, False
        return newest, inspected, True

    def _size_by_storage_type(self, bucket: str, region: str) -> dict[str, float]:
        """Latest daily BucketSizeBytes per storage type from CloudWatch (free metric)."""
        cw = self.session.client("cloudwatch", region_name=region)
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=3)
        sizes: dict[str, float] = {}
        metrics = cw.list_metrics(
            Namespace="AWS/S3", MetricName="BucketSizeBytes",
            Dimensions=[{"Name": "BucketName", "Value": bucket}],
        ).get("Metrics", [])
        for m in metrics:
            dims = {d["Name"]: d["Value"] for d in m["Dimensions"]}
            storage_type = dims.get("StorageType", "StandardStorage")
            resp = cw.get_metric_statistics(
                Namespace="AWS/S3", MetricName="BucketSizeBytes", Dimensions=m["Dimensions"],
                StartTime=start, EndTime=end, Period=86400, Statistics=["Average"],
            )
            points = resp.get("Datapoints", [])
            if points:
                latest = max(points, key=lambda p: p["Timestamp"])
                sizes[storage_type] = latest["Average"]
        return sizes
