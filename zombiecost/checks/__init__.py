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

__all__ = ["Check", "ALL_CHECKS"]
