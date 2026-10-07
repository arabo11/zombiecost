from __future__ import annotations

from botocore.exceptions import ClientError

from ..models import Finding
from .. import pricing
from .base import Check


class UnusedLoadBalancers(Check):
    name = "lb-unused"
    description = "Load balancers with no registered targets, or ALBs that served zero requests."

    def run(self, region: str) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._elbv2(region))
        findings.extend(self._classic(region))
        return findings

    def _elbv2(self, region: str) -> list[Finding]:
        elb = self.session.client("elbv2", region_name=region)
        findings: list[Finding] = []
        for page in elb.get_paginator("describe_load_balancers").paginate():
            for lb in page.get("LoadBalancers", []):
                arn = lb["LoadBalancerArn"]
                name = lb["LoadBalancerName"]
                lb_type = lb.get("Type", "application")

                targets = 0
                try:
                    groups = elb.describe_target_groups(LoadBalancerArn=arn).get("TargetGroups", [])
                except ClientError as exc:
                    if exc.response.get("Error", {}).get("Code") != "TargetGroupNotFound":
                        raise
                    groups = []
                for tg in groups:
                    health = elb.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])
                    targets += len(health.get("TargetHealthDescriptions", []))

                reason = None
                if targets == 0:
                    reason = "has no registered targets"
                elif lb_type == "application":
                    # ARN suffix "app/name/id" is the CloudWatch dimension.
                    suffix = arn.split(":loadbalancer/")[-1]
                    requests = self._metric_sum(
                        region, "AWS/ApplicationELB", "RequestCount",
                        [{"Name": "LoadBalancer", "Value": suffix}],
                    )
                    if requests is not None and requests == 0:
                        reason = f"served 0 requests in {self.lookback_days} days"
                if reason is None:
                    continue

                findings.append(
                    Finding(
                        check=self.name,
                        resource_id=name,
                        region=region,
                        description=f"{lb_type} load balancer {reason}",
                        monthly_cost_estimate=pricing.lb_monthly(lb_type),
                        recommendation="Delete it. Load balancers bill hourly whether or not they carry traffic.",
                        details={"arn": arn, "type": lb_type, "registered_targets": targets},
                    )
                )
        return findings

    def _classic(self, region: str) -> list[Finding]:
        elb = self.session.client("elb", region_name=region)
        findings: list[Finding] = []
        for page in elb.get_paginator("describe_load_balancers").paginate():
            for lb in page.get("LoadBalancerDescriptions", []):
                if lb.get("Instances"):
                    continue
                findings.append(
                    Finding(
                        check=self.name,
                        resource_id=lb["LoadBalancerName"],
                        region=region,
                        description="classic load balancer has no registered instances",
                        monthly_cost_estimate=pricing.lb_monthly("classic"),
                        recommendation="Delete it, or migrate to an ALB/NLB if it is still needed.",
                        details={"type": "classic", "registered_targets": 0},
                    )
                )
        return findings
