# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-05

### Added
- Automated PR creation with AI-generated titles and descriptions on `git push`
- AI code review with three configurable review styles (`light`, `normal`, `thorough`)
- Auto-merge with label-based rules (`auto_merge_labels`, `block_merge_labels`)
- Support for multiple AI providers: OpenAI, Anthropic, OpenCode Zen, OpenRouter, and local LLMs
- OpenCode Zen as the default AI backend (`deepseek-v4-flash-free` model, free tier)
- Mermaid workflow diagram in README illustrating the end-to-end pipeline
- MIT license and issue templates

### Fixed
- Run AI review on push event to bypass GitHub's `GITHUB_TOKEN` recursion limit
- Downgrade `REQUEST_CHANGES` to `COMMENT` when PR is owned by the bot (GitHub policy)
- Replace relative imports with absolute imports for reliable execution
- Add retry logic (3 attempts with backoff) for AI API timeouts and rate limits
- HTML/Cloudflare challenge detection for graceful failure handling
- Commit-based PR title fallback when AI title generation fails
- YAML lint error (em-dash character in workflow comment)
- Default workflow permissions set to write for PR creation

### Changed
- Default AI backend from OpenRouter (`openrouter/free`) → OpenCode Zen (`deepseek-v4-flash-free`)
- Default AI endpoint from `https://openrouter.ai/api/v1` → `https://opencode.ai/zen/v1`
- Updated all documentation, templates, and setup scripts to reflect new defaults
