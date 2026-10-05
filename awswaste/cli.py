from __future__ import annotations

import argparse
import json
import sys

import boto3
from rich.console import Console
from rich.table import Table

from . import __version__
from .scanner import scan


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="awswaste",
        description="Find idle and forgotten AWS resources and estimate what they cost every month.",
    )
    p.add_argument("--profile", help="AWS named profile to use")
    p.add_argument(
        "--regions",
        help="Comma-separated regions to scan. Default: every region enabled on the account.",
    )
    p.add_argument("--days", type=int, default=14, help="Lookback window for utilization metrics (default 14)")
    p.add_argument("--json", dest="json_path", help="Also write the full report as JSON to this path")
    p.add_argument("--version", action="version", version=f"awswaste {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = Console(stderr=True)

    session = boto3.Session(profile_name=args.profile)
    regions = [r.strip() for r in args.regions.split(",")] if args.regions else None

    with console.status("Scanning...") as status:
        result = scan(
            session,
            regions=regions,
            lookback_days=args.days,
            on_progress=lambda region, check: status.update(f"Scanning {region}: {check}"),
        )

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
            f"across {len(result.findings)} resources in {len(result.regions)} regions.\n"
        )
    else:
        out.print(f"[green]No waste found in {len(result.regions)} regions. Nice.[/green]")

    if args.json_path:
        with open(args.json_path, "w") as fh:
            json.dump(result.to_dict(), fh, indent=2, default=str)
        out.print(f"Full report written to {args.json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
