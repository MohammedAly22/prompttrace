"""
PromptTrace — Lightweight prompt versioning & eval tracker for LLM engineers.

Usage:
    from prompttrace import trace, dashboard

    @trace(experiment="my-experiment")
    def generate(prompt, **kwargs):
        # your LLM call here
        return llm_output

    # Launch the dashboard
    dashboard()
"""

__version__ = "0.1.0"

from prompttrace.core import trace, log_call, dashboard, get_db_path, set_db_path

__all__ = ["trace", "log_call", "dashboard", "get_db_path", "set_db_path", "__version__"]