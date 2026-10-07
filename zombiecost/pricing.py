"""Rough on-demand prices, us-east-1, USD. Good enough for a savings estimate.

Everything here is intentionally approximate. The point of the report is to
show order of magnitude, not to replace Cost Explorer. Replace with the AWS
Pricing API later if customers ask for exact numbers.
"""

HOURS_PER_MONTH = 730

# $ per GB-month
EBS_GB_MONTH = {
    "gp2": 0.10,
    "gp3": 0.08,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,
}

SNAPSHOT_GB_MONTH = 0.05

# Elastic IP not attached to a running instance
EIP_UNUSED_HOUR = 0.005

# NAT gateway hourly charge, excluding data processing
NAT_GATEWAY_HOUR = 0.045

# Common instance types. Unknown types fall back to EC2_DEFAULT_HOUR.
EC2_HOUR = {
    "t2.micro": 0.0116,
    "t2.small": 0.023,
    "t2.medium": 0.0464,
    "t2.large": 0.0928,
    "t3.micro": 0.0104,
    "t3.small": 0.0208,
    "t3.medium": 0.0416,
    "t3.large": 0.0832,
    "t3.xlarge": 0.1664,
    "t3a.medium": 0.0376,
    "t3a.large": 0.0752,
    "m5.large": 0.096,
    "m5.xlarge": 0.192,
    "m5.2xlarge": 0.384,
    "m6i.large": 0.096,
    "m6i.xlarge": 0.192,
    "c5.large": 0.085,
    "c5.xlarge": 0.17,
    "c6i.large": 0.085,
    "r5.large": 0.126,
    "r5.xlarge": 0.252,
}
EC2_DEFAULT_HOUR = 0.10


def ebs_monthly(volume_type: str, size_gb: int) -> float:
    return round(EBS_GB_MONTH.get(volume_type, 0.10) * size_gb, 2)


def snapshot_monthly(size_gb: int) -> float:
    return round(SNAPSHOT_GB_MONTH * size_gb, 2)


def eip_monthly() -> float:
    return round(EIP_UNUSED_HOUR * HOURS_PER_MONTH, 2)


def nat_gateway_monthly() -> float:
    return round(NAT_GATEWAY_HOUR * HOURS_PER_MONTH, 2)


def ec2_monthly(instance_type: str) -> float:
    return round(EC2_HOUR.get(instance_type, EC2_DEFAULT_HOUR) * HOURS_PER_MONTH, 2)


# --- RDS, on-demand single-AZ, us-east-1 ---
RDS_HOUR = {
    "db.t3.micro": 0.017,
    "db.t3.small": 0.034,
    "db.t3.medium": 0.068,
    "db.t3.large": 0.136,
    "db.t4g.micro": 0.016,
    "db.t4g.small": 0.032,
    "db.t4g.medium": 0.065,
    "db.t4g.large": 0.129,
    "db.m5.large": 0.171,
    "db.m5.xlarge": 0.342,
    "db.m6g.large": 0.152,
    "db.m6g.xlarge": 0.304,
    "db.r5.large": 0.24,
    "db.r5.xlarge": 0.48,
    "db.r6g.large": 0.218,
}
RDS_DEFAULT_HOUR = 0.20
RDS_STORAGE_GB_MONTH = 0.115  # gp2/gp3


def rds_monthly(instance_class: str, allocated_gb: int = 0, multi_az: bool = False) -> float:
    hourly = RDS_HOUR.get(instance_class, RDS_DEFAULT_HOUR) * (2 if multi_az else 1)
    return round(hourly * HOURS_PER_MONTH + RDS_STORAGE_GB_MONTH * allocated_gb, 2)


# --- Load balancers, hourly base charge only (LCU/data charges excluded) ---
LB_HOUR = {
    "application": 0.0225,
    "network": 0.0225,
    "gateway": 0.0125,
    "classic": 0.025,
}


def lb_monthly(lb_type: str) -> float:
    return round(LB_HOUR.get(lb_type, 0.0225) * HOURS_PER_MONTH, 2)


# --- S3 storage, $ per GB-month ---
S3_GB_MONTH = {
    "StandardStorage": 0.023,
    "StandardIAStorage": 0.0125,
    "OneZoneIAStorage": 0.01,
    "IntelligentTieringFAStorage": 0.023,
    "IntelligentTieringIAStorage": 0.0125,
    "GlacierInstantRetrievalStorage": 0.004,
    "GlacierStorage": 0.0036,
    "DeepArchiveStorage": 0.00099,
}


def s3_monthly(bytes_by_storage_type: dict[str, float]) -> float:
    total = 0.0
    for storage_type, size_bytes in bytes_by_storage_type.items():
        total += S3_GB_MONTH.get(storage_type, 0.023) * size_bytes / 1024**3
    return round(total, 2)
