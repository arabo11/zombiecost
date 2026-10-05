from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from .checks import ALL_CHECKS, Check
from .models import Finding, ScanResult


def enabled_regions(session: boto3.Session) -> list[str]:
    ec2 = session.client("ec2", region_name=session.region_name or "us-east-1")
    resp = ec2.describe_regions(AllRegions=False)
    return sorted(r["RegionName"] for r in resp["Regions"])


def account_id(session: boto3.Session) -> str:
    return session.client("sts").get_caller_identity()["Account"]


def scan(
    session: boto3.Session,
    regions: list[str] | None = None,
    lookback_days: int = 14,
    checks: list[type[Check]] | None = None,
    on_progress=None,
) -> ScanResult:
    regions = regions or enabled_regions(session)
    checks = checks or ALL_CHECKS
    findings: list[Finding] = []
    for region in regions:
        for check_cls in checks:
            check = check_cls(session, lookback_days=lookback_days)
            if on_progress:
                on_progress(region, check.name)
            try:
                findings.extend(check.run(region))
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                # Opt-in regions and missing permissions should not kill the whole scan.
                if code in {"UnauthorizedOperation", "AccessDeniedException", "AuthFailure", "OptInRequired"}:
                    continue
                raise
    findings.sort(key=lambda f: f.monthly_cost_estimate, reverse=True)
    return ScanResult(account_id=account_id(session), regions=regions, lookback_days=lookback_days, findings=findings)
