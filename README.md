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

@track(provider="anthropic", model="claude-sonnet-4-20250514")
def ask_claude(prompt):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": prompt}],
    )
    return response  # Tokens auto-extracted from response.usage
```

**Context Manager:**

```python
from agentmon import UsageTracker

tracker = UsageTracker()
with tracker.track("anthropic", "claude-sonnet-4-20250514") as t:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
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
| Anthropic | Claude Opus 4 | $15.00 | $75.00 |
| Anthropic | Claude Sonnet 4 | $3.00 | $15.00 |
| Anthropic | Claude 3.5 Haiku | $0.80 | $4.00 |
| OpenAI | GPT-4o | $2.50 | $10.00 |
| OpenAI | GPT-4o Mini | $0.15 | $0.60 |
| Google | Gemini 2.5 Pro | $1.25 | $10.00 |
| Google | Gemini 2.5 Flash | $0.15 | $0.60 |
| DeepSeek | DeepSeek V3 | $0.27 | $1.10 |
| DeepSeek | DeepSeek R1 | $0.55 | $2.19 |
| Moonshot | Kimi V1 8K | $1.44 | $1.44 |

## Configuration

Configuration is stored at `~/.agent-monitor/config.yaml`. You can also edit the defaults in `config/default.yaml`.

## License

MIT License - Copyright (c) 2026 Jaxz714
