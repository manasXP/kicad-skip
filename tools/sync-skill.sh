#!/usr/bin/env bash
# Mirror the live Claude Code skill (~/.claude/skills/kicad-skip) into this
# repo's .claude/skills/kicad-skip and stage the result for commit.
#
# Usage: tools/sync-skill.sh
#   SKILL_SRC=/path/to/skill tools/sync-skill.sh   # override source location
#
# Fails if the synced files contain machine-specific paths, so a local
# environment never leaks into the public repo — genericize the live skill
# and re-run.
set -euo pipefail

SRC="${SKILL_SRC:-$HOME/.claude/skills/kicad-skip}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DST="$REPO_DIR/.claude/skills/kicad-skip"

[ -d "$SRC" ] || { echo "error: source skill not found: $SRC" >&2; exit 1; }

LEAK_PATTERN='/Users/|/home/[a-z]|~/\.claude|\$HOME/\.claude|secrets\.env'
if grep -rEn --exclude='*.bak' "$LEAK_PATTERN" "$SRC"; then
  echo "" >&2
  echo "error: machine-specific paths found in live skill (listed above)." >&2
  echo "Genericize them in $SRC, then re-run. Repo copy left untouched." >&2
  exit 1
fi

mkdir -p "$DST"
rsync -a --delete --exclude='*.bak' "$SRC/" "$DST/"

cd "$REPO_DIR"
if [ -n "$(git status --porcelain -- .claude)" ]; then
  git add .claude
  git status --short -- .claude
  echo "Skill copy updated and staged — review, then:"
  echo "  git commit -m 'Sync Claude Code skill' && git push"
else
  echo "Skill copy already up to date."
fi
