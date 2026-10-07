from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

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


def _scan_region(session: boto3.Session, region: str, lookback_days: int, checks: list[type[Check]], on_progress) -> list[Finding]:
    findings: list[Finding] = []
    for check_cls in checks:
        check = check_cls(session, lookback_days=lookback_days)
        if on_progress:
            on_progress(region, check.name)
        try:
            findings.extend(check.run(region))
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            # Opt-in regions, SCP-denied regions and missing permissions should
            # not kill the whole scan.
            if code in {"UnauthorizedOperation", "AccessDeniedException", "AccessDenied", "AuthFailure", "OptInRequired"}:
                continue
            raise
    return findings


def scan(
    session: boto3.Session,
    regions: list[str] | None = None,
    lookback_days: int = 14,
    checks: list[type[Check]] | None = None,
    on_progress=None,
    max_workers: int = 8,
) -> ScanResult:
    regions = regions or enabled_regions(session)
    checks = checks or ALL_CHECKS
    findings: list[Finding] = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(regions))) as pool:
        futures = [pool.submit(_scan_region, session, r, lookback_days, checks, on_progress) for r in regions]
        for fut in as_completed(futures):
            findings.extend(fut.result())
    findings.sort(key=lambda f: f.monthly_cost_estimate, reverse=True)
    return ScanResult(account_id=account_id(session), regions=regions, lookback_days=lookback_days, findings=findings)
