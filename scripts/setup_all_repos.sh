#!/usr/bin/env bash
# =============================================================================
# setup_all_repos.sh – Install gh-ai-pipeline across all SA-Baitham repos
# =============================================================================
# This script clones each of your repos, adds the AI Pipeline workflow,
# and pushes the change. You'll need a GitHub token with repo scope.
#
# Usage:
#   export GITHUB_TOKEN=ghp_...
#   ./scripts/setup_all_repos.sh
#
# To skip certain repos, set SKIP_REPOS env var:
#   SKIP_REPOS="llama.cpp" ./scripts/setup_all_repos.sh
# =============================================================================

set -euo pipefail

# ── Repos to set up ──────────────────────────────────────────────────────────
REPOS=(
    "SA-Baitham/gpr_diffusion"
    "SA-Baitham/gpr_data_pipeline"
    "SA-Baitham/diff-gpr-claude"
    "SA-Baitham/gpr-utility-detector"
    "SA-Baitham/util-detnet"
    "SA-Baitham/rar_data_gpr"
    "SA-Baitham/SSMTLHT-PyT"
    "SA-Baitham/Infuse"
    "SA-Baitham/iee-ht"
)

SKIP="${SKIP_REPOS:-}"

# ── Config (customize these) ─────────────────────────────────────────────────
AI_PROVIDER="openai"
AI_MODEL="deepseek-v4-flash-free"
AI_ENDPOINT="https://opencode.ai/zen/v1"
AUTO_MERGE="false"

# ── Main ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "  gh-ai-pipeline - Bulk Setup"
echo "  Provider: $AI_PROVIDER / $AI_MODEL"
echo "  Endpoint: $AI_ENDPOINT"
echo "  Auto-merge: $AUTO_MERGE"
echo "  Repos: ${#REPOS[@]} total"
echo "=========================================="
echo ""

for REPO in "${REPOS[@]}"; do
    REPO_NAME="${REPO#*/}"

    # Check skip list
    if echo "$SKIP" | grep -qi "$REPO_NAME"; then
        echo "⏭️  Skipping $REPO (in SKIP_REPOS)"
        continue
    fi

    echo ""
    echo "──────────────────────────────────────────"
    echo "  Processing $REPO ..."
    echo "──────────────────────────────────────────"

    # Use the single-repo setup script
    bash "$SCRIPT_DIR/setup_repo.sh" "$REPO" "$AI_PROVIDER" "$AI_MODEL" "$AI_ENDPOINT" "$AUTO_MERGE" || {
        echo "⚠️  Failed on $REPO, continuing..."
    }
done

echo ""
echo "=========================================="
echo "  All done!"
echo "=========================================="
echo ""
echo "Don't forget to add AI_API_KEY secrets to each repo:"
echo "  1. Go to https://github.com/settings/apps or each repo's secrets page"
echo "  2. Add AI_API_KEY with your provider's API key"
echo ""
echo "Or set an org-level secret (SA-Baitham org) to apply to all repos at once."
