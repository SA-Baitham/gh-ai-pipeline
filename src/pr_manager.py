"""
PR Manager – creates and updates pull requests.
Triggers on pushes to non-default branches.
"""

import os
import re

from github_client import GitHubClient
from ai_client import AIClient


class PRManager:
    """Handles PR creation and updates."""

    def __init__(
        self, gh: GitHubClient, ai: AIClient
    ):
        self.gh = gh
        self.ai = ai
        self.default_branch = gh.get_default_branch()

    def should_skip_branch(self, branch: str) -> bool:
        """Skip branches that shouldn't get automatic PRs."""
        skip_patterns = [
            r"^main$", r"^master$",
            r"^dependabot/",
            r"^renovate/",
            r"^wip/", r"^draft/",
            r"^release/.*\d+$",
            r"^bot/",
        ]
        for pat in skip_patterns:
            if re.match(pat, branch):
                return True
        return False

    def handle_push(
        self, branch: str
    ) -> dict | None:
        """
        Called on push to a non-default branch.
        Creates a PR if one doesn't exist, updates it otherwise.
        """
        if self.should_skip_branch(branch):
            print(f"⏭️  Skipping branch '{branch}' (excluded by pattern)")
            return None

        if branch == self.default_branch:
            print(f"⏭️  On default branch '{branch}', nothing to do")
            return None

        # Check for existing PR
        existing_prs = self.gh.list_prs(head=f"{self.gh.repo_full.split('/')[0]}:{branch}")

        # Also try without owner prefix
        if not existing_prs:
            existing_prs = self.gh.list_prs(state="open")

        existing = None
        for pr in existing_prs:
            if pr.get("head", {}).get("ref") == branch:
                existing = pr
                break

        if existing:
            print(f"📋 PR #{existing['number']} already exists for '{branch}'")
            # Update title/body if they seem auto-generated (optional enhancement)
            return existing

        # Generate PR title and body
        print(f"🤖 Generating PR for branch '{branch}'...")
        comparison = self.gh.compare_branches(self.default_branch, branch)
        diff = ""
        if comparison:
            diff = comparison.get("files", [])
            diff_text = "\n".join(
                f"--- a/{f.get('filename', '')}\n+++ b/{f.get('filename', '')}"
                for f in diff[:20]
            )
        else:
            diff_text = branch

        title, body = self.ai.generate_pr_title(diff_text, branch)

        # Add context to body
        enhanced_body = (
            f"{body}\n\n"
            f"---\n"
            f"_🤖 Auto-created by [gh-ai-pipeline](https://github.com/SA-Baitham/gh-ai-pipeline)_\n"
        )

        pr = self.gh.create_pr(
            title=title,
            body=enhanced_body,
            head=branch,
            base=self.default_branch,
            draft=False,
        )
        return pr

    def get_pr_context(
        self, pr_number: int
    ) -> dict:
        """Gather context about a PR for review."""
        pr = self.gh.get_pr(pr_number)
        if not pr:
            return {}

        diff = self.gh.get_pr_diff(pr_number)
        files = self.gh.get_pr_files(pr_number)
        file_list = [f["filename"] for f in files]
        labels = self.gh.get_labels(pr_number)

        return {
            "pr": pr,
            "diff": diff,
            "files": file_list,
            "labels": labels,
            "title": pr.get("title", ""),
            "branch": pr.get("head", {}).get("ref", ""),
        }
