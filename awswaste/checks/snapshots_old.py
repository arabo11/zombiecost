from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..models import Finding
from .. import pricing
from .base import Check


class OldSnapshots(Check):
    name = "snapshots-old"
    description = "EBS snapshots older than the age threshold that no AMI you own references."

    max_age_days = 90

    def run(self, region: str) -> list[Finding]:
        ec2 = self.session.client("ec2", region_name=region)
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.max_age_days)

        # Snapshots that back one of our AMIs are not waste, skip them.
        ami_snapshots: set[str] = set()
        for image in ec2.describe_images(Owners=["self"]).get("Images", []):
            for bdm in image.get("BlockDeviceMappings", []):
                snap_id = bdm.get("Ebs", {}).get("SnapshotId")
                if snap_id:
                    ami_snapshots.add(snap_id)

        findings: list[Finding] = []
        paginator = ec2.get_paginator("describe_snapshots")
        for page in paginator.paginate(OwnerIds=["self"]):
            for snap in page.get("Snapshots", []):
                if snap["SnapshotId"] in ami_snapshots:
                    continue
                started = snap["StartTime"]
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                if started > cutoff:
                    continue
                age_days = (datetime.now(timezone.utc) - started).days
                size = snap.get("VolumeSize", 0)
                findings.append(
                    Finding(
                        check=self.name,
                        resource_id=snap["SnapshotId"],
                        region=region,
                        description=f"{size} GiB snapshot is {age_days} days old and not used by any AMI",
                        monthly_cost_estimate=pricing.snapshot_monthly(size),
                        recommendation="Delete it, or move it to the Archive tier if you must keep it.",
                        details={
                            "size_gb": size,
                            "age_days": age_days,
                            "volume_id": snap.get("VolumeId"),
                            "description": snap.get("Description", ""),
                        },
                    )
                )
        return findings
