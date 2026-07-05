# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in **gh-ai-pipeline**, please report it privately instead of opening a public issue.

**Contact:** [Open a private advisory](https://github.com/SA-Baitham/gh-ai-pipeline/security/advisories/new) on GitHub.

Please include:
- A description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact

We aim to acknowledge receipt within 48 hours and provide a fix timeline within 7 days.

## Supported Versions

Only the latest release is actively maintained. We recommend always using the latest version.

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ |
| < 1.0   | ❌ |

## Best Practices for Users

- **Never commit API keys** to the repository. Use GitHub Secrets (`AI_API_KEY`) instead.
- **Review auto-merge behavior** before enabling `auto_merge: true` in your workflow.
- **Pin to a specific release** tag (e.g., `@v1.0.0`) rather than `@main` for production use.
