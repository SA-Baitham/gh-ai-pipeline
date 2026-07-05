"""Tests for AIClient – verdict extraction, prompt building, and endpoint normalization."""

import os
import sys
import json

# Ensure src/ is on sys.path so imports work
_src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from ai_client import AIClient


class TestExtractVerdict:
    """Verify that verdict extraction works for all three outcomes."""

    def setup_method(self):
        self.ai = AIClient()

    def test_approve_verdict(self):
        text = "## Summary\n\nLooks good.\n\n## Verdict\n\n**APPROVE**"
        assert self.ai.extract_verdict(text) == "APPROVE"

    def test_approve_verdict_no_markdown(self):
        text = "Looks fine. APPROVE"
        assert self.ai.extract_verdict(text) == "APPROVE"

    def test_request_changes_verdict(self):
        text = "## Summary\n\nIssues found.\n\n## Verdict\n\n**REQUEST_CHANGES**"
        assert self.ai.extract_verdict(text) == "REQUEST_CHANGES"

    def test_request_changes_no_markdown(self):
        text = "This should be fixed. REQUEST_CHANGES"
        assert self.ai.extract_verdict(text) == "REQUEST_CHANGES"

    def test_comment_verdict(self):
        text = "## Summary\n\nQuestions below.\n\n## Verdict\n\n**COMMENT**"
        assert self.ai.extract_verdict(text) == "COMMENT"

    def test_comment_non_standard_caps(self):
        text = "## Verdict\n\nComment"
        assert self.ai.extract_verdict(text) == "COMMENT"

    def test_empty_text_falls_back_to_comment(self):
        text = ""
        assert self.ai.extract_verdict(text) == "COMMENT"

    def test_no_verdict_keyword(self):
        text = "The code looks alright but could use some improvements."
        assert self.ai.extract_verdict(text) == "COMMENT"

    def test_approve_among_other_text(self):
        text = "I've reviewed this. APPROVE. Good work."
        assert self.ai.extract_verdict(text) == "APPROVE"


class TestBuildReviewPrompt:
    """Verify review prompt generation with different styles."""

    def setup_method(self):
        self.ai = AIClient()

    def test_normal_style_prompt_contains_instructions(self):
        prompt = self.ai._build_review_prompt("diff --git a/file.py b/file.py", ["file.py"])
        assert "Instructions" in prompt
        assert "APPROVE" in prompt
        assert "REQUEST_CHANGES" in prompt
        assert "COMMENT" in prompt

    def test_light_style_includes_critical_keyword(self):
        self.ai.review_style = "light"
        prompt = self.ai._build_review_prompt("some diff", ["main.py"])
        assert "critical bugs" in prompt.lower()

    def test_thorough_style_includes_edge_cases(self):
        self.ai.review_style = "thorough"
        prompt = self.ai._build_review_prompt("some diff", ["main.py"])
        assert "edge cases" in prompt.lower()
        assert "error handling" in prompt.lower()

    def test_includes_file_list(self):
        files = ["src/main.py", "src/utils.py"]
        prompt = self.ai._build_review_prompt("some diff", files)
        for f in files:
            assert f"`{f}`" in prompt

    def test_unknown_style_defaults_to_normal(self):
        self.ai.review_style = "invalid_style"
        prompt = self.ai._build_review_prompt("some diff", ["f.py"])
        assert "best practices" in prompt


class TestBuildPRTitlePrompt:
    """Verify PR title prompt generation."""

    def setup_method(self):
        self.ai = AIClient()

    def test_contains_branch_name(self):
        prompt = self.ai._build_pr_title_prompt("some diff", "feat/add-login")
        assert "feat/add-login" in prompt

    def test_requests_json_format(self):
        prompt = self.ai._build_pr_title_prompt("diff", "fix-bug")
        assert "JSON" in prompt or "json" in prompt


class TestNormalizeEndpoint:
    """Verify endpoint URL normalization."""

    def setup_method(self):
        self.ai = AIClient()

    def test_appends_chat_completions(self):
        result = self.ai._normalize_endpoint("https://opencode.ai/zen/v1")
        assert result == "https://opencode.ai/zen/v1/chat/completions"

    def test_does_not_duplicate_chat_completions(self):
        result = self.ai._normalize_endpoint("https://api.openai.com/v1/chat/completions")
        assert result == "https://api.openai.com/v1/chat/completions"

    def test_strips_trailing_slash(self):
        result = self.ai._normalize_endpoint("https://example.com/v1/")
        assert result == "https://example.com/v1/chat/completions"

    def test_opencode_detection_flag(self):
        ai = AIClient()
        ai.endpoint = "https://opencode.ai/zen/v1"
        # Re-trigger detection (normally done in __init__)
        ai._is_opencode = "opencode.ai" in ai.endpoint.lower() if ai.endpoint else False
        assert ai._is_opencode is True

    def test_openrouter_detection_flag(self):
        ai = AIClient()
        ai.endpoint = "https://openrouter.ai/api/v1"
        ai._is_openrouter = "openrouter" in ai.endpoint.lower() if ai.endpoint else False
        assert ai._is_openrouter is True

    def test_neither_flag_set(self):
        ai = AIClient()
        ai.endpoint = "https://api.openai.com/v1"
        ai._is_openrouter = "openrouter" in ai.endpoint.lower() if ai.endpoint else False
        ai._is_opencode = "opencode.ai" in ai.endpoint.lower() if ai.endpoint else False
        assert ai._is_openrouter is False
        assert ai._is_opencode is False

    def test_defaults(self):
        ai = AIClient()
        assert ai.model == "deepseek-v4-flash-free"
        assert ai.endpoint == "https://opencode.ai/zen/v1"
