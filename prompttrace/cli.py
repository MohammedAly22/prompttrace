"""CLI entry point for PromptTrace."""

import sys
from rich.console import Console

console = Console()


def main():
    from prompttrace.core import dashboard, ACCENT, _print_banner

    args = sys.argv[1:]
    port = 8777
    host = "127.0.0.1"

    for i, arg in enumerate(args):
        if arg in ("--port", "-p") and i + 1 < len(args):
            port = int(args[i + 1])
        elif arg in ("--host", "-h") and i + 1 < len(args):
            host = args[i + 1]
        elif arg == "--help":
            _print_banner()
            console.print("  [bold]Usage:[/] prompttrace [options]")
            console.print(f"  [bold]  --port, -p[/]  [dim]Port number (default: 8777)[/]")
            console.print(f"  [bold]  --host[/]       [dim]Host address (default: 127.0.0.1)[/]")
            console.print(f"  [bold]  --help[/]       [dim]Show this help[/]")
            console.print()
            return

    dashboard(host=host, port=port)


if __name__ == "__main__":
    main()