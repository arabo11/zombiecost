from .base import Check
from .ebs_unattached import UnattachedEbsVolumes
from .eip_unused import UnusedElasticIps
from .snapshots_old import OldSnapshots
from .ec2_idle import IdleEc2Instances
from .nat_idle import IdleNatGateways

ALL_CHECKS: list[type[Check]] = [
    UnattachedEbsVolumes,
    UnusedElasticIps,
    OldSnapshots,
    IdleEc2Instances,
    IdleNatGateways,
]

__all__ = ["Check", "ALL_CHECKS"]
