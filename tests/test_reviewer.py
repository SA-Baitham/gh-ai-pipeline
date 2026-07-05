"""Tests for Reviewer – needs_review logic and bot PR ownership handling."""

import os
import sys

# Ensure src/ is on sys.path so imports work
_src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from reviewer import Reviewer


class MockGitHubClient:
    """Minimal mock for Reviewer tests."""

    def __init__(self, **overrides):
        self._reviews = overrides.get("reviews", [])

    def list_reviews(self, pr_number):
        return self._reviews

    def get_pr(self, pr_number):
        return {"number": pr_number, "title": "Test PR", "user": {"login": "github-actions"}}

    def get_pr_diff(self, pr_number):
        return "diff --git a/test.py b/test.py\n+print('hello')"

    def get_pr_files(self, pr_number):
        return [{"filename": "test.py"}]

    def create_review(self, pr_number, body, event="COMMENT"):
        return {"id": 1, "state": event}


class MockAIClient:
    """Minimal mock for Reviewer tests."""

    def __init__(self, verdict="COMMENT", **_):
        self._verdict = verdict
        self.provider = "test"
        self.model = "test-model"

    def review_diff(self, diff, file_list):
        return f"## Summary\n\nTest review.\n\n## Verdict\n\n**{self._verdict}**"

    def extract_verdict(self, text):
        if "APPROVE" in text.upper():
            return "APPROVE"
        elif "REQUEST_CHANGES" in text.upper():
            return "REQUEST_CHANGES"
        return "COMMENT"


class TestReviewerNeedsReview:
    """Verify needs_review checks for existing bot reviews."""

    def test_no_reviews_needs_review(self):
        gh = MockGitHubClient(reviews=[])
        ai = MockAIClient()
        reviewer = Reviewer(gh, ai)
        assert reviewer.needs_review(1) is True

    def test_bot_already_reviewed_skips(self):
        gh = MockGitHubClient(reviews=[
            {"state": "COMMENTED", "user": {"login": "github-actions"}},
        ])
        ai = MockAIClient()
        reviewer = Reviewer(gh, ai)
        assert reviewer.needs_review(1) is False

    def test_human_review_does_not_skip(self):
        gh = MockGitHubClient(reviews=[
            {"state": "COMMENTED", "user": {"login": "some-human"}},
        ])
        ai = MockAIClient()
        reviewer = Reviewer(gh, ai)
        assert reviewer.needs_review(1) is True

    def test_mixed_reviews_with_bot(self):
        gh = MockGitHubClient(reviews=[
            {"state": "COMMENTED", "user": {"login": "human1"}},
            {"state": "APPROVED", "user": {"login": "github-actions"}},
            {"state": "COMMENTED", "user": {"login": "human2"}},
        ])
        ai = MockAIClient()
        reviewer = Reviewer(gh, ai)
        assert reviewer.needs_review(1) is False


class TestReviewerDowngradeOwnPR:
    """Verify REQUEST_CHANGES is downgraded to COMMENT when bot owns PR."""

    def test_request_changes_downgraded_for_bot_pr(self, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTOR", "github-actions")
        gh = MockGitHubClient()
        ai = MockAIClient(verdict="REQUEST_CHANGES")
        reviewer = Reviewer(gh, ai)
        result = reviewer.review(1)
        # Should return "COMMENT" due to downgrade
        assert result == "COMMENT"

    def test_approve_stays_approve(self, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTOR", "github-actions")
        gh = MockGitHubClient()
        ai = MockAIClient(verdict="APPROVE")
        reviewer = Reviewer(gh, ai)
        result = reviewer.review(1)
        assert result == "APPROVE"

    def test_no_downgrade_for_human_pr(self, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTOR", "someone-else")

        class HumanPRMock(MockGitHubClient):
            def get_pr(self, pr_number):
                return {"number": pr_number, "title": "Test PR", "user": {"login": "human-user"}}

        gh = HumanPRMock()
        ai = MockAIClient(verdict="REQUEST_CHANGES")
        reviewer = Reviewer(gh, ai)
        result = reviewer.review(1)
        assert result == "REQUEST_CHANGES"

    def test_no_substantial_diff_returns_none(self):
        gh = MockGitHubClient()
        # Override diff to return empty
        gh.get_pr_diff = lambda n: ""
        ai = MockAIClient()
        reviewer = Reviewer(gh, ai)
        result = reviewer.review(1)
        assert result is None
