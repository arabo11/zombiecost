# Launch post (r/devops first, r/aws the next day)

**Title**

My personal AWS bill was $4.90/month and it still had nine zombie resources in it. So I wrote a scanner.

**Body**

Last week I finally put my personal AWS organization under Terraform. Three accounts, nothing running, bill under five dollars. Before importing anything I went through the management account by hand to see what was actually in there. This is what two years of "I'll clean that up later" looks like on an account that does nothing:

- a stopped t3.medium from a Cloud9 workshop in March 2024, still paying for its 10 GiB volume
- two customer-managed KMS keys at $1/month each, the single biggest line on the bill
- three DynamoDB tables from an old Terraform state-locking setup, one of them locking a state file that was 180 bytes of nothing
- an empty S3 bucket and a second bucket holding that 180-byte state file
- an IAM role and policy whose only purpose was to reach the buckets and tables above
- an IAM user with an access key created in February 2024, never rotated
- a service control policy attached to nothing
- a CloudTrail log group with no retention, 465 MB and growing
- budget alerts that had been going to a misspelled email address for two years, so I had never received one

Total: about $4.90/month. Not a scary number. That is the point. On a hobby account the zombies cost $5. On the accounts I look after at work the same pattern costs hundreds, and nobody has time to walk every region by hand.

So I wrote `zombiecost`. One read-only scan, every region in parallel, one table, a number at the bottom:

```
$ pip install zombiecost
$ zombiecost --profile prod --redact
```

Here is what it finds on my own accounts today, after the cleanup, with `--redact` so the output is safe to paste:

```
Management account
 s3-stale        us-east-1  res-xxxxx01       779.7 KiB, nothing written for 946 days; reads unknown without request metrics   0.00
 Estimated waste: $0.00 per month across 1 resource in 17 regions.

Development account (the EIP and volume below are deliberately planted so I can test the scanner; not organic)
 eip-unused      eu-west-1  eipalloc-xxxxx01  Elastic IP ip-xxxxx01 is allocated but not associated                            3.65
 ebs-unattached  eu-west-1  vol-xxxxx01       10 GiB gp3 volume not attached to any instance                                   0.80
 Estimated waste: $4.45 per month across 2 resources in 17 regions.

Production account
 No waste found in 17 regions. Nice.
```

That 946-day bucket is real. I had forgotten it existed.

What it checks: unattached EBS volumes, unused Elastic IPs, snapshots older than 90 days that no AMI uses, EC2 instances under 3% CPU, NAT gateways moving almost no traffic, RDS instances with zero connections, load balancers with no targets or no requests, and S3 buckets nothing has written to in six months.

Things I tried to get right, because I have been burned by tools that did not:

- **Read-only.** The IAM policy is in the README: Describe, List and Get, nothing else.
- **No false "idle" on new resources.** Anything younger than 3 days is skipped. The first version flagged an instance I had launched ten minutes earlier as "idle for 14 days". A tool that does that is a tool you stop trusting.
- **Honest about what it cannot see.** S3 findings say "reads unknown" because reads are invisible without paid request metrics.
- **Prices are estimates** and labelled as such. "About $40/month", not an invoice.
- **`--redact`** replaces IDs, names, IPs and the account number with placeholders, so you can paste a report here without leaking anything.

MIT licensed: https://github.com/arabo11/zombiecost

What I am wondering: would anyone want this as a weekly scan with a Slack message, across all your accounts, without running anything yourself? That is what I would build next, and I would rather ask than guess. If that sounds useful there is a one-field form at https://zombiecost.com and I will tell you when it exists.

And the real question: run it on something bigger than my hobby account and tell me what it found, or what it missed. What is the zombie resource that bit you?

---

**Before posting**

- [ ] Post Tuesday to Thursday, 14:00 to 16:00 UTC
- [ ] r/devops first; r/aws the next day, different hour
- [ ] Reply to every comment in the first two hours
- [ ] If someone posts a report with a real number, ask permission to quote it in a follow-up
