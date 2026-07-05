"""
Auto-Merger – handles automatic merging of approved PRs.
"""

import json
import os

from github_client import GitHubClient


class Merger:
    """Manages auto-merge logic based on rules and review status."""

    def __init__(self, gh: GitHubClient):
        self.gh = gh
        self.auto_merge = os.environ.get("AUTO_MERGE", "false").lower() == "true"
        self.merge_method = os.environ.get("AUTO_MERGE_METHOD", "squash")
        self.label_rules = self._parse_label_rules(
            os.environ.get("LABEL_RULES", "{}")
        )

    def _parse_label_rules(self, raw: str) -> dict:
        """Parse label-based merge rules from JSON string."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def should_merge(self, pr_number: int) -> tuple[bool, str]:
        """
        Determine if a PR should be auto-merged.
        Returns (should_merge, reason).
        """
        if not self.auto_merge:
            return False, "Auto-merge is disabled"

        pr = self.gh.get_pr(pr_number)
        if not pr:
            return False, "PR not found"

        # Don't merge if PR is draft
        if pr.get("draft", False):
            return False, "PR is a draft"

        # Don't merge if PR has conflicts
        if pr.get("mergeable") is False:
            return False, "PR has merge conflicts"

        # Check labels against rules
        labels = self.gh.get_labels(pr_number)
        no_merge_labels = self.label_rules.get("block_merge_labels", [])
        for label in labels:
            if label in no_merge_labels:
                return False, f"Blocked by label: '{label}'"

        auto_merge_labels = self.label_rules.get("auto_merge_labels", [])
        if auto_merge_labels:
            has_auto_label = any(l in auto_merge_labels for l in labels)
            if not has_auto_label:
                return (
                    False,
                    f"None of the auto-merge labels present: {auto_merge_labels}",
                )

        # Check that the latest review was approving
        reviews = self.gh.list_reviews(pr_number)
        if not reviews:
            return False, "No reviews yet"

        # Get the state of the most recent review from our bot
        latest_review_state = None
        for review in reversed(reviews):
            state = review.get("state", "")
            if state in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED"):
                latest_review_state = state
                break

        if latest_review_state != "APPROVED":
            return False, f"Latest review state is '{latest_review_state}', not APPROVED"

        return True, "All merge conditions met"

    def try_merge(self, pr_number: int) -> bool:
        """Attempt to merge a PR if conditions are met."""
        can_merge, reason = self.should_merge(pr_number)

        if not can_merge:
            print(f"⏭️  PR #{pr_number}: {reason}")
            return False

        print(f"🚀 Auto-merging PR #{pr_number} ({self.merge_method})...")
        return self.gh.merge_pr(pr_number, method=self.merge_method)
