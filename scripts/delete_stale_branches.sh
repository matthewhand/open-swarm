#!/usr/bin/env bash
# Delete stale remote branches on origin, per the 2026-06-10 triage of all 84
# unmerged branches plus the merge work that followed.
#
# REQUIRES: the local cleanup-wave commits pushed to origin/main first
# (otherwise GitHub will still show the "merged" branches as unmerged).
#
# Usage:
#   bash scripts/delete_stale_branches.sh --dry-run   # print what would happen
#   bash scripts/delete_stale_branches.sh             # actually delete
set -euo pipefail

DRY_RUN="${1:-}"

delete() {
  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo "[dry-run] git push origin --delete $1"
  else
    git push origin --delete "$1" || echo "  (skip: $1 already gone?)"
  fi
}

echo "== Tier 1: branches fully merged into main (mechanically verified) =="
# Recompute at run time so this stays correct after the push:
for b in $(git branch -r --merged origin/main | grep -v 'origin/main$\|origin/HEAD' | sed 's|^ *origin/||'); do
  delete "$b"
done

echo "== Tier 2: superseded per triage (fix already in main via other commits) =="
TIER2=(
  fix-message-validation-loop-13461393135452482360
  fix-message-validation-loop-16910505641363257756
  fix-message-sequence-validation-loop-5758531575210750583
  feat-validate-message-roles-10373432377625855168
  fix-poets-db-schema-12912138158328753318
  fix-poets-db-schema-8532731972265219774
  performance-async-swarm-log-fix-13345939046878504528
  performance-geese-async-io-v2-9298554655306349675
  optimize-github-parallel-10256249175462087564
  performance-async-file-io-whinge-surf-13168900650679793687
  performance-optimize-id-check-api-views-4868921917336824364
  verify-message-sequence-loop-fix-5336370506532432389
)

echo "== Tier 3: duplicate clusters — a better twin was merged or kept =="
TIER3=(
  security-fix-command-injection-codey-14944322991747537880
  security-fix-command-injection-codey-4622495280475509466
  fix-command-injection-3895585039769700448
  security-fix-echocraft-command-injection-7551603414105985424
  security-fix-rue-code-shell-execution-15432071725826217408
  security-fix-hardcoded-password-236351230174461440
  security-fix-hardcoded-password-5453351325604988603
  security-fix-sql-injection-blueprints-5833449816944804593
  refine-poet-db-schema-18199682901264052305
  optimize-github-sync-bulk-ops-18431593568333718367
  performance-mcp-sync-bulk-9635073156339025494
  cleanup-remove-deprecated-digitalbutlers-blueprint-14338822249398726615
  perf-opt-bulk-create-messages-3759653611412313645
  cleanup-poet-blueprint-comment-16067329048041896351
  fix-interactive-mode-syntax-error-18384623706999174466
  cleanup-blueprint-init-7976437804615998789
  cleanup-settings-imports-18408781243714172989
)

echo "== Tier 4: stale-diverged (pre-restructure base; superseded by archive branch) =="
TIER4=(
  chore/blueprint-dilbot
  chore/blueprint-geese
  chore/blueprint-poets
  chore/blueprint-ruecode
  refactor-wip   # reviewed 2026-06-10: nothing worth salvaging (notes in ROADMAP)
)

for b in "${TIER2[@]}" "${TIER3[@]}" "${TIER4[@]}"; do
  delete "$b"
done

echo
echo "Branches deliberately KEPT (still merge-worthy or undecided):"
echo "  feat/ansi-output-fallback, improve-ci-config-quality,"
echo "  optimize-codey-async-sleep-*, perf-codey-cache-*, perf-job-id-opt-*,"
echo "  perf-optimize-save-conversation-*, performance-redact-optimization-*,"
echo "  fix-jeeves-ux-todo-*, fix-geese-coordinator-dead-code-*,"
echo "  fix-dict-messages-filtering-*, fix-message-sequence-roles-*,"
echo "  poets-db-optimization-*, testing-improvement-merge-fields-*,"
echo "  fix-hardcoded-password-vulnerability-*, security-fix-sql-injection-blueprints-18407935481939566592,"
echo "  security-fix-command-injection-mcp-demo-*, fix-codey-shell-injection-*,"
echo "  fix-remove-unused-*, remove-unused-permission-import-*,"
echo "  resolve-blueprint-todo-*, test-tool-executor-json-error-*,"
echo "  cleanup-interactive-mode-comments-*, cleanup-digitalbutlers-blueprint-*,"
echo "  performance-optimize-blueprint-sync-*, fix-poets-schema-and-security-*,"
echo "  fix-security-command-injection-shlex-*, fix-silenced-exception... (merged ones drop out of this list after push)"
