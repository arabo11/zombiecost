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
