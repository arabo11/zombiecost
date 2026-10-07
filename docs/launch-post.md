# Launch post draft (r/devops, r/aws)

**Title options**

- I built a free CLI that finds the AWS resources you forgot about and tells you what they cost
- Found $X/month of zombie resources in my own AWS account with a 9-second scan, so I open-sourced the scanner

**Body**

Every AWS account I have ever touched has the same leftovers: a volume from an instance that was terminated two years ago, an Elastic IP nobody released, a load balancer in front of nothing, a NAT gateway for a VPC that has been empty since the migration. Each one is small. Together they are a line on the bill nobody can explain.

I wrote `zombiecost` to find them. One read-only scan, one table, a number at the bottom:

```
$ pip install zombiecost
$ zombiecost --profile prod
```

[PASTE REAL REPORT TABLE HERE]

What it checks today: unattached EBS volumes, unused Elastic IPs, snapshots older than 90 days that no AMI uses, EC2 instances under 3% CPU, NAT gateways moving almost no traffic, RDS instances with zero connections, load balancers with no targets, and S3 buckets nothing has written to in six months.

Things I tried to get right, because I have been burned by tools that did not:

- **Read-only.** The IAM policy is in the README. Eleven Describe/List/Get actions, nothing else.
- **No false "idle" on new resources.** Anything younger than 3 days is skipped. A tool that flags an instance you launched this morning is a tool you stop trusting.
- **Honest about what it cannot see.** S3 findings say "reads unknown" because reads are invisible without paid request metrics.
- **Prices are estimates** and labelled as such. The point is "this is ~$40/month", not an invoice.
- **Multi-region in parallel.** 17 regions in about 9 seconds on an empty account.

It is MIT licensed: [github link]

What I am wondering: would anyone want this as a weekly scan with a Slack message, across accounts, without running anything yourself? That is what I am considering building next, and I would rather ask than guess. If that sounds useful, there is a one-field form at [zombiecost.com] and I will tell you when it exists.

Happy to add checks. What is the zombie resource that bit you?

---

**Notes to self before posting**

- Replace $X with the real number from a real account. The Development account with test waste is not it; use a friend's account or wait for the first external report.
- Put the actual table in, not a description of the table.
- Make the repo public first. A private repo link is a dead post.
- One-field email form on zombiecost.com must exist before posting. Cloudflare Pages + a form, or a Tally form embedded.
- Post Tuesday to Thursday, 14:00 to 16:00 UTC.
- Reply to every comment in the first two hours.
