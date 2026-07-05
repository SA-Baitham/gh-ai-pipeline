"""
gh-ai-pipeline: Automated PR creation, AI review, and auto-merge.

Entry point for the GitHub Composite Action.
Determines the triggering event (push / pull_request) and dispatches
to the appropriate module.
"""

import os
import json
import sys

# Ensure src/ is on sys.path so absolute imports work
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from github_client import GitHubClient
from ai_client import AIClient
from pr_manager import PRManager
from reviewer import Reviewer
from merger import Merger


def get_event_info() -> dict:
    """Parse the GitHub event payload from the environment."""
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")

    payload = {}
    if event_path and os.path.exists(event_path):
        with open(event_path) as f:
            payload = json.load(f)

    return {"event": event_name, "payload": payload}


def handle_push(gh: GitHubClient, ai: AIClient, payload: dict):
    """Handle a push event – create/update PR and run AI review."""
    ref = payload.get("ref", "")
    branch = ref.replace("refs/heads/", "")

    if not branch:
        print("⚠️  Could not determine branch from push event")
        return

    print(f"\n{'='*60}")
    print(f"📦 Push detected on branch: {branch}")
    print(f"{'='*60}")

    manager = PRManager(gh, ai)
    pr = manager.handle_push(branch)

    if pr:
        print(f"   → PR #{pr['number']} is ready: {pr['html_url']}")
        # Run AI review immediately (avoids GITHUB_TOKEN recursion limit,
        # where a PR created by the pipeline won't trigger pull_request events)
        reviewer = Reviewer(gh, ai)
        verdict = reviewer.review(pr["number"])

        # Auto-merge if conditions met
        if verdict == "APPROVE":
            merger = Merger(gh)
            merger.try_merge(pr["number"])


def handle_pull_request(gh: GitHubClient, ai: AIClient, payload: dict):
    """Handle a PR event – run AI review and possibly auto-merge."""
    pr = payload.get("pull_request", {})
    action = payload.get("action", "")
    pr_number = pr.get("number")

    if not pr_number:
        print("⚠️  No PR number in event payload")
        return

    print(f"\n{'='*60}")
    print(f"🔀 PR #{pr_number} event: {action}")
    print(f"{'='*60}")

    # Only review on opened/synchronize
    if action not in ("opened", "synchronize", "reopened"):
        print(f"⏭️  Skipping review for action '{action}'")
        return

    # Check if PR is from a branch we want to review
    branch = pr.get("head", {}).get("ref", "")
    manager = PRManager(gh, ai)
    if manager.should_skip_branch(branch):
        print(f"⏭️  Skipping review for excluded branch '{branch}'")
        return

    # Run AI review
    reviewer = Reviewer(gh, ai)
    verdict = reviewer.review(pr_number)

    # Auto-merge if conditions met
    if verdict == "APPROVE":
        merger = Merger(gh)
        merger.try_merge(pr_number)


def main():
    """Main entry point – routes events to handlers."""
    event_info = get_event_info()
    event = event_info["event"]
    payload = event_info["payload"]

    gh = GitHubClient()
    ai = AIClient()

    print(f"🚀 gh-ai-pipeline v1.0.0")
    print(f"   Repo: {gh.repo_full}")
    print(f"   Event: {event}")
    print(f"   AI: {ai.provider} / {ai.model}")
    print(f"   Auto-merge: {os.environ.get('AUTO_MERGE', 'false')}")

    if event == "push":
        handle_push(gh, ai, payload)
    elif event == "pull_request":
        handle_pull_request(gh, ai, payload)
    else:
        print(f"⏭️  Unhandled event type: {event}")

    print(f"\n✅ Pipeline finished.")


if __name__ == "__main__":
    main()
