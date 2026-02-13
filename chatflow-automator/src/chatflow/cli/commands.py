"""CLI commands using Click."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live

from ..core.engine import Engine
from ..core.events import EventEmitter
from ..core.types import TaskStatus, ConnectionConfig, BrowserConfig, ProxyConfig
from ..storage.config import ConfigManager
from ..storage.results import ResultsManager
from ..tasks.loader import TaskLoader
from ..utils.paths import get_config_path, get_data_dir, get_results_dir
from ..utils.logging import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--config', '-c', type=click.Path(), help='Config file path')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: Optional[str]) -> None:
    """ChatFlow Automator - Browser automation for chat interfaces."""
    ctx.ensure_object(dict)
    
    # Setup logging
    level = "DEBUG" if verbose else "INFO"
    setup_logging(level=level)
    
    # Load config
    config_path = Path(config) if config else get_config_path()
    ctx.obj['config'] = ConfigManager(config_path)
    try:
        ctx.obj['config'].load()
    except Exception as e:
        if verbose:
            console.print(f"[yellow]Warning: Could not load config: {e}[/yellow]")


@cli.command()
@click.option('--url', '-u', required=True, help='Target URL')
@click.option('--tasks', '-t', required=True, type=click.Path(exists=True), help='Tasks file (JSON/YAML/TXT)')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.option('--cookies', type=click.Path(exists=True), help='Cookies file')
@click.option('--proxy', help='Proxy URL (e.g., socks5://127.0.0.1:1080)')
@click.option('--headless', is_flag=True, help='Run browser in headless mode')
@click.option('--adapter', default='generic', help='Adapter name')
@click.pass_context
def run(
    ctx: click.Context,
    url: str,
    tasks: str,
    output: Optional[str],
    cookies: Optional[str],
    proxy: Optional[str],
    headless: bool,
    adapter: str
) -> None:
    """Run a task sequence."""
    config_manager: ConfigManager = ctx.obj['config']
    
    console.print(f"[bold blue]ChatFlow Automator[/bold blue]")
    console.print(f"URL: {url}")
    console.print(f"Tasks: {tasks}")
    
    # Parse proxy
    proxy_config = ProxyConfig()
    if proxy:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(proxy)
            proxy_config = ProxyConfig(
                enabled=True,
                type=parsed.scheme or "http",
                host=parsed.hostname or "",
                port=parsed.port or 0,
                username=parsed.username,
                password=parsed.password,
            )
            console.print(f"Proxy: {proxy_config.type}://{proxy_config.host}:{proxy_config.port}")
        except Exception as e:
            console.print(f"[red]Invalid proxy URL: {e}[/red]")
            sys.exit(1)
    
    # Build connection config
    browser_config = BrowserConfig(
        headless=headless,
        hide_automation=True,
        proxy=proxy_config,
    )
    
    connection_config = ConnectionConfig(
        url=url,
        cookies_file=cookies,
        adapter_name=adapter,
        browser=browser_config,
        adapter_settings=config_manager.get("adapter_settings", {}),
    )
    
    # Load tasks
    loader = TaskLoader()
    try:
        sequence = loader.load_from_file(tasks)
        console.print(f"Loaded {len(sequence.cards)} tasks")
    except Exception as e:
        console.print(f"[red]Failed to load tasks: {e}[/red]")
        sys.exit(1)
    
    # Setup results manager
    output_path = Path(output) if output else None
    results_manager = ResultsManager(get_results_dir())
    
    # Run
    async def execute():
        engine = Engine()
        
        try:
            # Connect
            with console.status("[bold green]Connecting to browser..."):
                await engine.connect(connection_config)
            
            console.print("[green]✓ Connected[/green]")
            
            # Execute with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                
                task_progress = progress.add_task(
                    f"Executing {sequence.name}",
                    total=len(sequence.enabled_cards)
                )
                
                async for result in engine.executor.execute_sequence(sequence):
                    status_icon = "✓" if result.status == TaskStatus.COMPLETED else "✗"
                    console.print(f"  {status_icon} {result.task_name} ({result.duration_seconds:.1f}s)")
                    progress.advance(task_progress)
            
            # Get session result
            session = engine.executor._current_task  # Simplified
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise
        finally:
            await engine.disconnect()
            console.print("[green]✓ Disconnected[/green]")
    
    # Run async
    try:
        asyncio.run(execute())
        console.print("[bold green]Execution completed![/bold green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Execution failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def list_sessions(ctx: click.Context) -> None:
    """List saved sessions."""
    results_manager = ResultsManager(get_results_dir())
    sessions = results_manager.list_sessions()
    
    if not sessions:
        console.print("[yellow]No sessions found[/yellow]")
        return
    
    table = Table(title="Saved Sessions")
    table.add_column("Date", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Total", justify="right")
    table.add_column("Done", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Session ID", style="dim")
    
    for session in sessions[:20]:
        started = session.get("started_at", "")[:19].replace("T", " ")
        table.add_row(
            started,
            session.get("sequence_name", ""),
            str(session.get("total_tasks", 0)),
            str(session.get("completed_tasks", 0)),
            str(session.get("failed_tasks", 0)),
            session.get("session_id", "")[:20],
        )
    
    console.print(table)


@cli.command()
@click.argument('session_id')
@click.option('--format', '-f', type=click.Choice(['json', 'markdown', 'csv']), default='json')
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.pass_context
def export(ctx: click.Context, session_id: str, format: str, output: Optional[str]) -> None:
    """Export session results."""
    from ..storage.export import get_exporter
    
    results_manager = ResultsManager(get_results_dir())
    
    # Find session
    sessions = results_manager.list_sessions()
    matching = [s for s in sessions if s.get("session_id", "").startswith(session_id)]
    
    if not matching:
        console.print(f"[red]Session not found: {session_id}[/red]")
        sys.exit(1)
    
    if len(matching) > 1:
        console.print(f"[yellow]Multiple sessions match, using first:[/yellow]")
        for s in matching[:5]:
            console.print(f"  - {s.get('session_id')}")
    
    full_session_id = matching[0].get("session_id")
    
    try:
        session = results_manager.load_session(full_session_id)
    except Exception as e:
        console.print(f"[red]Failed to load session: {e}[/red]")
        sys.exit(1)
    
    # Export
    exporter = get_exporter(format)
    
    if output:
        output_path = Path(output)
    else:
        ext_map = {"json": ".json", "markdown": ".md", "csv": ".csv"}
        output_path = get_results_dir() / f"{full_session_id}{ext_map[format]}"
    
    try:
        exporter.export(session, output_path)
        console.print(f"[green]Exported to: {output_path}[/green]")
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.pass_context
def validate(ctx: click.Context, file_path: str) -> None:
    """Validate a tasks file."""
    from ..tasks.validator import TaskValidator
    
    loader = TaskLoader()
    validator = TaskValidator()
    
    try:
        sequence = loader.load_from_file(file_path)
        errors = validator.validate_sequence(sequence)
        
        if errors:
            console.print(f"[red]Validation failed:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            sys.exit(1)
        else:
            console.print(f"[green]✓ Valid[/green]")
            console.print(f"  Name: {sequence.name}")
            console.print(f"  Cards: {len(sequence.cards)}")
            console.print(f"  Enabled: {len(sequence.enabled_cards)}")
    except Exception as e:
        console.print(f"[red]Failed to load file: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def gui(ctx: click.Context) -> None:
    """Launch the GUI application."""
    from ..app import main as app_main
    sys.exit(app_main())


@cli.command()
def version() -> None:
    """Show version information."""
    from .. import __version__
    console.print(f"ChatFlow Automator v{__version__}")


def main() -> int:
    """Main entry point for CLI."""
    try:
        cli(obj={})
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
