# Contributing to gh-ai-pipeline

Thanks for wanting to help! This project is all about making PR workflows
suck less for solo devs and small teams.

## How to contribute

### 🐛 Report a bug
Open an issue with:
- Your workflow YAML (redact secrets)
- The GitHub Action run log
- What you expected vs what happened

### 💡 Suggest a feature
Open an issue describing:
- What you want to do
- Why the current pipeline can't do it
- A sketch of how it might work

### 🛠 Submit code

1. Fork the repo
2. Create a branch: `git checkout -b feat/your-thing`
3. Make your changes
4. Run the validation: `pip install -r requirements.txt && python -m src.main --help`
5. Push and open a PR

The AI pipeline will review your PR automatically. 😄

### Style notes
- Keep it simple. No over-engineering.
- Python 3.11+, standard lib + httpx + PyYAML only.
- Type hints everywhere.
- No async — GitHub Actions runners are single-threaded anyway.

## Code of Conduct

Don't be a jerk. That's it.
