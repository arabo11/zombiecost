from __future__ import annotations

from datetime import datetime, timezone

from ..models import Finding
from .. import pricing
from .base import Check


class IdleRdsInstances(Check):
    name = "rds-idle"
    description = "RDS instances with zero database connections over the lookback window."

    min_age_days = 3

    def run(self, region: str) -> list[Finding]:
        rds = self.session.client("rds", region_name=region)
        now = datetime.now(timezone.utc)
        findings: list[Finding] = []
        paginator = rds.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                if db.get("DBInstanceStatus") != "available":
                    continue
                created = db.get("InstanceCreateTime")
                if created is None or (now - created).days < self.min_age_days:
                    continue
                db_id = db["DBInstanceIdentifier"]
                max_conn = self._metric_max(
                    region, "AWS/RDS", "DatabaseConnections",
                    [{"Name": "DBInstanceIdentifier", "Value": db_id}],
                )
                if max_conn is None or max_conn > 0:
                    continue
                klass = db["DBInstanceClass"]
                storage = db.get("AllocatedStorage", 0)
                multi_az = bool(db.get("MultiAZ"))
                age_days = (now - created).days
                findings.append(
                    Finding(
                        check=self.name,
                        resource_id=db_id,
                        region=region,
                        description=(
                            f"{klass} {db.get('Engine', '')} instance had zero connections "
                            f"over the last {min(age_days, self.lookback_days)} days"
                        ),
                        monthly_cost_estimate=pricing.rds_monthly(klass, storage, multi_az),
                        recommendation="Take a final snapshot and delete it, or stop it if you will need it within 7 days.",
                        details={
                            "instance_class": klass,
                            "engine": db.get("Engine"),
                            "allocated_storage_gb": storage,
                            "multi_az": multi_az,
                            "age_days": age_days,
                        },
                    )
                )
        return findings
