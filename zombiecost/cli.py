from __future__ import annotations

import argparse
import json
import sys

import boto3
from rich.console import Console
from rich.table import Table

from . import __version__
from .scanner import scan
from .checks import ALL_CHECKS, select_checks
from .redact import Redactor


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="zombiecost",
        description="Find idle and forgotten AWS resources and estimate what they cost every month.",
    )
    p.add_argument("--profile", help="AWS named profile to use")
    p.add_argument(
        "--regions",
        help="Comma-separated regions to scan. Default: every region enabled on the account.",
    )
    p.add_argument("--days", type=int, default=14, help="Lookback window for utilization metrics (default 14)")
    p.add_argument("--json", dest="json_path", help="Also write the full report as JSON to this path")
    p.add_argument(
        "--redact",
        action="store_true",
        help="Replace resource IDs, names, IPs and the account ID with placeholders so the report can be shared",
    )
    p.add_argument("--only", help="Comma-separated check names to run (default: all)")
    p.add_argument("--skip", help="Comma-separated check names to skip, e.g. s3-stale if you do not want object keys listed")
    p.add_argument("--list-checks", action="store_true", help="Print the available checks and exit")
    p.add_argument("--version", action="version", version=f"zombiecost {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = Console(stderr=True)

    if args.list_checks:
        for c in ALL_CHECKS:
            print(f"{c.name:16} {c.description}")
        return 0
    try:
        checks = select_checks(
            only=[x.strip() for x in args.only.split(",")] if args.only else None,
            skip=[x.strip() for x in args.skip.split(",")] if args.skip else None,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 2

    session = boto3.Session(profile_name=args.profile)
    regions = [r.strip() for r in args.regions.split(",")] if args.regions else None

    with console.status("Scanning...") as status:
        result = scan(
            session,
            regions=regions,
            lookback_days=args.days,
            checks=checks,
            on_progress=lambda region, check: status.update(f"Scanning {region}: {check}"),
        )

    if args.redact:
        redactor = Redactor()
        result.findings = [redactor.finding(f) for f in result.findings]
        result.account_id = redactor.text(result.account_id)

    out = Console()
    table = Table(title=f"AWS waste report for account {result.account_id}")
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Region", no_wrap=True)
    table.add_column("Resource", no_wrap=True)
    table.add_column("What we found")
    table.add_column("Est. $/month", justify="right", style="bold red")

    for f in result.findings:
        table.add_row(f.check, f.region, f.resource_id, f.description, f"{f.monthly_cost_estimate:,.2f}")

    if result.findings:
        out.print(table)
        out.print(
            f"\n[bold]Estimated waste: ${result.total_monthly_estimate:,.2f} per month[/bold] "
            f"across {len(result.findings)} resource{'s' if len(result.findings) != 1 else ''} "
            f"in {len(result.regions)} region{'s' if len(result.regions) != 1 else ''}.\n"
        )
    else:
        out.print(f"[green]No waste found in {len(result.regions)} region{'s' if len(result.regions) != 1 else ''}. Nice.[/green]")

    if args.json_path:
        with open(args.json_path, "w") as fh:
            json.dump(result.to_dict(), fh, indent=2, default=str)
        out.print(f"Full report written to {args.json_path}", soft_wrap=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
