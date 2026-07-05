"""Tests for Merger – label rule parsing and merge decision logic."""

import os
import sys
import json

# Ensure src/ is on sys.path so imports work
_src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from merger import Merger


# We need a minimal mock GitHubClient for Merger tests


class MockGitHubClient:
    """Minimal mock that returns controlled data for should_merge tests."""

    def __init__(self, **overrides):
        self._pr = overrides.get("pr", {"number": 1, "draft": False, "mergeable": True, "title": "Test PR"})
        self._labels = overrides.get("labels", [])
        self._reviews = overrides.get("reviews", [{"state": "APPROVED", "user": {"login": "github-actions"}}])

    def get_pr(self, pr_number):
        return self._pr

    def get_labels(self, pr_number):
        return self._labels

    def list_reviews(self, pr_number):
        return self._reviews

    def merge_pr(self, pr_number, method="squash"):
        return True


class TestParseLabelRules:
    """Verify label rules JSON parsing."""

    def setup_method(self):
        # Merger needs a GitHubClient, but for _parse_label_rules we call directly
        pass

    def test_parses_valid_json(self):
        merger = Merger(MockGitHubClient())
        merger.label_rules = merger._parse_label_rules(
            '{"auto_merge_labels": ["auto-merge"], "block_merge_labels": ["wip"]}'
        )
        assert "auto_merge_labels" in merger.label_rules
        assert merger.label_rules["auto_merge_labels"] == ["auto-merge"]

    def test_invalid_json_returns_empty_dict(self):
        merger = Merger(MockGitHubClient())
        merger.label_rules = merger._parse_label_rules("not-json")
        assert merger.label_rules == {}

    def test_empty_string_returns_empty_dict(self):
        merger = Merger(MockGitHubClient())
        merger.label_rules = merger._parse_label_rules("")
        assert merger.label_rules == {}

    def test_complex_rules(self):
        merger = Merger(MockGitHubClient())
        merger.label_rules = merger._parse_label_rules(
            json.dumps({
                "auto_merge_labels": ["ready", "auto-merge"],
                "block_merge_labels": ["do-not-merge", "wip", "blocked"],
            })
        )
        assert len(merger.label_rules["auto_merge_labels"]) == 2
        assert len(merger.label_rules["block_merge_labels"]) == 3


class TestShouldMerge:
    """Verify auto-merge decision conditions."""

    def test_auto_merge_disabled(self):
        merger = Merger(MockGitHubClient())
        merger.auto_merge = False
        should, reason = merger.should_merge(1)
        assert should is False
        assert "disabled" in reason.lower()

    def test_draft_pr_skipped(self):
        merger = Merger(MockGitHubClient(pr={"number": 1, "draft": True, "mergeable": True}))
        merger.auto_merge = True
        should, reason = merger.should_merge(1)
        assert should is False
        assert "draft" in reason.lower()

    def test_merge_conflict_skipped(self):
        merger = Merger(MockGitHubClient(pr={"number": 1, "draft": False, "mergeable": False}))
        merger.auto_merge = True
        should, reason = merger.should_merge(1)
        assert should is False
        assert "conflict" in reason.lower()

    def test_approving_review_allows_merge(self):
        merger = Merger(MockGitHubClient(
            labels=[],
            reviews=[{"state": "APPROVED", "user": {"login": "github-actions"}}],
        ))
        merger.auto_merge = True
        should, reason = merger.should_merge(1)
        assert should is True

    def test_changes_requested_blocks_merge(self):
        merger = Merger(MockGitHubClient(
            labels=[],
            reviews=[{"state": "CHANGES_REQUESTED", "user": {"login": "some-user"}}],
        ))
        merger.auto_merge = True
        should, reason = merger.should_merge(1)
        assert should is False

    def test_block_merge_label_blocks_merge(self):
        merger = Merger(MockGitHubClient(
            labels=["wip", "feature"],
            reviews=[{"state": "APPROVED", "user": {"login": "github-actions"}}],
        ))
        merger.auto_merge = True
        merger.label_rules = {"block_merge_labels": ["wip"]}
        should, reason = merger.should_merge(1)
        assert should is False
        assert "blocked" in reason.lower()

    def test_auto_merge_label_required_but_missing(self):
        merger = Merger(MockGitHubClient(
            labels=["bug"],
            reviews=[{"state": "APPROVED", "user": {"login": "github-actions"}}],
        ))
        merger.auto_merge = True
        merger.label_rules = {"auto_merge_labels": ["auto-merge"]}
        should, reason = merger.should_merge(1)
        assert should is False

    def test_auto_merge_label_present_allows_merge(self):
        merger = Merger(MockGitHubClient(
            labels=["auto-merge", "feature"],
            reviews=[{"state": "APPROVED", "user": {"login": "github-actions"}}],
        ))
        merger.auto_merge = True
        merger.label_rules = {"auto_merge_labels": ["auto-merge"]}
        should, reason = merger.should_merge(1)
        assert should is True

    def test_no_reviews_blocks_merge(self):
        merger = Merger(MockGitHubClient(reviews=[]))
        merger.auto_merge = True
        should, reason = merger.should_merge(1)
        assert should is False
        assert "no reviews" in reason.lower()
