#!/usr/bin/env bash
# zeromem-eval-test — hit@k cross-session. Mặc định dùng fake zm (chỉ kiểm harness, KHÔNG phải chất lượng);
# ZEROMEM_E2E=1 seed hai phiên golden vào store TẠM rồi đo bằng zm thật qua zeromem-bridge.py.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
ROOT="$(pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
chmod 700 "$TMP"
export OVERSTACK_ZEROMEM_HOME="$TMP/stores"
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
BRIDGE="$ROOT/harness/scripts/zeromem-bridge.py"
GOLDEN="$ROOT/harness/evals/zeromem-cross-session.json"
pass=0; fail=0
ok(){ printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad(){ printf '  \033[1;31m✗\033[0m %s — %s\n' "$1" "$2"; fail=$((fail+1)); }

if [ "${ZEROMEM_E2E:-0}" = "1" ]; then
  MODE=real
  unset ZEROMEM_ZM
  command -v zm >/dev/null 2>&1 || { echo "ZEROMEM_E2E=1 nhưng không có zm — không đo được"; exit 2; }
  # Seed chỉ vào store tạm (OVERSTACK_ZEROMEM_HOME trỏ TMP). Ingest qua đúng db của bridge, không ghi cứng đường dẫn.
  python3 - "$ROOT" "$(command -v zm)" "$TMP" <<'PY' || { echo "seed zeromem thất bại"; exit 2; }
import importlib.util, json, subprocess, sys
root, zm, tmp = sys.argv[1], sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location("zb", f"{root}/harness/scripts/zeromem-bridge.py")
zb = importlib.util.module_from_spec(spec); spec.loader.exec_module(zb)
home = zb.ensure_store(zb.store_home(root))
g = json.load(open(f"{root}/harness/evals/zeromem-cross-session.json", encoding="utf-8"))
lines, ts = [], 1000
for sid, texts in g["sessions"].items():
    for t in texts:
        ts += 1
        lines.append(json.dumps({"session_id": sid, "speaker": "user", "text": t, "ts": ts}, ensure_ascii=False))
seed = f"{tmp}/seed.jsonl"
open(seed, "w", encoding="utf-8").write("\n".join(lines) + "\n")
p = subprocess.run([zm, "--db", str(home / "zeromem.db"), "ingest", seed], capture_output=True, text=True, timeout=300)
print(p.stdout.strip()); print(p.stderr.strip()[-300:], file=sys.stderr)
sys.exit(p.returncode)
PY
else
  MODE=fake
  export ZEROMEM_ZM="$ROOT/harness/tests/fixtures/fake-zm.py"
fi

python3 - "$ROOT" "$MODE" "$BRIDGE" "$GOLDEN" <<'PY' > "$TMP/hits.txt"
import json, re, subprocess, sys
root, mode, bridge, golden = sys.argv[1:5]
g = json.load(open(golden, encoding="utf-8"))
hit = 0
for case in g["cases"]:
    out = subprocess.run([sys.executable, bridge, "recall", "--root", root, "--query", case["query"],
                          "--exclude-session", g["query_session"], "--top-k", str(case["k"])],
                         capture_output=True, text=True).stdout.splitlines()
    if mode == "real":   # đo thật: phải có evidence của đúng phiên mong đợi trong top-k
        ok = any(ln.startswith(f"- [{case['expect_session']}] ") for ln in out)
    else:                # fake: chỉ kiểm bridge trả đúng định dạng dòng evidence, KHÔNG kiểm chất lượng
        ok = any(re.match(r"- \[[^\]]+\] ", ln) for ln in out)
    hit += int(ok)
    print(f"{case['id']} {'HIT' if ok else 'MISS'}")
print(f"HITRATE {hit}/{len(g['cases'])}")
PY
cat "$TMP/hits.txt"
rate=$(grep HITRATE "$TMP/hits.txt" | awk '{print $2}')
if [ -z "$rate" ]; then
  bad "harness eval" "không có dòng HITRATE (script đo lỗi)"
elif grep -q 'MISS' "$TMP/hits.txt"; then
  bad "hit@k $MODE" "có ca MISS ($rate)"
elif [ "$MODE" = "fake" ]; then
  ok "harness eval chạy với fake zm ($rate) — KHÔNG phải số chất lượng"
else
  ok "hit@k zeromem thật ($rate)"
fi
echo "zeromem-eval-test: $pass pass, $fail fail ($MODE)"
[ $fail -eq 0 ] && echo "PASS" || exit 1
