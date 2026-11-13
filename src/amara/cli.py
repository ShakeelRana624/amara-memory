"""AMARA Command-Line Interface (CLI).

Provides commands for starting the API server, managing API keys,
running database migrations, executing background workers, and running benchmarks.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import click
import uvicorn
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

from amara.server.auth import APIKeyStore
from amara.worker import run_worker_main


@click.group()
@click.version_option(version="0.1.0", prog_name="amara")
def cli() -> None:
    """AMARA: Adaptive Memory Architecture for Reasoning and AI.

    Commercial Cognitive Memory Framework & Server.
    """


@cli.command("serve")
@click.option("--host", default="0.0.0.0", help="Host network interface to bind.")
@click.option("--port", default=8000, type=int, help="Port to listen on.")
@click.option("--reload", is_flag=True, help="Enable auto-reload for local development.")
@click.option("--workers", default=1, type=int, help="Number of Uvicorn worker processes.")
@click.option(
    "--storage",
    type=click.Choice(["memory", "postgres"]),
    default="postgres",
    help="Storage backend implementation.",
)
def serve_command(host: str, port: int, reload: bool, workers: int, storage: str) -> None:
    """Launch the AMARA FastAPI REST API server."""
    os.environ["AMARA_STORAGE_BACKEND"] = storage
    click.echo(f"Starting AMARA Server on http://{host}:{port} (storage: {storage})...")
    uvicorn.run(
        "amara.server.app:create_app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        factory=True,
    )


@cli.command("worker")
@click.option("--interval", default=60.0, type=float, help="Seconds between maintenance cycles.")
@click.option(
    "--storage",
    type=click.Choice(["memory", "postgres"]),
    default="postgres",
    help="Storage backend implementation.",
)
@click.option(
    "--tenants",
    default="default,production",
    help="Comma-separated tenant IDs to process.",
)
def worker_command(interval: float, storage: str, tenants: str) -> None:
    """Launch the AMARA background cognitive lifecycle worker."""
    tenant_list = [t.strip() for t in tenants.split(",") if t.strip()]
    click.echo(
        f"Starting AMARA Worker (interval: {interval}s, storage: {storage}, "
        f"tenants: {tenant_list})..."
    )
    asyncio.run(
        run_worker_main(
            interval=interval,
            storage=storage,
            tenants=tenant_list,
        )
    )


@cli.command("create-key")
@click.option("--tenant-id", required=True, help="Tenant identifier.")
@click.option("--name", default="Production Key", help="Human-readable label for key.")
@click.option(
    "--scopes",
    default="read,write",
    help="Comma-separated permission scopes (read, write, admin).",
)
@click.option("--workspace-id", default=None, help="Optional workspace scope.")
def create_key_command(
    tenant_id: str,
    name: str,
    scopes: str,
    workspace_id: str | None,
) -> None:
    """Provision a new secure cryptographic API key for a tenant."""
    scope_set = {s.strip() for s in scopes.split(",") if s.strip()}
    store = APIKeyStore()
    record, raw_key = store.create_key(
        tenant_id=tenant_id,
        name=name,
        scopes=scope_set,
        workspace_id=workspace_id,
    )

    click.echo("\n" + "=" * 60)
    click.echo("AMARA SECURE API KEY GENERATED")
    click.echo("=" * 60)
    click.echo(f"Key ID:       {record.key_id}")
    click.echo(f"Tenant ID:    {record.tenant_id}")
    click.echo(f"Name:         {record.name}")
    click.echo(f"Scopes:       {', '.join(sorted(record.scopes))}")
    click.echo("-" * 60)
    click.echo(f"API Key:      {raw_key}")
    click.echo("-" * 60)
    click.echo("WARNING: Copy this API key now. It will NEVER be displayed again.")
    click.echo("=" * 60 + "\n")


@cli.command("migrate")
@click.option("--direction", type=click.Choice(["up", "down"]), default="up")
@click.option("--revision", default="head", help="Alembic revision target.")
def migrate_command(direction: str, revision: str) -> None:
    """Run database schema migrations using Alembic."""
    alembic_cfg = AlembicConfig("alembic.ini")
    click.echo(f"Running database migration: {direction} ({revision})...")
    if direction == "up":
        alembic_command.upgrade(alembic_cfg, revision)
    else:
        alembic_command.downgrade(alembic_cfg, revision)
    click.echo("Migration complete.")


@cli.command("benchmark")
@click.option("--seed", default=42, type=int, help="Deterministic random seed.")
def benchmark_command(seed: int) -> None:
    """Run the empirical research evaluation benchmark suite."""
    click.echo(f"Launching AMARA Benchmark Harness (seed={seed})...")
    script = Path("benchmarks") / "run_benchmarks.py"
    if not script.exists():
        click.echo(f"Error: Benchmark runner script not found at {script}", err=True)
        sys.exit(1)
    result = subprocess.run([sys.executable, str(script), "--seed", str(seed)], check=False)
    sys.exit(result.returncode)


@cli.command("info")
def info_command() -> None:
    """Display AMARA version, license, and architectural information."""
    click.echo("\n" + "=" * 60)
    click.echo("AMARA: Adaptive Memory Architecture for Reasoning and AI")
    click.echo("Version:     0.1.0 (Commercial Release)")
    click.echo("License:     Proprietary Commercial Software License")
    click.echo("Copyright:   (c) 2026 AMARA. All Rights Reserved.")
    click.echo("Python:      " + sys.version.split()[0])
    click.echo("=" * 60 + "\n")


if __name__ == "__main__":
    cli()
