from __future__ import annotations

from ..models import Finding
from .. import pricing
from .base import Check


class UnattachedEbsVolumes(Check):
    name = "ebs-unattached"
    description = "EBS volumes in 'available' state, attached to nothing, still billed every month."

    def run(self, region: str) -> list[Finding]:
        ec2 = self.session.client("ec2", region_name=region)
        findings: list[Finding] = []
        paginator = ec2.get_paginator("describe_volumes")
        for page in paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}]):
            for vol in page.get("Volumes", []):
                size = vol["Size"]
                vtype = vol.get("VolumeType", "gp2")
                cost = pricing.ebs_monthly(vtype, size)
                findings.append(
                    Finding(
                        check=self.name,
                        resource_id=vol["VolumeId"],
                        region=region,
                        description=f"{size} GiB {vtype} volume not attached to any instance",
                        monthly_cost_estimate=cost,
                        recommendation="Snapshot it if you might need the data, then delete the volume.",
                        details={
                            "size_gb": size,
                            "volume_type": vtype,
                            "created": vol["CreateTime"].isoformat(),
                            "tags": {t["Key"]: t["Value"] for t in vol.get("Tags", [])},
                        },
                    )
                )
        return findings
