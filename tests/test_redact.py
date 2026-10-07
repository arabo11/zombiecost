from zombiecost.models import Finding
from zombiecost.redact import Redactor


def test_redaction_is_stable_and_hides_identifiers():
    r = Redactor()
    f1 = Finding("ec2-idle", "i-0f220d4d4a3581143", "eu-west-1",
                 "t3.micro instance 'acme-billing-worker' averaged 0.5% CPU", 7.59, "stop it",
                 {"instance_type": "t3.micro"})
    f2 = Finding("eip-unused", "eipalloc-08a40a2a05731da50", "eu-west-1",
                 "Elastic IP 54.155.2.82 is allocated but not associated", 3.65, "release it")
    f3 = Finding("s3-stale", "acme-customer-exports", "us-east-1", "12.0 GiB, nothing written for 400 days", 0.28, "archive")

    out = [r.finding(f) for f in (f1, f2, f3)]

    assert "i-0f220d4d4a3581143" not in out[0].resource_id
    assert "acme" not in out[0].description and "acme" not in out[2].resource_id
    assert "54.155.2.82" not in out[1].description
    assert out[0].details == {}
    assert r.text("i-0f220d4d4a3581143") == out[0].resource_id  # same input, same placeholder
    assert r.text("123456789012") != "123456789012"
