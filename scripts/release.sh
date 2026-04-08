#!/usr/bin/env bash
#
# release.sh — Bump versions, update changelogs, commit, and tag a release.
#
# Usage:
#   ./scripts/release.sh <patch|minor|major|X.Y.Z> [--push] [--dry-run]
#
# Examples:
#   ./scripts/release.sh patch              # 1.0.0 → 1.0.1, commit + tag locally
#   ./scripts/release.sh minor --push       # 1.0.0 → 1.1.0, commit + tag + push
#   ./scripts/release.sh 2.0.0 --dry-run    # Preview what would happen
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Clean up temp files on exit (interrupted runs, errors, etc.)
cleanup() {
  rm -f "${TMPDIR:-/tmp}"/release-changelog.*
  for f in "${CHANGELOG_FILES[@]:-}"; do
    rm -f "$REPO_ROOT/${f}.tmp" 2>/dev/null
  done
}
trap cleanup EXIT

# ── Plugin config files (version source of truth) ──────────────────────────
VERSION_FILES=(
  "plugins/claude-code/.claude-plugin/plugin.json"
  "plugins/cursor/.cursor-plugin/plugin.json"
  "plugins/copilot/plugin.json"
  "plugins/codex/.codex-plugin/plugin.json"
  "plugins/opencode/package.json"
)

CHANGELOG_FILES=(
  "plugins/claude-code/CHANGELOG.md"
  "plugins/cursor/CHANGELOG.md"
  "plugins/copilot/CHANGELOG.md"
  "plugins/codex/CHANGELOG.md"
  "plugins/opencode/CHANGELOG.md"
)

# ── Defaults ────────────────────────────────────────────────────────────────
PUSH=false
DRY_RUN=false
BUMP_TYPE=""

# ── Parse arguments ─────────────────────────────────────────────────────────
usage() {
  echo "Usage: $0 <patch|minor|major|X.Y.Z> [--push] [--dry-run]"
  exit 1
}

for arg in "$@"; do
  case "$arg" in
    --push)    PUSH=true ;;
    --dry-run) DRY_RUN=true ;;
    patch|minor|major) BUMP_TYPE="$arg" ;;
    [0-9]*.[0-9]*.[0-9]*)  BUMP_TYPE="explicit"; EXPLICIT_VERSION="$arg" ;;
    -h|--help) usage ;;
    *) echo "Unknown argument: $arg"; usage ;;
  esac
done

[[ -z "$BUMP_TYPE" ]] && usage

# ── Read current version ────────────────────────────────────────────────────
SOURCE_FILE="$REPO_ROOT/${VERSION_FILES[0]}"
CURRENT_VERSION=$(grep -o '"version": *"[^"]*"' "$SOURCE_FILE" | head -1 | sed 's/.*"\([0-9][^"]*\)".*/\1/')

if [[ -z "$CURRENT_VERSION" ]]; then
  echo "Error: Could not read current version from $SOURCE_FILE"
  exit 1
fi

# ── Compute next version ────────────────────────────────────────────────────
if [[ "$BUMP_TYPE" == "explicit" ]]; then
  NEW_VERSION="$EXPLICIT_VERSION"
else
  IFS='.' read -r V_MAJOR V_MINOR V_PATCH <<< "$CURRENT_VERSION"
  case "$BUMP_TYPE" in
    patch) V_PATCH=$((V_PATCH + 1)) ;;
    minor) V_MINOR=$((V_MINOR + 1)); V_PATCH=0 ;;
    major) V_MAJOR=$((V_MAJOR + 1)); V_MINOR=0; V_PATCH=0 ;;
  esac
  NEW_VERSION="$V_MAJOR.$V_MINOR.$V_PATCH"
fi

echo "Current version: $CURRENT_VERSION"
echo "Next version:    $NEW_VERSION"
echo ""

# ── Preflight checks ───────────────────────────────────────────────────────
if [[ "$DRY_RUN" == false ]]; then
  if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
    echo "Error: Working tree is not clean. Commit or stash changes first."
    exit 1
  fi

  CURRENT_BRANCH=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)
  if [[ "$CURRENT_BRANCH" != "main" ]]; then
    echo "Warning: You are on branch '$CURRENT_BRANCH', not 'main'."
    read -rp "Continue anyway? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
  fi

  if git -C "$REPO_ROOT" rev-parse "v$NEW_VERSION" >/dev/null 2>&1; then
    echo "Error: Tag v$NEW_VERSION already exists."
    exit 1
  fi
fi

# ── Changelog entry ─────────────────────────────────────────────────────────
RELEASE_DATE=$(date +%Y-%m-%d)
TMPFILE=$(mktemp "${TMPDIR:-/tmp}/release-changelog.XXXXXX")

# Pre-fill with commits since last tag
LAST_TAG=$(git -C "$REPO_ROOT" describe --tags --abbrev=0 2>/dev/null || echo "")
{
  echo "## [$NEW_VERSION] - $RELEASE_DATE"
  echo ""
  echo "### Changed"
  echo ""
  if [[ -n "$LAST_TAG" ]]; then
    git -C "$REPO_ROOT" log --oneline "$LAST_TAG..HEAD" | sed 's/^/- /'
  else
    git -C "$REPO_ROOT" log --oneline -20 | sed 's/^/- /'
  fi
  echo ""
  echo "<!-- Edit the changelog entry above. Lines starting with <!-- are removed. -->"
} > "$TMPFILE"

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] Would open editor for changelog entry. Template:"
  echo "---"
  cat "$TMPFILE"
  echo "---"
else
  # Open editor for the user to refine
  "${EDITOR:-vi}" "$TMPFILE"

  # Strip HTML comments
  CHANGELOG_ENTRY=$(sed '/^<!--/d' "$TMPFILE")

  if [[ -z "$(echo "$CHANGELOG_ENTRY" | tr -d '[:space:]')" ]]; then
    echo "Error: Changelog entry is empty. Aborting."
    rm -f "$TMPFILE"
    exit 1
  fi
fi

rm -f "$TMPFILE"

# ── Update version files ───────────────────────────────────────────────────
echo ""
for file in "${VERSION_FILES[@]}"; do
  filepath="$REPO_ROOT/$file"
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would update version in $file"
  else
    sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" "$filepath"
    echo "Updated version in $file"
  fi
done

# ── Update changelogs ──────────────────────────────────────────────────────
echo ""
for file in "${CHANGELOG_FILES[@]}"; do
  filepath="$REPO_ROOT/$file"
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would prepend changelog entry to $file"
  else
    # Insert the new entry after the first blank line following the header
    # (after the "Format follows..." preamble lines)
    awk -v entry="$CHANGELOG_ENTRY" '
      /^## \[/ && !inserted {
        print entry
        print ""
        inserted = 1
      }
      { print }
    ' "$filepath" > "${filepath}.tmp" && mv "${filepath}.tmp" "$filepath"
    echo "Updated changelog in $file"
  fi
done

# ── Git commit and tag ─────────────────────────────────────────────────────
echo ""
if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] Would commit: release: v$NEW_VERSION"
  echo "[dry-run] Would tag: v$NEW_VERSION"
else
  cd "$REPO_ROOT"
  git add "${VERSION_FILES[@]}" "${CHANGELOG_FILES[@]}"
  git commit -m "release: v$NEW_VERSION"
  git tag "v$NEW_VERSION"
  echo "Committed: release: v$NEW_VERSION"
  echo "Tagged: v$NEW_VERSION"
fi

# ── Push ────────────────────────────────────────────────────────────────────
echo ""
if [[ "$PUSH" == true ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would push to origin with tags"
  else
    git -C "$REPO_ROOT" push origin HEAD --tags
    echo "Pushed to origin with tags"
  fi
else
  if [[ "$DRY_RUN" == false ]]; then
    echo "Done! To publish the release, run:"
    echo "  git push origin main --tags"
    echo ""
    echo "Or next time, use --push to push automatically:"
    echo "  ./scripts/release.sh $BUMP_TYPE --push"
  fi
fi
