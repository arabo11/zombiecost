from __future__ import annotations

from ..models import Finding
from .. import pricing
from .base import Check


class IdleNatGateways(Check):
    name = "nat-idle"
    description = "NAT gateways that moved almost no traffic over the lookback window."

    min_bytes = 1 * 1024**3  # 1 GiB total over the window counts as "used"

    def run(self, region: str) -> list[Finding]:
        ec2 = self.session.client("ec2", region_name=region)
        findings: list[Finding] = []
        paginator = ec2.get_paginator("describe_nat_gateways")
        for page in paginator.paginate(Filter=[{"Name": "state", "Values": ["available"]}]):
            for nat in page.get("NatGateways", []):
                nat_id = nat["NatGatewayId"]
                dims = [{"Name": "NatGatewayId", "Value": nat_id}]
                out_bytes = self._metric_sum(region, "AWS/NATGateway", "BytesOutToDestination", dims) or 0.0
                in_bytes = self._metric_sum(region, "AWS/NATGateway", "BytesInFromSource", dims) or 0.0
                total = out_bytes + in_bytes
                if total >= self.min_bytes:
                    continue
                findings.append(
                    Finding(
                        check=self.name,
                        resource_id=nat_id,
                        region=region,
                        description=(
                            f"NAT gateway in {nat.get('VpcId', '?')} moved {total / 1024**2:.1f} MiB "
                            f"in {self.lookback_days} days"
                        ),
                        monthly_cost_estimate=pricing.nat_gateway_monthly(),
                        recommendation="Delete it, or replace with VPC endpoints if the traffic is only to AWS services.",
                        details={
                            "vpc_id": nat.get("VpcId"),
                            "subnet_id": nat.get("SubnetId"),
                            "bytes_total": int(total),
                        },
                    )
                )
        return findings
