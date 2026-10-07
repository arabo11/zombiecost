# Security

zombiecost is a read-only scanner. It never creates, modifies or deletes AWS
resources, and it never sends data anywhere except to AWS APIs using the
credentials you give it.

## Reporting a vulnerability

If you find a way the tool could modify resources, leak data, or be abused,
please do not open a public issue. Use GitHub's private vulnerability reporting
on this repository ("Security" tab, "Report a vulnerability"), or email
arabo.markarian@gmail.com with "zombiecost security" in the subject.

You will get an acknowledgement within 3 days and a fix or a clear answer
within 14. Credit is given in the release notes unless you prefer otherwise.

## Scope

In scope: anything in this repository, the published PyPI package, and the
landing page at zombiecost.com.

Out of scope: vulnerabilities in AWS itself or in dependencies that are already
public, though reports pointing at a vulnerable dependency are welcome.

## Supply chain

- Releases are published to PyPI by GitHub Actions using Trusted Publishing.
  No PyPI token exists anywhere.
- Dependabot watches both Python dependencies and GitHub Actions.
- Secret scanning with push protection is enabled on the repository.
