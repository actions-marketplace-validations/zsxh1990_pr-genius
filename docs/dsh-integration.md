---
type: Documentation
title: DSH Integration Guide
description: How to use pr-genius as an MCP skill inside DeepSeek Harness (DSH)
version: 2.1.5
created: 2026-08-15
updated: 2026-10-03
author: zsxh1990
conforms_to: OKF v0.1 (Sudhakaran88/okf-conformance) + agent_guidelines extension
---

# DSH Integration Guide

[![MCP](https://img.shields.io/badge/MCP-Server-green?style=flat-square)](https://github.com/modelcontextprotocol)

> Use [pr-genius](https://github.com/zsxh1990/pr-genius) as an MCP skill inside [DeepSeek Harness (DSH)](https://github.com/deepseek-ai/dsh) for AI-powered PR submission review, coach guidance, and anti-pattern detection.

## What is DSH?

DeepSeek Harness (DSH, ⭐108k+) is an open-source AI coding agent built on the Cordis framework. It supports plugins, MCP servers, and web UI extensions.

## Why pr-genius + DSH?

| DSH Native | pr-genius adds |
|-----------|----------------|
| Code generation, refactoring | Pre-submit PR review & anti-pattern detection |
| Task planning, testing | Coach mode for iterative PR improvement |
| File search, linting | Harvest mode to extract reusable lessons |
| — | Profile-driven context (project-specific rules) |
| — | 251 anti-pattern rules, 692 success patterns |

## Setup

### Method 1: MCP Skill Mode (Recommended)

The MCP entry point is `prgenius-core mcp serve` (stdio). In DSH settings or
`~/.dsh/settings.json`, add:

```json
{
  "mcpServers": {
    "pr-genius": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/zsxh1990/pr-genius@v2.1.4#subdirectory=prgenius", "prgenius-core", "mcp", "serve"],
      "env": {
        "GITHUB_TOKEN": "<your-token>"
      }
    }
  }
}
```

> The Python package lives in the `prgenius/` subdirectory (there is no
> repo-root `pyproject.toml`), hence `#subdirectory=prgenius`. The wheel ships
> code only — the knowledge base lives in the repo checkout, so pass
> `--repo-root /path/to/pr-genius` when the auto-detected path is wrong.

### Method 2: Local Development

```bash
git clone https://github.com/zsxh1990/pr-genius.git
cd pr-genius
# [mcp] extra pulls in the MCP SDK; either generation works
# (1.x and 2.x are both supported since 2.2.0)
pip install -e "./prgenius[mcp]"
```

Then configure DSH to use the local install:

```json
{
  "mcpServers": {
    "pr-genius": {
      "command": "prgenius-core",
      "args": ["mcp", "serve"],
      "env": {
        "GITHUB_TOKEN": "<your-token>"
      }
    }
  }
}
```

(`python -m prgenius mcp serve` works the same way.)

### Method 3: Docker (stdio MCP server)

The root `Dockerfile` is a **stdio** MCP server
(`ENTRYPOINT ["python", "-m", "prgenius", "mcp", "serve"]`) — it does not
listen on a port, so there is nothing to `-p` map:

```bash
docker build -t pr-genius .
docker run --rm -i pr-genius
```

```json
{
  "mcpServers": {
    "pr-genius": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "pr-genius"],
      "env": {
        "GITHUB_TOKEN": "<your-token>"
      }
    }
  }
}
```

> Note: the image published to `ghcr.io/zsxh1990/pr-genius` is built from
> `Dockerfile.github_action` (GitHub Action entrypoint), **not** this stdio
> MCP server. Do not `docker run -p 8000:8000` it — it exposes no HTTP port.

## Usage Scenarios in DSH

### 1. Pre-submit Review (in DSH conversation)

> "Review my staged changes before I push"

pr-genius will scan your diff, flag anti-patterns, suggest improvements, and rate PR readiness.

### 2. Coach Mode

> "Coach me on improving this PR"

Iterative guidance: fix issues → re-review → learn patterns specific to your project.

### 3. Harvest Mode

> "Extract lessons from this codebase"

Analyze git history to generate reusable lessons for future PRs in this project.

### 4. Standalone CLI

```bash
# Analyze a PR (merge probability + risk tier)
python3 -m prgenius analyze "feat: add feature" --repo owner/repo

# Coach mode (pass/fail gate)
python3 -m prgenius coach "feat: add feature" --repo owner/repo

# Triage (policy check against repo profile)
python3 -m prgenius triage "docs: typo" --repo owner/repo --diff-stat "docs/faq.md | 3 ++-"

# Harvest lessons from a rejected PR
python3 -m prgenius harvest owner/repo 123
```

## Example Workflow in DSH

```
You: "I've been working on adding OAuth support to the auth module.
      Help me review and polish the PR before submission."

DSH + pr-genius:
1. pr-genius reviews your diff → flags 3 anti-patterns
2. You fix them with DSH's code editing
3. pr-genius coach mode → confirms fixes + 2 more suggestions
4. Final check passes → ready to submit
```

## Architecture

```
┌─────────────┐     MCP stdio      ┌─────────────┐
│     DSH     │ ◄──────────────────►│  pr-genius   │
│  (DeepSeek) │                     │  (Python)    │
└─────────────┘                     └──────┬──────┘
                                           │
                              ┌────────────┼────────────┐
                              │            │            │
                         ┌────▼───┐  ┌─────▼────┐  ┌───▼────┐
                         │ Review │  │  Coach   │  │Harvest │
                         └────────┘  └──────────┘  └────────┘
```

## Links

- [pr-genius GitHub](https://github.com/zsxh1990/pr-genius)
- [DSH GitHub](https://github.com/deepseek-ai/dsh)
- [DSH Plugins Topic](https://github.com/topics/dsh-plugin)
- [awesome-dsh-plugin](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin)
