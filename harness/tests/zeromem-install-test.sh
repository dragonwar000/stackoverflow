#!/usr/bin/env bash
# zeromem-install-test — kiểm chế độ --verify-only của zeromem-install.sh bằng lock tạm.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
INSTALL="harness/scripts/zeromem-install.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
ok(){ printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad(){ printf '  \033[1;31m✗\033[0m %s — %s\n' "$1" "$2"; fail=$((fail+1)); }

mkdir -p "$TMP/snap/onnx"
printf 'model-bytes' > "$TMP/snap/onnx/model.onnx"
printf '{}' > "$TMP/snap/tokenizer.json"
python3 - "$TMP" <<'PY'
import hashlib, json, sys
t = sys.argv[1]
files = {}
for rel in ["onnx/model.onnx", "tokenizer.json"]:
    files[rel] = hashlib.sha256(open(f"{t}/snap/{rel}", "rb").read()).hexdigest()
json.dump({"model": {"files": files}}, open(f"{t}/lock.json", "w"))
PY

ZEROMEM_LOCK="$TMP/lock.json" bash "$INSTALL" --verify-only "$TMP/snap" > "$TMP/ok.log" 2>&1
[ $? -eq 0 ] && ok "sha khớp → rc 0" || bad "sha khớp → rc 0" "$(cat "$TMP/ok.log")"

printf 'x' >> "$TMP/snap/onnx/model.onnx"
ZEROMEM_LOCK="$TMP/lock.json" bash "$INSTALL" --verify-only "$TMP/snap" > "$TMP/lech.log" 2>&1
rc=$?
[ $rc -eq 1 ] && grep -q 'LỆCH onnx/model.onnx' "$TMP/lech.log" && ok "sha lệch → rc 1 và báo đúng file" || bad "sha lệch → rc 1" "rc=$rc $(cat "$TMP/lech.log")"

rm -f "$TMP/snap/tokenizer.json"
ZEROMEM_LOCK="$TMP/lock.json" bash "$INSTALL" --verify-only "$TMP/snap" > "$TMP/thieu.log" 2>&1
rc=$?
[ $rc -eq 1 ] && grep -q 'THIẾU tokenizer.json' "$TMP/thieu.log" && ok "thiếu file → rc 1 và báo đúng file" || bad "thiếu file → rc 1" "rc=$rc $(cat "$TMP/thieu.log")"

echo "zeromem-install-test: $pass pass, $fail fail"
[ $fail -eq 0 ] && echo "PASS" || exit 1
