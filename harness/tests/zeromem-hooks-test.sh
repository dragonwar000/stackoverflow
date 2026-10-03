#!/usr/bin/env bash
# zeromem-hooks-test — SessionStart in dòng recall zeromem khi backend là zeromem; mem-rank không đổi.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
ROOT="$(pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export OVERSTACK_ZEROMEM_HOME="$TMP/stores" ZEROMEM_ZM="$ROOT/harness/tests/fixtures/fake-zm.py"
pass=0; fail=0
ok(){ printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad(){ printf '  \033[1;31m✗\033[0m %s — %s\n' "$1" "$2"; fail=$((fail+1)); }

for f in llmwiki/.claude/hooks/stop.py llmwiki/.claude/hooks/session_start.py llmwiki/.claude/hooks/session_end.py; do
  python3 -m py_compile "$f" && ok "cú pháp $(basename "$f")" || bad "cú pháp $(basename "$f")" "py_compile lỗi"
done

PROJ="$TMP/proj"; mkdir -p "$PROJ/harness" "$PROJ/llmwiki/wiki"
git -C "$PROJ" init -q && git -C "$PROJ" -c user.email=t@t -c user.name=t commit -q --allow-empty -m "feat: xuất csv"
cp harness/mem-rank.config.yaml "$PROJ/harness/" && cp -r harness/scripts "$PROJ/harness/" && mkdir -p "$PROJ/harness/tests" && cp -r harness/tests/fixtures "$PROJ/harness/tests/"

out=$(echo '{"session_id":"bbbbbbbb","cwd":"'"$PROJ"'"}' | CLAUDE_PROJECT_DIR="$PROJ" python3 llmwiki/.claude/hooks/session_start.py 2>/dev/null)
echo "$out" | grep -q 'Trí nhớ zeromem' && echo "$out" | grep -q 'aaaaaaaa' && ! echo "$out" | grep -q 'bbbbbbbb' \
  && ok "SessionStart in recall zeromem, loại phiên hiện tại" || bad "SessionStart recall" "$(echo "$out" | head -5)"

sed -i.bak 's/backend: zeromem/backend: mem-rank/' "$PROJ/harness/mem-rank.config.yaml"
out=$(echo '{"session_id":"bbbbbbbb","cwd":"'"$PROJ"'"}' | CLAUDE_PROJECT_DIR="$PROJ" python3 llmwiki/.claude/hooks/session_start.py 2>/dev/null)
echo "$out" | grep -q 'Trí nhớ zeromem' && bad "backend mem-rank" "vẫn in recall zeromem" || ok "backend mem-rank không in recall zeromem"

echo '{}' > "$TMP/t.jsonl"
echo '{"session_id":"cccccccc","transcript_path":"'"$TMP"'/t.jsonl","cwd":"'"$PROJ"'"}' | CLAUDE_PROJECT_DIR="$PROJ" python3 llmwiki/.claude/hooks/session_end.py >/dev/null 2>"$TMP/se.err"
[ $? -eq 0 ] && ! grep -q Traceback "$TMP/se.err" && ok "SessionEnd chạy ghi zeromem không lỗi" || bad "SessionEnd" "$(head -3 "$TMP/se.err")"

echo "zeromem-hooks-test: $pass pass, $fail fail"
[ $fail -eq 0 ] && echo "PASS" || exit 1
