[English](README.md) | [中文](README_CN.md)

# Agent Monitor

AI API 调用的成本与用量监控工具。追踪支出、设置预算、对比服务商，从此告别超支。

## 功能特性

- **自动追踪** - 包装任意 LLM API 调用，自动记录服务商、模型、token 用量、费用、延迟及成功/失败状态
- **SQLite 存储** - 所有数据本地存储于 `~/.agent-monitor/usage.db`
- **数据看板** - 支持按日、周、月、年查看费用明细
- **预算告警** - 设置月度预算，接近上限时自动提醒
- **服务商对比** - 查看哪个服务商最适合你的使用模式
- **CSV/JSON 导出** - 导出用量数据用于进一步分析
- **Python 集成** - 支持装饰器和上下文管理器两种用法

## 安装

```bash
pip install agent-monitor
```

或从源码安装：

```bash
git clone https://github.com/Jaxz714/agent-monitor.git
cd agent-monitor
pip install .
```

## 快速开始

### Python API

**装饰器：**

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

**上下文管理器：**

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

### CLI 命令

```bash
# 显示费用看板（默认按月查看）
agentmon dashboard
agentmon dashboard --period week

# 预算管理
agentmon budget set 100      # 设置 $100 月度预算
agentmon budget status       # 查看剩余预算

# 导出数据
agentmon export --format csv
agentmon export --format json --output ~/my-usage.json

# 对比服务商
agentmon providers

# 查看最近调用记录
agentmon history
agentmon history --limit 50

# 查看配置
agentmon config
```

## 定价数据

内置常用模型的定价信息：

| 服务商 | 模型 | 输入 ($/1M tokens) | 输出 ($/1M tokens) |
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

## 配置

配置文件存储于 `~/.agent-monitor/config.yaml`。也可以编辑 `config/default.yaml` 修改默认值。

## 许可证

MIT License - Copyright (c) 2026 Jaxz714
