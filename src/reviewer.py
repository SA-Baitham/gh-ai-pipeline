"""
AI Reviewer – analyzes PR diffs and posts review comments.
"""

from .github_client import GitHubClient
from .ai_client import AIClient


class Reviewer:
    """AI-powered code reviewer for pull requests."""

    def __init__(self, gh: GitHubClient, ai: AIClient):
        self.gh = gh
        self.ai = ai

    def needs_review(self, pr_number: int) -> bool:
        """Check if this PR already has an AI review."""
        reviews = self.gh.list_reviews(pr_number)
        for review in reviews:
            user = review.get("user", {})
            # If the bot user already reviewed, skip
            # The bot user is whoever runs the action — check login
            if "github-actions" in str(user.get("login", "")):
                return False
        return True

    def review(self, pr_number: int) -> str | None:
        """Run AI review on a PR and post the result."""
        pr = self.gh.get_pr(pr_number)
        if not pr:
            print(f"❌ PR #{pr_number} not found")
            return None

        print(f"🔍 Reviewing PR #{pr_number}: {pr.get('title', '')}")

        diff = self.gh.get_pr_diff(pr_number)
        if not diff or len(diff.strip()) < 10:
            print("  ⏭️  No substantial diff to review")
            return None

        files = self.gh.get_pr_files(pr_number)
        file_list = [f["filename"] for f in files]

        # Call AI
        print(f"  → Sending {len(file_list)} files to {self.ai.provider} ({self.ai.model})...")
        review_text = self.ai.review_diff(diff, file_list)

        if not review_text:
            print("  ⚠️  AI review returned empty result")
            return None

        # Truncate if too long for a GitHub review
        if len(review_text) > 60000:
            review_text = review_text[:60000] + "\n\n..._(review truncated)_"

        # Determine verdict
        verdict = self.ai.extract_verdict(review_text)
        bot_name = "🤖 AI Pipeline"

        if verdict == "APPROVE":
            full_review = f"## ✅ {bot_name}: Approved\n\n{review_text}"
            self.gh.create_review(pr_number, body=full_review, event="APPROVE")

        elif verdict == "REQUEST_CHANGES":
            full_review = f"## ❌ {bot_name}: Changes Requested\n\n{review_text}"
            self.gh.create_review(pr_number, body=full_review, event="REQUEST_CHANGES")

        else:
            full_review = f"## 💬 {bot_name}: Comment\n\n{review_text}"
            self.gh.create_review(pr_number, body=full_review, event="COMMENT")

        print(f"  → Verdict: {verdict}")
        return verdict
