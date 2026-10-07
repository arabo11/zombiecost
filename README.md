# zombiecost

Find the zombie resources in your AWS account: things that should be dead but still bill you every month.

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
| `rds-idle` | RDS instances with zero connections over the lookback window | Instance class + storage |
| `lb-unused` | Load balancers with no registered targets, or ALBs that served 0 requests | Hourly LB charge |
| `s3-stale` | Buckets nothing has written to in 180 days, with their size and storage class | GB-month by storage class |

Prices are rough us-east-1 on-demand numbers. The goal is order of magnitude, not an invoice.

Checks that depend on usage history (`ec2-idle`, `rds-idle`, `nat-idle`, `lb-unused`)
ignore resources younger than 3 days, so a freshly launched instance is never
reported as idle. `s3-stale` can see writes but not reads; it says so in every
finding, because reads are invisible without paid request metrics.

## Install

```bash
pip install zombiecost
```

Or from a clone:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
zombiecost                                  # every enabled region, default profile
zombiecost --profile prod --regions eu-west-1,us-east-1
zombiecost --days 30 --json report.json     # longer lookback, machine-readable output
zombiecost --redact                         # placeholders instead of IDs, names and IPs: safe to paste publicly
zombiecost --skip s3-stale                  # never list object keys
zombiecost --only ebs-unattached,eip-unused # just the fast, metadata-only checks
zombiecost --list-checks
```

## Privacy and security

**Nothing leaves your machine except AWS API calls made with your own credentials.**
There is no telemetry, no update check, no call to zombiecost.com or any other
service. You can verify this: the package has exactly one runtime dependency that
talks to a network, `boto3`, and every call it makes is a `Describe`, `List` or
`Get`. There is no code path that creates, modifies or deletes anything.

What the tool reads, per check:

| Check | Reads |
|---|---|
| `ebs-unattached`, `eip-unused`, `snapshots-old`, `ec2-idle`, `nat-idle` | EC2 metadata (IDs, sizes, types, tags, launch times) and CloudWatch metrics |
| `rds-idle` | RDS instance metadata and CloudWatch connection counts |
| `lb-unused` | Load balancer and target group metadata, CloudWatch request counts |
| `s3-stale` | Bucket names and locations, object **keys and modification times** (never contents), CloudWatch size metrics |

`s3-stale` is the only check that touches anything object-level. It lists keys to
find the newest modification time and discards them; keys are never stored or
printed. If you would rather it did not list keys at all, run with
`--skip s3-stale` and drop `s3:ListBucket` from the policy below.

**The report is yours.** Plain output and `--json` contain real resource IDs,
names, tags and IPs, because that is what you need to go fix things. If you want
to share a report, use `--redact`: IDs, names, IPs and the account number become
stable placeholders and the per-finding `details` block is dropped entirely.

**Reporting a vulnerability:** see [SECURITY.md](SECURITY.md).

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
      "rds:DescribeDBInstances",
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeTargetGroups",
      "elasticloadbalancing:DescribeTargetHealth",
      "s3:ListAllMyBuckets",
      "s3:GetBucketLocation",
      "s3:ListBucket",
      "cloudwatch:GetMetricStatistics",
      "cloudwatch:ListMetrics"
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

- [ ] Unused KMS keys, Secrets Manager secrets and VPC endpoints (small, fixed monthly charges that add up)
- [ ] Stopped instances still paying for their volumes
- [ ] Old AMIs and the snapshots behind them
- [ ] Hosted version: cross-account role, weekly scans, Slack alerts
