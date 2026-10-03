#!/usr/bin/env bash
# zeromem-bridge-test — bridge với fake zm: recall loại phiên hiện tại, lỗi zm thì fail-open.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
BRIDGE="$(pwd)/harness/scripts/zeromem-bridge.py"
FAKE="$(pwd)/harness/tests/fixtures/fake-zm.py"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export OVERSTACK_ZEROMEM_HOME="$TMP/stores" ZEROMEM_ZM="$FAKE"
pass=0; fail=0
ok(){ printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad(){ printf '  \033[1;31m✗\033[0m %s — %s\n' "$1" "$2"; fail=$((fail+1)); }

out=$(python3 "$BRIDGE" recall --root "$TMP" --query "kho sach" --exclude-session bbbbbbbb 2>"$TMP/err")
rc=$?
[ $rc -eq 0 ] && echo "$out" | grep -q 'aaaaaaaa' && ! echo "$out" | grep -q 'bbbbbbbb' \
  && ok "recall loại đúng phiên hiện tại" || bad "recall loại phiên" "rc=$rc out=$out"

out=$(ZEROMEM_ZM=/does/not/exist python3 "$BRIDGE" recall --root "$TMP" --query x 2>"$TMP/err2")
rc=$?
[ $rc -eq 0 ] && [ -z "$out" ] && grep -q 'zeromem-bridge' "$TMP/err2" \
  && ok "zm thiếu → rc 0, stdout rỗng, cảnh báo stderr" || bad "fail-open" "rc=$rc out=$out"

out=$(python3 "$BRIDGE" stats --root "$TMP" 2>/dev/null)
echo "$out" | grep -q '"embedder_is_fallback": true' && ok "stats trả trường embedder_is_fallback" || bad "stats" "$out"

python3 "$BRIDGE" forget-session --root "$TMP" --session aaaaaaaa >/dev/null 2>&1
[ $? -eq 0 ] && ok "forget-session chạy không lỗi" || bad "forget-session" "rc khác 0"

python3 "$BRIDGE" ingest --root "$TMP" --session aaaaaaaa --transcript "" >/dev/null 2>&1
[ $? -eq 0 ] && ok "ingest không có transcript → rc 0 không làm gì" || bad "ingest rỗng" "rc khác 0"

echo "zeromem-bridge-test: $pass pass, $fail fail"
[ $fail -eq 0 ] && echo "PASS" || exit 1
