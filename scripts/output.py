"""
Unified output formatting module for clean console output.
"""
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def info(message: str) -> None:
    """Print an informational message."""
    console.print(f"[dim]ℹ[/dim] {message}")


def success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]✗[/red] {message}")


def step(step_num: int, total: int, message: str) -> None:
    """Print a step message."""
    console.print(f"[blue][{step_num}/{total}][/blue] {message}")


def header(title: str) -> None:
    """Print a header."""
    console.print()
    console.print(Panel(title, border_style="blue", padding=(0, 1)))
    console.print()


def print_table(headers: list, rows: list, title: str = "") -> None:
    """Print a table."""
    table = Table(title=title, show_header=True, header_style="bold blue")
    for header in headers:
        table.add_column(header)
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    console.print(table)


def print_summary(items: list) -> None:
    """Print summary items."""
    for item in items:
        if isinstance(item, dict):
            for key, value in item.items():
                console.print(f"  {key}: {value}")
        else:
            console.print(f"  - {item}")


print_info = info
print_success = success
print_warning = warning
print_error = error
print_step = step
print_header = header
