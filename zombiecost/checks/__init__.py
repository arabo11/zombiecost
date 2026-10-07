from .base import Check
from .ebs_unattached import UnattachedEbsVolumes
from .eip_unused import UnusedElasticIps
from .snapshots_old import OldSnapshots
from .ec2_idle import IdleEc2Instances
from .nat_idle import IdleNatGateways
from .rds_idle import IdleRdsInstances
from .lb_unused import UnusedLoadBalancers
from .s3_stale import StaleS3Buckets

ALL_CHECKS: list[type[Check]] = [
    UnattachedEbsVolumes,
    UnusedElasticIps,
    OldSnapshots,
    IdleEc2Instances,
    IdleNatGateways,
    IdleRdsInstances,
    UnusedLoadBalancers,
    StaleS3Buckets,
]

__all__ = ["Check", "ALL_CHECKS", "select_checks"]


def select_checks(only: list[str] | None = None, skip: list[str] | None = None) -> list[type[Check]]:
    """Filter ALL_CHECKS by name. Unknown names raise ValueError so typos fail loudly."""
    names = {c.name for c in ALL_CHECKS}
    for group in (only or []), (skip or []):
        unknown = sorted(set(group) - names)
        if unknown:
            raise ValueError(f"unknown check(s): {', '.join(unknown)}. Known: {', '.join(sorted(names))}")
    chosen = [c for c in ALL_CHECKS if (not only or c.name in only) and c.name not in (skip or [])]
    return chosen
