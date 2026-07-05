"""
AI client abstraction layer.
Supports OpenAI, Anthropic Claude, and local LLMs (OpenAI-compatible).
"""

import os
import json
import httpx
from typing import Any


class AIClient:
    """Unified interface for multiple AI backends."""

    def __init__(self):
        self.provider = os.environ.get("AI_PROVIDER", "openai").lower()
        self.api_key = os.environ.get("AI_API_KEY", "")
        self.model = os.environ.get("AI_MODEL", "openrouter/free")
        self.endpoint = os.environ.get("AI_ENDPOINT", "")
        self.review_style = os.environ.get("REVIEW_STYLE", "normal")
        self._is_openrouter = "openrouter" in self.endpoint.lower() if self.endpoint else False

    def _build_review_prompt(self, diff: str, file_list: list[str]) -> str:
        """Build a structured prompt for code review."""
        style_guides = {
            "light": "Focus only on critical bugs, security issues, and logic errors.",
            "normal": (
                "Check for bugs, security issues, performance problems, "
                "code quality, and adherence to best practices."
            ),
            "thorough": (
                "Perform a comprehensive review covering: correctness, security, "
                "performance, maintainability, style, edge cases, error handling, "
                "documentation, and test coverage."
            ),
        }
        style = style_guides.get(self.review_style, style_guides["normal"])

        files_str = "\n".join(f"- `{f}`" for f in file_list[:30])

        return f"""You are an expert code reviewer integrated into a GitHub Automation pipeline.

## Instructions
{style}

## Files Changed in this PR
{files_str if file_list else "(no files listed)"}

## Diff
```diff
{diff[:50000]}
```

## Review Guidelines
- Be constructive and specific. Reference exact lines where applicable.
- Categorize each issue as: **critical**, **warning**, or **suggestion**.
- If the code looks good, say so! Acknowledge well-written parts too.
- Keep your overall comment concise but thorough.

## Output Format
Start with a brief summary of the PR's purpose and overall assessment (1-2 sentences).
Then list issues if any, grouped by category.
End with a clear verdict: **APPROVE**, **REQUEST_CHANGES**, or **COMMENT**.
"""

    def _build_pr_title_prompt(self, diff: str, branch: str) -> str:
        """Generate a PR title from the diff and branch name."""
        branch_clean = branch.replace("-", " ").replace("_", " ").title()
        return f"""Generate a concise, descriptive PR title (max 72 chars) and a short body describing the changes.

Branch: {branch}
Diff preview:
```diff
{diff[:8000]}
```

Respond in this JSON format ONLY (no markdown):
{{"title": "feat: short title here", "body": "Brief description of what this PR does and why."}}
"""

    # ── OpenAI ───────────────────────────────────────────

    def _call_openai(
        self, messages: list[dict], temperature: float = 0.3
    ) -> str | None:
        url = self.endpoint or "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "gh-ai-pipeline/1.0",
        }
        # OpenRouter headers for usage tracking
        if self._is_openrouter:
            headers["HTTP-Referer"] = os.environ.get(
                "HTTP_REFERER", "https://github.com/SA-Baitham/gh-ai-pipeline"
            )
            headers["X-Title"] = os.environ.get(
                "X_TITLE", "gh-ai-pipeline"
            )

        last_error = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=180) as client:
                    resp = client.post(url, json=payload, headers=headers)

                if resp.is_success:
                    try:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
                        content_type = resp.headers.get("content-type", "")
                        body_preview = resp.text[:300]
                        print(f"⚠️  AI response parse error (attempt {attempt + 1}): {e}")
                        print(f"   Status: {resp.status_code}, Content-Type: {content_type}")
                        print(f"   Body: {body_preview}")
                        # If HTML response (e.g. Cloudflare challenge), don't retry
                        if "text/html" in content_type:
                            print("   💡 Received HTML instead of JSON — likely a Cloudflare challenge.")
                            print("      The CI runner IP may be blocked by the AI endpoint.")
                            print("      Try using a different AI provider/model or a paid API tier.")
                            return None
                        last_error = e
                        # Retry on empty/non-JSON responses
                        if attempt < 2:
                            import time
                            time.sleep(2 ** attempt)
                            continue
                        return None
                else:
                    print(f"⚠️  OpenAI API error: {resp.status_code} {resp.text[:300]}")
                    if resp.status_code == 429 and attempt < 2:
                        import time
                        wait = 2 ** attempt
                        print(f"   Rate limited — retrying in {wait}s...")
                        time.sleep(wait)
                        continue
                    return None
            except httpx.TimeoutException as e:
                print(f"⚠️  AI request timeout (attempt {attempt + 1})")
                last_error = e
                if attempt < 2:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                return None
            except httpx.RequestError as e:
                print(f"⚠️  AI request error: {e}")
                return None

        return None

    # ── Anthropic ────────────────────────────────────────

    def _call_anthropic(
        self, messages: list[dict], temperature: float = 0.3
    ) -> str | None:
        url = self.endpoint or "https://api.anthropic.com/v1/messages"
        # Convert OpenAI-style messages to Anthropic format
        system_msg = ""
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg += m["content"] + "\n"
            else:
                anthropic_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "system": system_msg.strip(),
            "temperature": temperature,
            "max_tokens": 4096,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=180) as client:
            resp = client.post(url, json=payload, headers=headers)
        if resp.is_success:
            try:
                data = resp.json()
                return data.get("content", [{}])[0].get("text", "")
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
                print(f"⚠️  Anthropic response parse error: {e}")
                print(f"   Status: {resp.status_code}, Body: {resp.text[:500]}")
                return None
        else:
            print(f"⚠️  Anthropic API error: {resp.status_code} {resp.text[:300]}")
            return None

    # ── Public API ───────────────────────────────────────

    def review_diff(
        self, diff: str, file_list: list[str]
    ) -> str | None:
        """Send a diff to the AI for review and get feedback."""
        prompt = self._build_review_prompt(diff, file_list)
        messages = [
            {"role": "system", "content": "You are a senior software engineer doing code review."},
            {"role": "user", "content": prompt},
        ]

        if self.provider == "anthropic":
            return self._call_anthropic(messages)
        else:
            return self._call_openai(messages)

    def generate_pr_title(
        self, diff: str, branch: str
    ) -> tuple[str, str]:
        """Generate a PR title and body from the changes."""
        prompt = self._build_pr_title_prompt(diff, branch)
        messages = [
            {"role": "system", "content": "You generate concise, conventional PR titles and descriptions."},
            {"role": "user", "content": prompt},
        ]

        if self.provider == "anthropic":
            result = self._call_anthropic(messages, temperature=0.2)
        else:
            result = self._call_openai(messages, temperature=0.2)

        if result:
            # Try to parse JSON from the result
            try:
                # Handle potential markdown wrapping
                clean = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                data = json.loads(clean)
                return data.get("title", f"Updates on {branch}"), data.get("body", "")
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback
        branch_clean = branch.replace("-", " ").replace("_", " ").title()
        return f"Updates: {branch_clean}", "Automated PR generated by AI Pipeline."

    def extract_verdict(self, review_text: str) -> str:
        """Extract APPROVE / REQUEST_CHANGES / COMMENT from review."""
        upper = review_text.upper()
        if "**APPROVE**" in upper or "APPROVE" in upper:
            return "APPROVE"
        elif "**REQUEST_CHANGES**" in upper or "REQUEST_CHANGES" in upper:
            return "REQUEST_CHANGES"
        else:
            return "COMMENT"
