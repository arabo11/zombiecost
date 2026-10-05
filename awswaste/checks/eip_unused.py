from __future__ import annotations

from ..models import Finding
from .. import pricing
from .base import Check


class UnusedElasticIps(Check):
    name = "eip-unused"
    description = "Elastic IPs that are allocated but not associated with anything."

    def run(self, region: str) -> list[Finding]:
        ec2 = self.session.client("ec2", region_name=region)
        findings: list[Finding] = []
        for addr in ec2.describe_addresses().get("Addresses", []):
            if addr.get("AssociationId") or addr.get("InstanceId") or addr.get("NetworkInterfaceId"):
                continue
            findings.append(
                Finding(
                    check=self.name,
                    resource_id=addr.get("AllocationId") or addr["PublicIp"],
                    region=region,
                    description=f"Elastic IP {addr['PublicIp']} is allocated but not associated",
                    monthly_cost_estimate=pricing.eip_monthly(),
                    recommendation="Release the address if nothing will use it.",
                    details={"public_ip": addr["PublicIp"]},
                )
            )
        return findings
