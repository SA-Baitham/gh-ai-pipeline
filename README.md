<div align="center">

# 🤖 gh-ai-pipeline

**Automated PR creation + AI code review + auto-merge — for free, on any repo.**

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/SA-Baitham/gh-ai-pipeline)](https://github.com/SA-Baitham/gh-ai-pipeline/releases)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Push a branch → AI writes your PR. Open a PR → AI reviews your code. Flip a toggle → approved PRs merge themselves.

</div>

---

## ✨ What it does

| Trigger | What happens |
|---------|-------------|
| You `git push` a branch | AI generates a title & description → PR is created automatically |
| PR opened / updated | AI reviews the diff → posts comments inline |
| PR approved | Auto-merges (if you opt in) |

No more pushing straight to main. No more untracked changes. No more manual PR overhead.

## 🚀 Quick Start (takes 5 minutes)

### 1. Fork & push this repo to your GitHub

```bash
# Clone, then push to your own GitHub
git clone https://github.com/SA-Baitham/gh-ai-pipeline.git
cd gh-ai-pipeline
git remote set-url origin https://github.com/YOUR_USER/gh-ai-pipeline.git
git push origin main
```

### 2. Add the workflow to your target repo

Copy [`template-workflow.yml`](./template-workflow.yml) into the repo you want to automate:

**`.github/workflows/ai-pipeline.yml`**
```yaml
name: AI Pipeline

on:
  push:
    branches-ignore: [main, master]
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  ai-pipeline:
    uses: YOUR_USER/gh-ai-pipeline/.github/workflows/ai-pipeline.yml@main
    with:
      ai_provider: openai
      ai_model: deepseek-v4-flash-free
      ai_endpoint: https://opencode.ai/zen/v1
      auto_merge: false
    secrets:
      AI_API_KEY: ${{ secrets.AI_API_KEY }}
```

> **Note:** Replace `YOUR_USER` with your GitHub username after you fork.

### 3. Get an API key

Choose a free AI provider and add its API key:

| Provider | How to get a key |
|----------|-----------------|
| **OpenCode Zen** (recommended, free) | Go to [opencode.ai](https://opencode.ai) → sign up → create API key |
| **OpenRouter** (alternative free tier) | [openrouter.ai/keys](https://openrouter.ai/keys) — free, no credit card |
| **OpenAI** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |

Add it to your repo: **Settings → Secrets and variables → Actions → `AI_API_KEY`**

### 4. Test it

```bash
git checkout -b test-ai-pipeline
echo "# Test" >> README.md
git add . && git commit -m "test: ai pipeline"
git push origin test-ai-pipeline
```

That's it. Go check — a PR with an AI-generated title is waiting for you.

---

> **💡 Note on defaults:** The `deepseek-v4-flash-free` + `https://opencode.ai/zen/v1` defaults
> in this project point to **OpenCode Zen** (free tier). Override `ai_model`, `ai_endpoint`,
> and `ai_provider` to change the AI backend. See the table below.

## 🧠 AI Providers

Any OpenAI-compatible API works. The default is **OpenCode Zen** (`deepseek-v4-flash-free` at `https://opencode.ai/zen/v1`)
which gives you access to DeepSeek V4 Flash for free.

| Provider | Endpoint | API Key |
|----------|----------|---------|
| **OpenCode Zen** (recommended, free) | `https://opencode.ai/zen/v1` | Your OpenCode API key |
| **OpenRouter** (free tier available) | `https://openrouter.ai/api/v1` | Your OpenRouter key |
| **OpenAI** | `https://api.openai.com/v1` | `sk-...` |
| **Anthropic** | *(built-in, not OpenAI-compat)* | `sk-ant-...` |
| **Local** (llama.cpp, vLLM, etc.) | `http://your-server:8080/v1` | Anything |

### Anthropic example

```yaml
with:
  ai_provider: anthropic
  ai_model: claude-3-sonnet-20240229
  review_style: thorough
```

### Local LLM example

```yaml
with:
  ai_provider: openai
  ai_model: your-model
  ai_endpoint: http://localhost:8080/v1
```

---

## ⚙️ Configuration

### Workflow inputs

| Input | Default | Description |
|-------|---------|-------------|
| `ai_provider` | `openai` | `openai`, `anthropic`, `local` |
| `ai_model` | `deepseek-v4-flash-free` | Model name |
| `ai_endpoint` | `https://opencode.ai/zen/v1` | API base URL |
| `auto_merge` | `false` | `true` / `false` |
| `auto_merge_method` | `squash` | `merge`, `squash`, `rebase` |
| `review_style` | `normal` | `light`, `normal`, `thorough` |
| `label_rules` | `{}` | JSON rules (see below) |

### Review styles

| Style | What it checks |
|-------|---------------|
| `light` | Critical bugs, security holes, logic errors |
| `normal` | Bugs, security, perf, code quality, best practices |
| `thorough` | Everything + edge cases, error handling, docs, tests |

### Label-based merge rules

```yaml
with:
  label_rules: >-
    {
      "block_merge_labels": ["do-not-merge", "wip"],
      "auto_merge_labels": ["auto-merge", "ready"]
    }
```

---

## 📁 Project structure

```
gh-ai-pipeline/
├── .github/
│   ├── workflows/ai-pipeline.yml    # Reusable GitHub workflow
│   └── ISSUE_TEMPLATE/              # Bug & feature templates
├── src/
│   ├── main.py                      # Entry point: routes push/PR events
│   ├── github_client.py             # GitHub REST API wrapper
│   ├── ai_client.py                 # OpenAI / Anthropic / local adapter
│   ├── pr_manager.py                # Creates & updates PRs with AI titles
│   ├── reviewer.py                  # AI code review logic
│   └── merger.py                    # Auto-merge with label rules
├── scripts/
│   ├── setup_repo.sh                # Install pipeline on one repo
│   └── setup_all_repos.sh           # Bulk install across repos
├── config/default_rules.yaml        # Documented defaults
├── template-workflow.yml            # Copy this into your repos
├── action.yml                       # Composite action metadata
├── requirements.txt                 # Python deps (minimal)
├── LICENSE                          # MIT
├── CONTRIBUTING.md
└── README.md
```

---

## 🧰 Requirements

- **Python 3.11+** (on the GitHub runner)
- **GitHub token** — built-in `GITHUB_TOKEN` is sufficient
- **AI API key** — [OpenCode](https://opencode.ai) (free), [OpenRouter](https://openrouter.ai/keys) (free), OpenAI, or Anthropic

---

## 🤝 Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

The project philosophy:
- **Simple** — no over-engineering. It's a Python script, not a framework.
- **Minimal deps** — standard lib + `httpx` + `PyYAML`. That's it.
- **No async** — GitHub Actions runners are single-threaded.
- **Type hints everywhere** — makes it easy to understand and modify.

---

## 📜 License

MIT — do whatever you want. See [LICENSE](LICENSE).

---

## 💬 Why this exists

> *"My GitHub is 95% commits. No code reviews, no issues, no pull requests."*
>
> If that sounds like you, this pipeline is for you. It turns a solo dev's messy
> commit history into a clean, reviewable, automated workflow — without adding
> any overhead to your day.
>
> Push a branch. Get a PR. Get a review. Merge. Move on.

---

Maintained by [@SA-Baitham](https://github.com/SA-Baitham).
