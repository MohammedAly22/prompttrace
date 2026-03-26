<div align="center">
  <br />
  <img src="prompttrace/logo.png" alt="PromptTrace" width="120" height="120" style="border-radius: 24px;" />
  <h1>
    <code style="background: none; font-size: 32px;">PromptTrace</code>
  </h1>
  <p><strong>Stop losing your best prompts.</strong></p>
  <p>
    <em>Lightweight prompt versioning & evaluation tracker for LLM engineers.<br/>
    One decorator. Automatic versioning. Local SQLite. Beautiful dashboard.</em>
  </p>

  <br />

  <a href="https://pypi.org/project/prompttrace/"><img src="https://img.shields.io/pypi/v/prompttrace?style=for-the-badge&logo=pypi&logoColor=C6F808&label=PyPI&color=111111" alt="PyPI" /></a>
  &nbsp;
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.9+-111111?style=for-the-badge&logo=python&logoColor=C6F808" alt="Python" /></a>
  &nbsp;
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-111111?style=for-the-badge" alt="License" /></a>
  &nbsp;
  <a href="#"><img src="https://img.shields.io/badge/Dependencies-1_(rich)-111111?style=for-the-badge" alt="Deps" /></a>

  <br />
  <br />

  <p>
    <a href="#-quick-start">Quick Start</a>&nbsp;&nbsp;•&nbsp;&nbsp;
    <a href="#-features">Features</a>&nbsp;&nbsp;•&nbsp;&nbsp;
    <a href="#-dashboard">Dashboard</a>&nbsp;&nbsp;•&nbsp;&nbsp;
    <a href="#-api-reference">API Reference</a>&nbsp;&nbsp;•&nbsp;&nbsp;
    <a href="#%EF%B8%8F-configuration">Configuration</a>
  </p>

  <br />
</div>

---

<br />

## The Problem

You iterate on prompts **50 times a day**. You had a great system prompt last Tuesday that got 92% accuracy — but you lost it. You changed one word and everything broke, but you can't remember which word.

Your eval scores live in scattered notebooks and `print()` statements.

**PromptTrace fixes this.** → `pip install prompttrace` → done.

<br />

## 📦 Installation

```bash
pip install prompttrace
```

> **Requirements:** Python 3.9+ · Single dependency: `rich`

<br />

## 🚀 Quick Start

### 1 → Decorate your LLM calls

```python
from prompttrace import trace

@trace(experiment="my-chatbot", model="gpt-4o")
def generate(prompt, temperature=0.7):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content

# Every call is now automatically tracked
generate("Explain quantum computing in one sentence.", temperature=0.3)
generate("Explain quantum computing in one sentence.", temperature=0.9)
```

### 2 → Launch the dashboard

```python
from prompttrace import dashboard

dashboard()  # → http://127.0.0.1:8777
```

Or from the terminal:

```bash
prompttrace
```

That's it. Every prompt, output, latency, model, and generation parameter is logged and visualized.

<br />

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🎯 | **`@trace` decorator** | Wrap any LLM call — auto-logs prompt, output, latency, params |
| 📝 | **`log_call()` function** | Manual logging for when you can't use a decorator |
| 📊 | **Auto eval** | Pass an `eval_fn` to score outputs automatically |
| 🔀 | **Prompt versioning** | Every unique prompt gets a hash — see how changes affect results |
| ⚖️ | **Side-by-side compare** | Diff two prompts word-by-word, see outputs and metrics |
| 🖥️ | **Web dashboard** | Modern UI with animated charts, tables, filters — zero JS deps |
| 🔒 | **Local-only** | Everything in SQLite. No cloud. No API keys. No telemetry |
| 🎨 | **Rich terminal logs** | Colorful, emoji-powered console output via `rich` |
| 🔄 | **Real-time updates** | Dashboard auto-refreshes every 2s — no manual reload |
| 🗑️ | **Experiment management** | Delete experiments, filter dashboard by experiment |
| 📤 | **CSV export** | One-click export of all traces for external analysis |

<br />

## 🖥️ Dashboard

Launch with `prompttrace` or `from prompttrace import dashboard; dashboard()`.

**Three views:**

| View | What it does |
|---|---|
| **Dashboard** | Stats cards, latency chart, status donut, model usage — filterable by experiment |
| **Traces** | Full table of all logged calls with search, filter, delete, and CSV export |
| **Compare** | Select two prompts → word-level diff highlighting with outputs side-by-side |

<br />

## 📖 Usage Guide

### The `@trace` Decorator

```python
from prompttrace import trace

@trace(
    experiment="summarizer",       # Group related traces
    model="claude-3-sonnet",       # Model identifier
    tags=["prod", "v2"],           # Optional tags
    description="Q3 summary bot",  # Optional experiment description
)
def summarize(prompt, temperature=0.5, max_tokens=500):
    # Your LLM call here
    return llm_response
```

**What gets logged automatically:**

> Prompt text · Output · Latency · Generation parameters (`temperature`, `top_p`, `max_tokens`, etc.) · Input variables · Status (`success` / `error`) · Error messages · Approximate token counts

<br />

### Returning Metadata

Return a dict to include token counts:

```python
@trace(experiment="qa", model="gpt-4o")
def answer(prompt):
    resp = openai.chat.completions.create(...)
    return {
        "output": resp.choices[0].message.content,
        "token_count_input": resp.usage.prompt_tokens,
        "token_count_output": resp.usage.completion_tokens,
    }
```

<br />

### Auto Evaluation

Pass an `eval_fn` to score every output automatically:

```python
def my_eval(prompt, output):
    """Return a dict of metric_name: score."""
    return {
        "relevance": compute_relevance(prompt, output),
        "length_ok": 1.0 if 50 < len(output) < 500 else 0.0,
        "has_citation": 1.0 if "[source]" in output else 0.0,
    }

@trace(experiment="research-bot", model="gpt-4o", eval_fn=my_eval)
def research(prompt):
    return call_llm(prompt)
```

Metrics appear in the terminal and the dashboard.

<br />

### Manual Logging with `log_call()`

For cases where a decorator doesn't fit:

```python
from prompttrace import log_call
import time

start = time.perf_counter()
output = my_llm_pipeline(prompt)
elapsed = (time.perf_counter() - start) * 1000

log_call(
    prompt="Translate to French: Hello world",
    output="Bonjour le monde",
    experiment="translation",
    model="gpt-4o-mini",
    generation_params={"temperature": 0.2},
    latency_ms=elapsed,
    token_count_input=8,
    token_count_output=5,
    tags=["translation", "french"],
    eval_metrics={"bleu": 0.95, "fluency": 0.88},
)
```

<br />

### CLI

```bash
# Default (localhost:8777)
prompttrace

# Custom port
prompttrace --port 9000

# Accessible from network
prompttrace --host 0.0.0.0 --port 8777
```

<br />

## 📋 API Reference

### `@trace(...)`

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `experiment` | `str` | `"default"` | Experiment name for grouping |
| `model` | `str` | `"unknown"` | Model identifier |
| `tags` | `list[str]` | `None` | Optional tags |
| `eval_fn` | `callable` | `None` | `fn(prompt, output) → dict[str, float]` |
| `description` | `str` | `""` | Experiment description |

### `log_call(...)`

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `prompt` | `str` | *required* | The prompt template |
| `output` | `str` | *required* | The LLM output |
| `experiment` | `str` | `"default"` | Experiment name |
| `model` | `str` | `"unknown"` | Model identifier |
| `generation_params` | `dict` | `None` | e.g. `{"temperature": 0.7}` |
| `input_variables` | `dict` | `None` | Template variables |
| `latency_ms` | `float` | `0` | Response time in ms |
| `token_count_input` | `int` | `0` | Input token count |
| `token_count_output` | `int` | `0` | Output token count |
| `status` | `str` | `"success"` | `"success"` or `"error"` |
| `error_message` | `str` | `""` | Error details |
| `tags` | `list[str]` | `None` | Optional tags |
| `eval_metrics` | `dict` | `None` | `{"metric": score}` |

### `dashboard(host, port)`

Launches the web UI. Blocks until `Ctrl+C`.

<br />

## ⚙️ Configuration

### Database Location

By default, traces are stored in `.prompttrace/traces.db` in the current directory.

```bash
# Override via environment variable
export PROMPTTRACE_DB=/path/to/my/traces.db
```

```python
# Override programmatically
from prompttrace import set_db_path
set_db_path("/path/to/my/traces.db")
```

<br />

## 📁 Project Structure

```
your-project/
├── pyproject.toml
├── README.md
├── example.py
└── prompttrace/
    ├── __init__.py          # Public API exports
    ├── core.py              # @trace decorator, log_call, dashboard launcher
    ├── db.py                # SQLite database layer
    ├── server.py            # Built-in HTTP server + JSON API
    ├── cli.py               # CLI entry point
    ├── dashboard.html       # Single-file web dashboard (zero JS deps)
    └── logo.png             # App logo
```


<br />

## 📄 License

MIT — use it however you want.

<br />

---

<div align="center">
  <br />
  <img src="prompttrace/logo.png" alt="" width="32" height="32" style="border-radius: 8px;" />
  <br />
  <strong>PromptTrace</strong>
  <br />
  <sub>Stop losing your best prompts.</sub>
  <br />
  <br />
</div>