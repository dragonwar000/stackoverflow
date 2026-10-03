#!/usr/bin/env bash
# zeromem-memory-map-test — --source zeromem đọc DB ở chế độ chỉ đọc, ghi file riêng, không đụng memory-map.html.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
ROOT="$(pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export OVERSTACK_ZEROMEM_HOME="$TMP/stores"
pass=0; fail=0
ok(){ printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad(){ printf '  \033[1;31m✗\033[0m %s — %s\n' "$1" "$2"; fail=$((fail+1)); }

# Chạy trong project tạm: memory-map lấy ROOT = cwd khi cwd có llmwiki/, nên store key khớp với DB seed ở dưới.
PROJ="$TMP/proj"; mkdir -p "$PROJ/llmwiki/html"
STORE=$(python3 -c "import sys; sys.path.insert(0,'harness/scripts'); import importlib.util as u; s=u.spec_from_file_location('zb','harness/scripts/zeromem-bridge.py'); m=u.module_from_spec(s); s.loader.exec_module(m); print(m.store_home('$PROJ'))")
mkdir -p "$STORE" && python3 - "$STORE/zeromem.db" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
con.execute("CREATE TABLE turns (id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, session_turn INTEGER NOT NULL, speaker TEXT NOT NULL, text TEXT NOT NULL, ts INTEGER NOT NULL)")
rows = [("aaaaaaaa-x", 0, "user", "xuat csv", 100), ("aaaaaaaa-x", 1, "assistant", "da xong", 101), ("bbbbbbbb-y", 0, "user", "sua hook", 200)]
con.executemany("INSERT INTO turns (session_id, session_turn, speaker, text, ts) VALUES (?,?,?,?,?)", rows)
con.commit(); con.close()
PY

(cd "$PROJ" && python3 "$ROOT/fdk/tools/memory-map.py" --source zeromem) > "$TMP/out.log" 2>&1
rc=$?
[ $rc -eq 0 ] && grep -q 'memory-map-zeromem.html' "$TMP/out.log" && [ -f "$PROJ/llmwiki/html/memory-map-zeromem.html" ] \
  && ok "--source zeromem chạy và ghi đúng file đích" || bad "chạy --source zeromem" "rc=$rc $(cat "$TMP/out.log")"

[ ! -e "$PROJ/llmwiki/html/memory-map.html" ] && ok "không ghi đè memory-map.html" || bad "memory-map.html bị ghi" "file đích sai"

python3 - "$STORE/zeromem.db" <<'PY' && ok "DB không bị ghi (đọc ở chế độ ro)" || bad "DB bị ghi" "số turn đổi"
import sqlite3, sys
con = sqlite3.connect(sys.argv[1]); n = con.execute("SELECT COUNT(*) FROM turns").fetchone()[0]; con.close()
sys.exit(0 if n == 3 else 1)
PY

python3 - "$STORE/zeromem.db" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1]); con.execute("ALTER TABLE turns RENAME COLUMN text TO body"); con.commit(); con.close()
PY
(cd "$PROJ" && python3 "$ROOT/fdk/tools/memory-map.py" --source zeromem) > "$TMP/schema.log" 2>&1
schema_rc=$?
[ $schema_rc -ne 0 ] && grep -q 'schema zeromem lạ' "$TMP/schema.log" \
  && ok "schema lạ → báo lỗi rc≠0, không vẽ bừa" || bad "schema lạ" "rc=$schema_rc $(cat "$TMP/schema.log")"

echo "zeromem-memory-map-test: $pass pass, $fail fail"
[ $fail -eq 0 ] && echo "PASS" || exit 1
