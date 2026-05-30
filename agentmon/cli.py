"""CLI interface for Agent Monitor."""

from __future__ import annotations

import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentmon.alerter import BudgetAlerter
from agentmon.analyzer import Analyzer
from agentmon.config import Config
from agentmon.db import Database
from agentmon.exporter import Exporter

console = Console()


def _get_components() -> tuple[Database, Config, Analyzer, BudgetAlerter, Exporter]:
    """Initialize all components."""
    config = Config()
    db = Database(config)
    analyzer = Analyzer(db, config)
    alerter = BudgetAlerter(db, config)
    exporter = Exporter(db, config)
    return db, config, analyzer, alerter, exporter


@click.group()
@click.version_option(version="0.1.0", prog_name="agentmon")
def cli() -> None:
    """Agent Monitor - Cost and usage monitoring for AI API calls.

    Track spending, set budgets, compare providers, never overspend again.
    """
    pass


# ---- Dashboard ----

@cli.command()
@click.option(
    "--period", "-p",
    type=click.Choice(["day", "week", "month", "year"], case_sensitive=False),
    default="month",
    help="Time period for the dashboard.",
)
def dashboard(period: str) -> None:
    """Show cost dashboard with usage breakdown."""
    db, config, analyzer, alerter, exporter = _get_components()
    try:
        summary = analyzer.dashboard(period)

        # Header
        title = f"Agent Monitor Dashboard ({period})"
        console.print()
        console.print(
            Panel(
                f"[bold]{title}[/bold]\n"
                f"Period: {summary.start_date} to {summary.end_date}",
                style="blue",
            )
        )

        # Overview stats
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column("Metric", style="bold")
        stats_table.add_column("Value")
        stats_table.add_row("Total Cost", f"[green]${summary.total_cost:.4f}[/green]")
        stats_table.add_row("Total Calls", str(summary.total_calls))
        stats_table.add_row(
            "Tokens (In/Out)",
            f"{summary.total_tokens_in:,} / {summary.total_tokens_out:,}",
        )
        stats_table.add_row("Avg Latency", f"{summary.avg_latency_ms:.1f} ms")
        stats_table.add_row("Success Rate", f"{summary.success_rate * 100:.1f}%")
        console.print(Panel(stats_table, title="Overview", border_style="green"))

        # Budget alerts
        alerts = alerter.check_alerts()
        for alert in alerts:
            console.print(f"[bold red]  ! {alert}[/bold red]")

        # Provider breakdown
        if summary.by_provider:
            prov_table = Table(title="Cost by Provider")
            prov_table.add_column("Provider", style="cyan")
            prov_table.add_column("Calls", justify="right")
            prov_table.add_column("Tokens In", justify="right")
            prov_table.add_column("Tokens Out", justify="right")
            prov_table.add_column("Cost", justify="right", style="green")
            prov_table.add_column("% of Total", justify="right")

            for provider, data in summary.by_provider.items():
                pct = (
                    (data["cost"] / summary.total_cost * 100)
                    if summary.total_cost > 0
                    else 0.0
                )
                prov_table.add_row(
                    provider,
                    f"{data['calls']:,}",
                    f"{data['tokens_in']:,}",
                    f"{data['tokens_out']:,}",
                    f"${data['cost']:.4f}",
                    f"{pct:.1f}%",
                )
            console.print(prov_table)

        # Model breakdown
        if summary.by_model:
            model_table = Table(title="Cost by Model")
            model_table.add_column("Model", style="cyan")
            model_table.add_column("Calls", justify="right")
            model_table.add_column("Cost", justify="right", style="green")

            for model, data in summary.by_model.items():
                model_table.add_row(
                    model,
                    f"{data['calls']:,}",
                    f"${data['cost']:.4f}",
                )
            console.print(model_table)

        console.print()
    finally:
        db.close()


# ---- Budget ----

@cli.group()
def budget() -> None:
    """Manage monthly budget."""
    pass


@budget.command("set")
@click.argument("amount", type=float)
def budget_set(amount: float) -> None:
    """Set monthly budget in USD."""
    if amount <= 0:
        console.print("[red]Budget must be a positive number.[/red]")
        sys.exit(1)

    db, config, analyzer, alerter, exporter = _get_components()
    try:
        alerter.set_budget(amount)
        console.print(f"[green]Monthly budget set to ${amount:.2f}[/green]")
    finally:
        db.close()


@budget.command("status")
def budget_status() -> None:
    """Check budget status."""
    db, config, analyzer, alerter, exporter = _get_components()
    try:
        status = alerter.get_budget_status()

        console.print()
        if status["budget"] is None:
            console.print(f"[yellow]{status['message']}[/yellow]")
        else:
            style = "green"
            if status["is_over"]:
                style = "red"
            elif status["is_warning"]:
                style = "yellow"

            budget_table = Table(show_header=False, box=None, padding=(0, 2))
            budget_table.add_column("Metric", style="bold")
            budget_table.add_column("Value")
            budget_table.add_row("Monthly Budget", f"${status['budget']:.2f}")
            budget_table.add_row("Spent", f"[{style}]${status['spent']:.4f}[/{style}]")
            budget_table.add_row("Remaining", f"${status['remaining']:.4f}")
            budget_table.add_row(
                "Used", f"[{style}]{status['percentage_used']:.1f}%[/{style}]"
            )
            console.print(Panel(budget_table, title="Budget Status", border_style=style))
            console.print(f"\n  {status['message']}")
        console.print()
    finally:
        db.close()


# ---- Export ----

@cli.command()
@click.option(
    "--format", "-f",
    type=click.Choice(["csv", "json"], case_sensitive=False),
    default="csv",
    help="Export format.",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path.")
@click.option("--provider", default=None, help="Filter by provider.")
@click.option("--limit", "-n", type=int, default=10000, help="Max records to export.")
def export(format: str, output: Optional[str], provider: Optional[str], limit: int) -> None:
    """Export usage data to CSV or JSON."""
    from pathlib import Path

    db, config, analyzer, alerter, exporter = _get_components()
    try:
        output_path = Path(output) if output else None
        path = exporter.export(
            format=format,
            provider=provider,
            output_path=output_path,
            limit=limit,
        )
        console.print(f"[green]Exported to: {path}[/green]")
    finally:
        db.close()


# ---- Providers ----

@cli.command()
@click.option(
    "--period", "-p",
    type=click.Choice(["day", "week", "month", "year"], case_sensitive=False),
    default="month",
    help="Time period for comparison.",
)
def providers(period: str) -> None:
    """Compare provider costs."""
    db, config, analyzer, alerter, exporter = _get_components()
    try:
        comparisons = analyzer.provider_comparison(period)

        if not comparisons:
            console.print("[yellow]No usage data found for the given period.[/yellow]")
            return

        console.print()
        table = Table(title=f"Provider Comparison ({period})")
        table.add_column("Provider", style="cyan")
        table.add_column("Model", style="cyan")
        table.add_column("Calls", justify="right")
        table.add_column("Total Tokens", justify="right")
        table.add_column("Total Cost", justify="right", style="green")
        table.add_column("Avg $/Call", justify="right")
        table.add_column("$/1K Tokens", justify="right")

        for comp in comparisons:
            table.add_row(
                comp.provider,
                comp.model,
                f"{comp.total_calls:,}",
                f"{comp.total_tokens:,}",
                f"${comp.total_cost:.4f}",
                f"${comp.avg_cost_per_call:.6f}",
                f"${comp.cost_per_1k_tokens:.6f}",
            )

        console.print(table)
        console.print()
    finally:
        db.close()


# ---- History ----

@cli.command()
@click.option("--limit", "-n", type=int, default=20, help="Number of recent calls to show.")
@click.option("--provider", default=None, help="Filter by provider.")
def history(limit: int, provider: Optional[str]) -> None:
    """Show recent API call history."""
    db, config, analyzer, alerter, exporter = _get_components()
    try:
        records = analyzer.get_recent_calls(limit=limit)

        if provider:
            records = [r for r in records if r.provider == provider]

        if not records:
            console.print("[yellow]No usage records found.[/yellow]")
            return

        console.print()
        table = Table(title="Recent API Calls")
        table.add_column("Time", style="dim")
        table.add_column("Provider", style="cyan")
        table.add_column("Model", style="cyan")
        table.add_column("Tokens In", justify="right")
        table.add_column("Tokens Out", justify="right")
        table.add_column("Cost", justify="right", style="green")
        table.add_column("Latency", justify="right")
        table.add_column("Status", justify="center")

        for record in records:
            ts = record.timestamp.strftime("%Y-%m-%d %H:%M") if record.timestamp else ""
            status = "[green]OK[/green]" if record.success else "[red]FAIL[/red]"
            table.add_row(
                ts,
                record.provider,
                record.model,
                f"{record.tokens_in:,}",
                f"{record.tokens_out:,}",
                f"${record.cost:.6f}",
                f"{record.latency_ms:.0f}ms",
                status,
            )

        console.print(table)
        console.print()
    finally:
        db.close()


# ---- Config info ----

@cli.command("config")
def show_config() -> None:
    """Show current configuration."""
    config = Config()

    console.print()
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Key", style="bold")
    info_table.add_column("Value")
    info_table.add_row("Database", str(config.db_path))
    info_table.add_row("Export Dir", str(config.export_dir))
    budget_val = f"${config.monthly_budget:.2f}" if config.monthly_budget else "Not set"
    info_table.add_row("Monthly Budget", budget_val)
    info_table.add_row("Warn Threshold", f"{config.warn_threshold * 100:.0f}%")

    providers = config.list_providers()
    info_table.add_row("Pricing Providers", ", ".join(providers))

    console.print(Panel(info_table, title="Configuration", border_style="blue"))

    # Show available models
    for prov in providers:
        models = config.list_models(prov)
        console.print(f"\n  [cyan]{prov}[/cyan]: {', '.join(models)}")
    console.print()


if __name__ == "__main__":
    cli()
