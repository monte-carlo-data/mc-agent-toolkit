#!/usr/bin/env bash
#
# bump-version.sh — Bump versions and update changelogs across all plugins.
#
# Run this on your feature branch before committing. It updates all 5 plugin
# config files and changelogs in one step. Commit the result as part of your PR.
#
# Usage:
#   ./scripts/bump-version.sh <patch|minor|major|X.Y.Z> [--dry-run]
#
# Examples:
#   ./scripts/bump-version.sh patch          # 1.0.0 → 1.0.1
#   ./scripts/bump-version.sh minor          # 1.0.0 → 1.1.0
#   ./scripts/bump-version.sh 2.0.0          # Set explicit version
#   ./scripts/bump-version.sh patch --dry-run  # Preview without changes
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
DRY_RUN=false
BUMP_TYPE=""

# ── Parse arguments ─────────────────────────────────────────────────────────
usage() {
  echo "Usage: $0 <patch|minor|major|X.Y.Z> [--dry-run]"
  exit 1
}

for arg in "$@"; do
  case "$arg" in
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
    # Replace the first "version" field regardless of its current value, so
    # plugins that drifted out of sync get normalized to $NEW_VERSION.
    sed -i '' -E '1,/"version"[[:space:]]*:/s|("version"[[:space:]]*:[[:space:]]*")[^"]*(")|\1'"$NEW_VERSION"'\2|' "$filepath"
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
    # Insert the new entry before the first existing version heading.
    # Uses ENVIRON instead of -v to safely pass multiline strings.
    CHANGELOG_ENTRY="$CHANGELOG_ENTRY" awk '
      /^## \[/ && !inserted {
        print ENVIRON["CHANGELOG_ENTRY"]
        print ""
        inserted = 1
      }
      { print }
    ' "$filepath" > "${filepath}.tmp" && mv "${filepath}.tmp" "$filepath"
    echo "Updated changelog in $file"
  fi
done

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
if [[ "$DRY_RUN" == false ]]; then
  echo "Version bumped to $NEW_VERSION."
  echo "Files updated — commit them as part of your PR."
fi
