"""`aicartographer` command-line entry point."""
from __future__ import annotations

import contextlib
import logging
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import click
import httpx
import uvicorn
from rich.console import Console

from .models import LLMKind, ScanRequest

console = Console()
log = logging.getLogger(__name__)


def _free_port(preferred: int = 0) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", preferred))
        return s.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=0.5)
            if r.status_code == 200:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.1)
    return False


@click.group()
@click.version_option(package_name="aicartographer")
def main() -> None:
    """AICodeCartographer - scan a project, explore it as a dashboard."""


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option(
    "--llm",
    type=click.Choice(["none", "anthropic", "openai", "ollama"]),
    default="none",
    help="LLM provider to use for module summaries.",
)
@click.option("--model", default=None, help="Model name (provider-specific).")
@click.option("--port", type=int, default=0, help="Port to bind (0 = pick a free one).")
@click.option("--host", default="127.0.0.1", help="Host to bind.")
@click.option("--no-open", is_flag=True, help="Do not open the browser.")
@click.option("--max-files", type=int, default=None, help="Cap files scanned (debug).")
def scan(
    path: str,
    llm: LLMKind,
    model: str | None,
    port: int,
    host: str,
    no_open: bool,
    max_files: int | None,
) -> None:
    """Scan PATH and open the interactive dashboard."""
    target = Path(path).resolve()
    if not target.is_dir():
        raise click.UsageError(f"{target} is not a directory")

    if port == 0:
        port = _free_port()

    base = f"http://{host}:{port}"
    console.print(f"[bold cyan]AICodeCartographer[/bold cyan] scanning [bold]{target}[/bold]")
    console.print(f"Server: [link]{base}[/link]   LLM: [yellow]{llm}[/yellow]")

    server_thread = threading.Thread(
        target=_run_uvicorn,
        kwargs={"host": host, "port": port},
        daemon=True,
    )
    server_thread.start()

    if not _wait_for_server(f"{base}/api/health"):
        console.print("[red]Server failed to start.[/red]")
        sys.exit(1)

    try:
        req = ScanRequest(path=str(target), llm=llm, model=model, max_files=max_files)
        r = httpx.post(f"{base}/api/scans", json=req.model_dump(), timeout=10.0)
        r.raise_for_status()
        scan_id = r.json()["scan_id"]
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to start scan:[/red] {exc}")
        sys.exit(1)

    dashboard = f"{base}/?scan={scan_id}"
    console.print(f"Dashboard: [bold link]{dashboard}[/bold link]")
    if not no_open:
        with contextlib.suppress(Exception):
            webbrowser.open(dashboard)

    console.print("[dim]Press Ctrl+C to stop.[/dim]")
    try:
        while server_thread.is_alive():
            server_thread.join(timeout=1.0)
    except KeyboardInterrupt:
        console.print("\n[bold]Bye.[/bold]")


@main.command(name="serve")
@click.option("--host", default="127.0.0.1")
@click.option("--port", type=int, default=8765)
def serve(host: str, port: int) -> None:
    """Start the server without launching a scan (useful for development)."""
    _run_uvicorn(host=host, port=port)


@main.command()
def mcp() -> None:
    """Run the MCP stdio server (tools for Cursor and other agents)."""
    from .mcp_server import run_stdio

    console.print("[bold cyan]AICodeCartographer MCP[/bold cyan] (stdio)")
    run_stdio()


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--port", type=int, default=0, help="Port to bind (0 = pick a free one).")
@click.option("--host", default="127.0.0.1", help="Host to bind.")
@click.option("--no-open", is_flag=True, help="Do not open the browser.")
def watch(path: str, port: int, host: str, no_open: bool) -> None:
    """Scan PATH and keep the dashboard live while files change."""
    target = Path(path).resolve()
    if port == 0:
        port = _free_port()
    base = f"http://{host}:{port}"
    server_thread = threading.Thread(
        target=_run_uvicorn,
        kwargs={"host": host, "port": port},
        daemon=True,
    )
    server_thread.start()
    if not _wait_for_server(f"{base}/api/health"):
        console.print("[red]Server failed to start.[/red]")
        sys.exit(1)
    req = ScanRequest(path=str(target), llm="none")
    r = httpx.post(f"{base}/api/scans", json=req.model_dump(), timeout=10.0)
    r.raise_for_status()
    scan_id = r.json()["scan_id"]
    console.print(f"Waiting for scan [dim]{scan_id}[/dim]…")
    deadline = time.time() + 600
    while time.time() < deadline:
        st = httpx.get(f"{base}/api/scans/{scan_id}", timeout=5.0).json()
        if st.get("state") in ("done", "error"):
            break
        time.sleep(0.5)
    httpx.post(f"{base}/api/scans/{scan_id}/watch", timeout=10.0)
    dashboard = f"{base}/?scan={scan_id}"
    console.print(f"Watch mode on. Dashboard: [link]{dashboard}[/link]")
    if not no_open:
        with contextlib.suppress(Exception):
            webbrowser.open(dashboard)
    console.print("[dim]Press Ctrl+C to stop.[/dim]")
    try:
        while server_thread.is_alive():
            server_thread.join(timeout=1.0)
    except KeyboardInterrupt:
        httpx.delete(f"{base}/api/scans/{scan_id}/watch", timeout=5.0)
        console.print("\n[bold]Bye.[/bold]")


def _run_uvicorn(host: str, port: int) -> None:
    uvicorn.run(
        "aicartographer.server:app",
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()
