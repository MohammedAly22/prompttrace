"""Core API: @trace decorator, log_call function, and dashboard launcher."""

import functools
import json
import time
import threading
from typing import Optional, Callable

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from prompttrace.db import (
    get_or_create_experiment,
    insert_trace,
    insert_eval,
    get_db_path,
    set_db_path,
)

console = Console()

ACCENT = "#C6F808"


def _print_banner():
    banner = Text()
    banner.append("⚡ ", style="bold")
    banner.append("PromptTrace", style=f"bold {ACCENT}")
    banner.append(" — prompt versioning & eval tracker", style="dim")
    console.print(Panel(banner, border_style="dim"))


def _print_trace_logged(trace_id: int, experiment: str, latency: float, status: str):
    status_icon = "✅" if status == "success" else "❌"
    console.print(
        f"  {status_icon}  "
        f"[dim]trace[/] [bold]#{trace_id}[/bold] "
        f"[dim]│[/] [bold {ACCENT}]{experiment}[/] "
        f"[dim]│[/] {latency:.0f}ms "
        f"[dim]│[/] {status}"
    )


def trace(
    experiment: str = "default",
    model: str = "unknown",
    tags: list = None,
    eval_fn: Optional[Callable] = None,
    description: str = "",
):
    """Decorator to trace an LLM call.

    The decorated function receives the prompt as its first argument.
    It should return the LLM output string (or a dict with 'output' and optional metadata).

    Args:
        experiment: Name of the experiment group.
        model: Model identifier (e.g., 'gpt-4', 'claude-3').
        tags: Optional list of tags.
        eval_fn: Optional function(prompt, output) -> dict[str, float] for auto-eval.
        description: Optional experiment description.

    Example:
        @trace(experiment="summarizer", model="gpt-4o")
        def summarize(prompt, temperature=0.7):
            return openai.chat(prompt, temperature=temperature)
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(prompt: str, *args, **kwargs):
            exp_id = get_or_create_experiment(experiment, description)

            # Extract generation params from kwargs
            gen_params = {
                k: v for k, v in kwargs.items()
                if k in {
                    "temperature", "top_p", "top_k", "max_tokens",
                    "frequency_penalty", "presence_penalty", "stop",
                    "seed", "response_format",
                }
            }

            input_vars = {
                k: v for k, v in kwargs.items()
                if k not in gen_params
            }

            start = time.perf_counter()
            status = "success"
            output = ""
            error_msg = ""
            token_in = 0
            token_out = 0

            try:
                result = fn(prompt, *args, **kwargs)

                if isinstance(result, dict):
                    output = result.get("output", str(result))
                    token_in = result.get("token_count_input", 0)
                    token_out = result.get("token_count_output", 0)
                    if result.get("model"):
                        gen_params["_actual_model"] = result["model"]
                else:
                    output = str(result)

            except Exception as e:
                status = "error"
                error_msg = str(e)
                raise
            finally:
                elapsed = (time.perf_counter() - start) * 1000

                trace_id = insert_trace(
                    experiment_id=exp_id,
                    prompt_template=prompt,
                    input_variables=input_vars,
                    output=output,
                    model=model,
                    generation_params=gen_params,
                    status=status,
                    latency_ms=round(elapsed, 2),
                    token_count_input=token_in,
                    token_count_output=token_out,
                    error_message=error_msg,
                    tags=tags,
                )

                _print_trace_logged(trace_id, experiment, elapsed, status)

                # Run eval if provided
                if eval_fn and status == "success":
                    try:
                        metrics = eval_fn(prompt, output)
                        if isinstance(metrics, dict):
                            for name, value in metrics.items():
                                insert_eval(trace_id, name, float(value))
                                console.print(
                                    f"       📊 [dim]{name}:[/] [bold {ACCENT}]{value}[/]"
                                )
                    except Exception as e:
                        console.print(f"       [red]⚠ eval error: {e}[/]")

            return result if status == "success" else None

        return wrapper
    return decorator


def log_call(
    prompt: str,
    output: str,
    experiment: str = "default",
    model: str = "unknown",
    generation_params: dict = None,
    input_variables: dict = None,
    latency_ms: float = 0,
    token_count_input: int = 0,
    token_count_output: int = 0,
    status: str = "success",
    error_message: str = "",
    tags: list = None,
    eval_metrics: dict = None,
) -> int:
    """Manually log an LLM call without the decorator.

    Returns the trace ID.
    """
    exp_id = get_or_create_experiment(experiment)
    trace_id = insert_trace(
        experiment_id=exp_id,
        prompt_template=prompt,
        input_variables=input_variables or {},
        output=output,
        model=model,
        generation_params=generation_params or {},
        status=status,
        latency_ms=latency_ms,
        token_count_input=token_count_input,
        token_count_output=token_count_output,
        error_message=error_message,
        tags=tags,
    )

    if eval_metrics:
        for name, value in eval_metrics.items():
            insert_eval(trace_id, name, float(value))

    _print_trace_logged(trace_id, experiment, latency_ms, status)
    return trace_id


def dashboard(host: str = "127.0.0.1", port: int = 8777):
    """Launch the PromptTrace web dashboard."""
    from prompttrace.server import run_server

    _print_banner()
    db_path = get_db_path()
    console.print(f"  📁 [dim]Database:[/] {db_path}")
    console.print(
        f"  🌐 [dim]Dashboard:[/] [bold underline {ACCENT}]http://{host}:{port}[/]"
    )
    console.print(f"  [dim]Press Ctrl+C to stop[/]\n")

    run_server(host, port)