"""
GitHub API client wrapper.
Handles all GitHub REST API interactions for the pipeline.
"""

import os
import json
import httpx
from typing import Any


class GitHubClient:
    """Thin wrapper around GitHub REST API."""

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.api_url = os.environ.get(
            "GITHUB_API_URL", "https://api.github.com"
        )
        self.repo_full = os.environ.get("GITHUB_REPOSITORY", "")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "gh-ai-pipeline",
        }

    # ── Helpers ──────────────────────────────────────────

    def _request(
        self, method: str, path: str, **kwargs
    ) -> httpx.Response:
        url = f"{self.api_url}{path}" if path.startswith("/") else path
        with httpx.Client(headers=self.headers, timeout=60) as client:
            resp = client.request(method, url, **kwargs)
        if resp.status_code >= 400:
            print(f"⚠️  API error {resp.status_code}: {resp.text[:500]}")
        return resp

    def _repo_path(self, endpoint: str) -> str:
        return f"/repos/{self.repo_full}{endpoint}"

    # ── Pull Requests ────────────────────────────────────

    def list_prs(
        self, state: str = "open", head: str | None = None
    ) -> list[dict]:
        """List PRs, optionally filtered by head branch."""
        params = {"state": state, "per_page": 100}
        if head:
            params["head"] = head
        resp = self._request(
            "GET", self._repo_path("/pulls"), params=params
        )
        return resp.json() if resp.is_success else []

    def get_pr(self, pr_number: int) -> dict | None:
        resp = self._request(
            "GET", self._repo_path(f"/pulls/{pr_number}")
        )
        return resp.json() if resp.is_success else None

    def create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = False,
    ) -> dict | None:
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "draft": draft,
        }
        resp = self._request(
            "POST", self._repo_path("/pulls"), json=payload
        )
        if resp.is_success:
            data = resp.json()
            print(f"✅ Created PR #{data['number']}: {data['html_url']}")
            return data
        else:
            print(f"❌ Failed to create PR: {resp.text[:300]}")
            return None

    def update_pr(self, pr_number: int, **kwargs) -> dict | None:
        resp = self._request(
            "PATCH", self._repo_path(f"/pulls/{pr_number}"), json=kwargs
        )
        return resp.json() if resp.is_success else None

    # ── PR Diff / Files ──────────────────────────────────

    def get_pr_diff(self, pr_number: int) -> str:
        """Fetch the unified diff for a PR."""
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        url = f"{self.api_url}/repos/{self.repo_full}/pulls/{pr_number}"
        with httpx.Client(headers=headers, timeout=60) as client:
            resp = client.get(url)
        return resp.text if resp.is_success else ""

    def get_pr_files(self, pr_number: int) -> list[dict]:
        resp = self._request(
            "GET", self._repo_path(f"/pulls/{pr_number}/files"),
            params={"per_page": 100},
        )
        return resp.json() if resp.is_success else []

    # ── Reviews ──────────────────────────────────────────

    def list_reviews(self, pr_number: int) -> list[dict]:
        resp = self._request(
            "GET", self._repo_path(f"/pulls/{pr_number}/reviews")
        )
        return resp.json() if resp.is_success else []

    def create_review(
        self,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        comments: list[dict] | None = None,
    ) -> dict | None:
        """Create a PR review. Event: APPROVE, REQUEST_CHANGES, COMMENT."""
        payload: dict[str, Any] = {"body": body, "event": event}
        if comments:
            payload["comments"] = comments
        resp = self._request(
            "POST",
            self._repo_path(f"/pulls/{pr_number}/reviews"),
            json=payload,
        )
        if resp.is_success:
            print(f"  → Review {event} posted on PR #{pr_number}")
        return resp.json() if resp.is_success else None

    # ── Merge ────────────────────────────────────────────

    def merge_pr(
        self, pr_number: int, method: str = "squash"
    ) -> bool:
        """Merge a PR. method: merge, squash, rebase."""
        payload = {
            "merge_method": method,
            "sha": self.get_pr(pr_number).get("head", {}).get("sha", ""),
        }
        resp = self._request(
            "PUT",
            self._repo_path(f"/pulls/{pr_number}/merge"),
            json=payload,
        )
        if resp.is_success:
            print(f"✅ Merged PR #{pr_number}")
            return True
        else:
            print(f"❌ Merge failed for PR #{pr_number}: {resp.text[:300]}")
            return False

    # ── Labels ───────────────────────────────────────────

    def add_labels(self, pr_number: int, labels: list[str]) -> None:
        resp = self._request(
            "POST",
            self._repo_path(f"/issues/{pr_number}/labels"),
            json={"labels": labels},
        )
        if resp.is_success:
            print(f"  → Labels added to PR #{pr_number}: {labels}")

    def get_labels(self, pr_number: int) -> list[str]:
        resp = self._request(
            "GET", self._repo_path(f"/issues/{pr_number}/labels")
        )
        if resp.is_success:
            return [l["name"] for l in resp.json()]
        return []

    # ── Branches ─────────────────────────────────────────

    def get_default_branch(self) -> str:
        resp = self._request("GET", self._repo_path(""))
        if resp.is_success:
            return resp.json().get("default_branch", "main")
        return "main"

    def list_branches(self) -> list[dict]:
        resp = self._request(
            "GET", self._repo_path("/branches"),
            params={"per_page": 100},
        )
        return resp.json() if resp.is_success else []

    def compare_branches(self, base: str, head: str) -> dict | None:
        """Compare two branches, returns status and ahead_by/behind_by."""
        resp = self._request(
            "GET",
            self._repo_path(f"/compare/{base}...{head}"),
        )
        return resp.json() if resp.is_success else None

    def get_commits(self, branch: str, per_page: int = 10) -> list[dict]:
        """Get recent commits on a branch."""
        resp = self._request(
            "GET",
            self._repo_path(f"/commits"),
            params={"sha": branch, "per_page": per_page},
        )
        return resp.json() if resp.is_success else []
