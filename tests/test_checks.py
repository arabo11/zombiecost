from datetime import datetime, timedelta, timezone

from zombiecost.checks import UnattachedEbsVolumes, UnusedElasticIps, OldSnapshots, IdleEc2Instances
from zombiecost.scanner import scan

REGION = "us-east-1"


def test_unattached_volume_is_flagged_and_attached_is_not(session):
    ec2 = session.client("ec2", region_name=REGION)
    ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=100, VolumeType="gp3")

    ami = ec2.describe_images()["Images"][0]["ImageId"]
    inst = ec2.run_instances(ImageId=ami, InstanceType="t3.micro", MinCount=1, MaxCount=1)["Instances"][0]
    attached = ec2.create_volume(AvailabilityZone=inst["Placement"]["AvailabilityZone"], Size=8)
    ec2.attach_volume(VolumeId=attached["VolumeId"], InstanceId=inst["InstanceId"], Device="/dev/sdf")

    findings = UnattachedEbsVolumes(session).run(REGION)

    assert len(findings) == 1
    assert findings[0].details["size_gb"] == 100
    assert findings[0].monthly_cost_estimate == 8.0  # 100 GiB * $0.08 gp3


def test_unassociated_eip_is_flagged(session):
    ec2 = session.client("ec2", region_name=REGION)
    ec2.allocate_address(Domain="vpc")

    findings = UnusedElasticIps(session).run(REGION)

    assert len(findings) == 1
    assert findings[0].check == "eip-unused"
    assert findings[0].monthly_cost_estimate > 0


def test_recent_snapshot_is_not_flagged(session):
    ec2 = session.client("ec2", region_name=REGION)
    vol = ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=20)
    ec2.create_snapshot(VolumeId=vol["VolumeId"])

    findings = OldSnapshots(session).run(REGION)

    assert findings == []


def test_brand_new_instance_is_not_flagged_even_with_low_cpu(session):
    ec2 = session.client("ec2", region_name=REGION)
    cw = session.client("cloudwatch", region_name=REGION)
    ami = ec2.describe_images()["Images"][0]["ImageId"]
    inst = ec2.run_instances(ImageId=ami, InstanceType="t3.micro", MinCount=1, MaxCount=1)["Instances"][0]
    cw.put_metric_data(
        Namespace="AWS/EC2",
        MetricData=[{
            "MetricName": "CPUUtilization",
            "Dimensions": [{"Name": "InstanceId", "Value": inst["InstanceId"]}],
            "Timestamp": datetime.now(timezone.utc) - timedelta(hours=1),
            "Value": 0.0,
            "Unit": "Percent",
        }],
    )

    findings = IdleEc2Instances(session, lookback_days=14).run(REGION)

    assert findings == []  # launched just now, too young to judge


def test_idle_instance_is_flagged_when_cpu_is_low(session, monkeypatch):
    # moto launches instances "now"; pretend this one is old enough to judge.
    monkeypatch.setattr(IdleEc2Instances, "min_age_days", 0)
    ec2 = session.client("ec2", region_name=REGION)
    cw = session.client("cloudwatch", region_name=REGION)
    ami = ec2.describe_images()["Images"][0]["ImageId"]
    inst = ec2.run_instances(ImageId=ami, InstanceType="t3.medium", MinCount=1, MaxCount=1)["Instances"][0]

    now = datetime.now(timezone.utc)
    cw.put_metric_data(
        Namespace="AWS/EC2",
        MetricData=[
            {
                "MetricName": "CPUUtilization",
                "Dimensions": [{"Name": "InstanceId", "Value": inst["InstanceId"]}],
                "Timestamp": now - timedelta(days=d),
                "Value": 1.0,
                "Unit": "Percent",
            }
            for d in range(1, 8)
        ],
    )

    findings = IdleEc2Instances(session, lookback_days=14).run(REGION)

    assert len(findings) == 1
    assert findings[0].details["instance_type"] == "t3.medium"
    assert findings[0].details["avg_cpu_percent"] == 1.0


def test_scan_sorts_findings_by_cost(session):
    ec2 = session.client("ec2", region_name=REGION)
    ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=10, VolumeType="gp3")   # $0.80
    ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=500, VolumeType="gp2")  # $50.00
    ec2.allocate_address(Domain="vpc")                                            # $3.65

    result = scan(session, regions=[REGION])

    costs = [f.monthly_cost_estimate for f in result.findings]
    assert costs == sorted(costs, reverse=True)
    assert result.total_monthly_estimate == round(0.8 + 50.0 + 3.65, 2)
