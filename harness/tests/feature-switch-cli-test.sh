#!/usr/bin/env bash
# feature-switch-cli-test — CLI: list/status/on/off, ack cho guardrail, từ chối công tắc chưa gắn hook.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
ROOT="$(pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/llmwiki/.claude/hooks" "$TMP/harness"
cp harness/features.yaml "$TMP/harness/"
cp llmwiki/.claude/hooks/hooklib.py "$TMP/llmwiki/.claude/hooks/"
CLI="$ROOT/harness/scripts/feature-switch.py"
pass=0; fail=0
ok(){ printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad(){ printf '  \033[1;31m✗\033[0m %s — %s\n' "$1" "$2"; fail=$((fail+1)); }

python3 "$CLI" --root "$TMP" list | grep -q 'egress-guard.*guardrail' && ok "list hiện lớp và nơi gác" || bad "list" "thiếu dòng egress-guard"

python3 "$CLI" --root "$TMP" off egress-guard > /dev/null 2> "$TMP/e1"; rc=$?
[ $rc -eq 2 ] && grep -q 'acknowledge-guardrail' "$TMP/e1" && ok "off guardrail thiếu ack → rc 2" || bad "ack" "rc=$rc $(cat "$TMP/e1")"

python3 "$CLI" --root "$TMP" off egress-guard --acknowledge-guardrail 2> "$TMP/e2"; rc=$?
# PyYAML ghi 'off' có nháy (YAML 1.1 đọc không nháy thành bool) → đọc lại bằng safe_load, không grep chuỗi thô.
python3 - "$TMP/llmwiki/features.local.yaml" <<'PY' && file_ok=1 || file_ok=0
import sys, yaml
sys.exit(0 if yaml.safe_load(open(sys.argv[1], encoding="utf-8")).get("egress-guard") == "off" else 1)
PY
[ $rc -eq 0 ] && [ $file_ok -eq 1 ] && grep -q 'TẮT egress-guard' "$TMP/e2" && ok "off có ack → ghi file cục bộ + stderr" || bad "off có ack" "rc=$rc"

python3 "$CLI" --root "$TMP" status egress-guard | grep -q 'TẮT.*file cục bộ' && ok "status báo TẮT và nguồn" || bad "status" "$(python3 "$CLI" --root "$TMP" status egress-guard)"

python3 "$CLI" --root "$TMP" off inject-scan > /dev/null 2> "$TMP/e3"; rc=$?
[ $rc -eq 2 ] && grep -q 'chưa gắn' "$TMP/e3" && ok "công tắc chưa gắn hook → từ chối" || bad "chưa gắn" "rc=$rc"

python3 "$CLI" --root "$TMP" on wikigraph > /dev/null && python3 "$CLI" --root "$TMP" status wikigraph | grep -q 'BẬT' && ok "on wikigraph → BẬT" || bad "on" "sai"

[ -f "$TMP/harness/metrics/feature-switch.jsonl" ] && grep -q '"action": "off"' "$TMP/harness/metrics/feature-switch.jsonl" && ok "nhật ký ghi lần tắt" || bad "nhật ký" "thiếu"

echo "feature-switch-cli-test: $pass pass, $fail fail"
[ $fail -eq 0 ] && echo "PASS" || exit 1
