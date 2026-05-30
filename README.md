[English](README.md) | [中文](README_CN.md)

# Agent Monitor

Cost and usage monitoring for AI API calls. Track spending, set budgets, compare providers, never overspend again.

## Features

- **Automatic Tracking** - Wrap any LLM API call to log provider, model, tokens, cost, latency, and success/failure
- **SQLite Storage** - All data stored locally at `~/.agent-monitor/usage.db`
- **Dashboard** - Daily, weekly, monthly, and yearly cost breakdowns
- **Budget Alerts** - Set monthly budgets and get warned when approaching limits
- **Provider Comparison** - See which provider is cheapest for your usage pattern
- **CSV/JSON Export** - Export your usage data for analysis
- **Python Integration** - Use as a decorator or context manager

## Installation

```bash
pip install agent-monitor
```

Or install from source:

```bash
git clone https://github.com/Jaxz714/agent-monitor.git
cd agent-monitor
pip install .
```

## Quick Start

### Python API

**Decorator:**

```python
from agentmon import track

@track(provider="anthropic", model="claude-sonnet-4-6")
def ask_claude(prompt):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": prompt}],
    )
    return response  # Tokens auto-extracted from response.usage
```

**Context Manager:**

```python
from agentmon import UsageTracker

tracker = UsageTracker()
with tracker.track("anthropic", "claude-sonnet-4-6") as t:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    t.record(
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
    )
```

### CLI Commands

```bash
# Show cost dashboard (monthly view by default)
agentmon dashboard
agentmon dashboard --period week

# Budget management
agentmon budget set 100      # Set $100 monthly budget
agentmon budget status       # Check remaining budget

# Export data
agentmon export --format csv
agentmon export --format json --output ~/my-usage.json

# Compare providers
agentmon providers

# View recent calls
agentmon history
agentmon history --limit 50

# Show configuration
agentmon config
```

## Pricing Data

Includes built-in pricing for common models:

| Provider | Model | Input ($/1M tokens) | Output ($/1M tokens) |
|----------|-------|---------------------|----------------------|
| Anthropic | Claude Opus 4.8 | $5.00 | $25.00 |
| Anthropic | Claude Sonnet 4.6 | $3.00 | $15.00 |
| Anthropic | Claude Haiku 4.5 | $1.00 | $5.00 |
| OpenAI | GPT-5.5 | $5.00 | $30.00 |
| OpenAI | GPT-5.4 | $2.50 | $15.00 |
| OpenAI | GPT-5.4 Mini | $0.75 | $4.50 |
| OpenAI | GPT-5.4 Nano | $0.20 | $1.25 |
| OpenAI | Deep Research | $5.00 | $20.00 |
| OpenAI | Deep Research Mini | $1.00 | $4.00 |
| Google | Gemini 3.5 Flash | $1.50 | $9.00 |
| Google | Gemini 2.5 Pro | $1.25 | $10.00 |
| Google | Gemini 2.5 Flash | $0.30 | $2.50 |
| Google | Gemini 3.1 Flash-Lite | $0.25 | $1.50 |
| DeepSeek | DeepSeek V4 Flash | $0.14 | $0.28 |
| DeepSeek | DeepSeek V4 Pro | $1.74 | $3.48 |
| Moonshot | Kimi K2.6 | $0.684 | $3.42 |

## Configuration

Configuration is stored at `~/.agent-monitor/config.yaml`. You can also edit the defaults in `config/default.yaml`.

## License

MIT License - Copyright (c) 2026 Jaxz714
