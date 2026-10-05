# ghostbill

Stop paying for AWS resources that are ghosts.

Find idle and forgotten AWS resources and see what they cost you every month.

One read-only scan. One table. A number at the bottom you can act on today.

## What it finds

| Check | What it flags | How cost is estimated |
|---|---|---|
| `ebs-unattached` | EBS volumes attached to nothing | GB-month price by volume type |
| `eip-unused` | Elastic IPs not associated with anything | Hourly unused-EIP charge |
| `snapshots-old` | Snapshots older than 90 days that no AMI you own uses | GB-month snapshot price |
| `ec2-idle` | Running instances averaging under 3% CPU over the lookback window | On-demand hourly price |
| `nat-idle` | NAT gateways that moved under 1 GiB in the lookback window | Hourly NAT charge |

Prices are rough us-east-1 on-demand numbers. The goal is order of magnitude, not an invoice.

## Install

```bash
pip install ghostbill
```

Or from a clone:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
ghostbill                                  # every enabled region, default profile
ghostbill --profile prod --regions eu-west-1,us-east-1
ghostbill --days 30 --json report.json     # longer lookback, machine-readable output
```

## Permissions

The scan is read-only. Attach `ReadOnlyAccess`, or this minimal policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "sts:GetCallerIdentity",
      "ec2:DescribeRegions",
      "ec2:DescribeVolumes",
      "ec2:DescribeAddresses",
      "ec2:DescribeSnapshots",
      "ec2:DescribeImages",
      "ec2:DescribeInstances",
      "ec2:DescribeNatGateways",
      "cloudwatch:GetMetricStatistics"
    ],
    "Resource": "*"
  }]
}
```

## Tests

```bash
pytest
```

Tests run against [moto](https://github.com/getmoto/moto), no AWS account needed.

## Roadmap

- [ ] Idle RDS instances and unused load balancers
- [ ] Unused security groups and empty target groups
- [ ] Hosted version: cross-account role, weekly scans, Slack alerts
