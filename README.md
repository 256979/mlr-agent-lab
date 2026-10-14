# mlr-agent-lab

Experiments with an LLM agent in the loop for machine-learning work.

## Requirements

- [uv](https://docs.astral.sh/uv/) for Python environments and packages
- [GitHub CLI](https://cli.github.com/) for repository work

Both are installed per-user under `%USERPROFILE%\bin` on the lab machine — no
administrator rights required.

## Setup

```bash
uv venv
uv pip install -r requirements.txt   # once dependencies are pinned
```

## Repository rules

This repository is **public** so that GitHub Pages can be served for free.
Therefore:

- No API keys, tokens, or credentials — use environment variables and a
  `.env` file (git-ignored). If a key is ever committed, revoke it; deleting
  the file later is not enough, it stays in history.
- No `.claude/` config folder.
- No `.venv/`.
- No datasets or model weights — generate or fetch them locally.

`​.gitignore` enforces all four. Check `git status` before every commit.

## Pages

Static site source lives at the repository root (`index.html`). Published from
*Settings → Pages → Deploy from a branch → `main` / root*.
