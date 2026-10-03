#!/usr/bin/env bash
# feature-switch-hooks-test — công tắc wikigraph quan sát ĐẦU-CUỐI qua hook thật:
# lời nhắc ở SessionStart (mặc định tắt, env =1 hoặc file cục bộ bật, env =0 tắt) và dòng stderr khi tắt tường minh.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
ROOT="$(pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
ok(){ printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad(){ printf '  \033[1;31m✗\033[0m %s — %s\n' "$1" "$2"; fail=$((fail+1)); }

# Dự án khách: có wiki, CHƯA có wiki-graph.html, không chứa engine. Engine và registry lấy từ "global" = repo này.
PROJ="$TMP/proj"; mkdir -p "$PROJ/.llmwiki/wiki/concepts"
printf '# x\n' > "$PROJ/.llmwiki/wiki/concepts/x.md"
printf '{"schema": 1}\n' > "$PROJ/.llmwiki/.harness-stamp"
git -C "$PROJ" init -q

ss(){ # ss <tên file out> [ENV=...]: chạy session_start.py thật, stdout và stderr tách riêng
  local out="$1"; shift
  printf '{"session_id":"s1","cwd":"%s"}' "$PROJ" | env -u OVERSTACK_WIKIGRAPH -u OVERSTACK_FEATURE_WIKIGRAPH \
    OVERSTACK_HARNESS_HOME="$ROOT" CLAUDE_PROJECT_DIR="$PROJ" ZEROMEM_ZM=/does/not/exist "$@" \
    python3 "$ROOT/llmwiki/.claude/hooks/session_start.py" > "$TMP/$out.out" 2> "$TMP/$out.err"
}
nhac(){ grep -q '\[wiki-graph\]' "$TMP/$1.out"; }

ss a
nhac a && bad "mặc định" "có stamp, không env mà vẫn nhắc — mặc định bị đổi" || ok "có stamp, không env → KHÔNG nhắc (mặc định giữ nguyên)"

ss b OVERSTACK_WIKIGRAPH=1
nhac b && ok "OVERSTACK_WIKIGRAPH=1 → nhắc vẽ graph" || bad "env cũ =1" "không nhắc: $(head -3 "$TMP/b.out")"

ss c OVERSTACK_FEATURE_WIKIGRAPH=on
nhac c && ok "OVERSTACK_FEATURE_WIKIGRAPH=on → nhắc" || bad "env mới =on" "không nhắc"

printf "wikigraph: 'on'\n" > "$PROJ/.llmwiki/features.local.yaml"
ss d
nhac d && ok "features.local.yaml bật → nhắc" || bad "file cục bộ on" "không nhắc"

ss e OVERSTACK_WIKIGRAPH=0
nhac e && bad "env=0 thua file cục bộ" "vẫn nhắc" || ok "OVERSTACK_WIKIGRAPH=0 thắng file cục bộ → không nhắc"
grep -q '\[harness\] wikigraph TẮT — nguồn: env OVERSTACK_WIKIGRAPH' "$TMP/e.err" \
  && ok "tắt tường minh in một dòng stderr nêu nguồn" || bad "stderr khi tắt" "$(cat "$TMP/e.err" | head -3)"

printf "wikigraph: 'off'\n" > "$PROJ/.llmwiki/features.local.yaml"
ss f
nhac f && bad "file cục bộ off" "vẫn nhắc" || ok "features.local.yaml tắt → không nhắc"
rm -f "$PROJ/.llmwiki/features.local.yaml"

ss g
[ ! -s "$TMP/g.err" ] || ! grep -q 'wikigraph TẮT' "$TMP/g.err" \
  && ok "tắt do mặc định → không in stderr (không nhiễu mỗi phiên)" || bad "stderr mặc định" "$(head -2 "$TMP/g.err")"

echo "feature-switch-hooks-test: $pass pass, $fail fail"
[ $fail -eq 0 ] && echo "PASS" || exit 1
