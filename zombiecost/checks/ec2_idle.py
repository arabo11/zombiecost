from __future__ import annotations

from datetime import datetime, timezone

from ..models import Finding
from .. import pricing
from .base import Check


class IdleEc2Instances(Check):
    name = "ec2-idle"
    description = "Running instances whose average CPU over the lookback window is below the threshold."

    cpu_threshold_percent = 3.0
    # An instance younger than this has not had a chance to do anything yet.
    min_age_days = 3

    def run(self, region: str) -> list[Finding]:
        now = datetime.now(timezone.utc)
        ec2 = self.session.client("ec2", region_name=region)
        findings: list[Finding] = []
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
            for reservation in page.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    instance_id = inst["InstanceId"]
                    age_days = (now - inst["LaunchTime"]).days
                    if age_days < self.min_age_days:
                        continue
                    avg_cpu = self._metric_average(
                        region,
                        "AWS/EC2",
                        "CPUUtilization",
                        [{"Name": "InstanceId", "Value": instance_id}],
                    )
                    if avg_cpu is None or avg_cpu >= self.cpu_threshold_percent:
                        continue
                    itype = inst["InstanceType"]
                    name = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), "")
                    findings.append(
                        Finding(
                            check=self.name,
                            resource_id=instance_id,
                            region=region,
                            description=(
                                f"{itype} instance{' ' + repr(name) if name else ''} averaged "
                                f"{avg_cpu:.1f}% CPU over the last {min(age_days, self.lookback_days)} days"
                            ),
                            monthly_cost_estimate=pricing.ec2_monthly(itype),
                            recommendation="Stop it, downsize it, or move the workload to a scheduled job.",
                            details={
                                "instance_type": itype,
                                "name": name,
                                "avg_cpu_percent": round(avg_cpu, 2),
                                "age_days": age_days,
                                "launch_time": inst["LaunchTime"].isoformat(),
                            },
                        )
                    )
        return findings
