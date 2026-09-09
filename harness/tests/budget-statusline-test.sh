#!/usr/bin/env bash
# budget-statusline-test — plugin overstack-budget-statusline phải CÒN SỐNG, không chỉ có mặt.
#
# Vì sao cần rào riêng: self-test của plugin nằm trong chính plugin, không nhánh CI nào chạm
# tới. Một script status bar hỏng thì im lặng tuyệt đối (fail-open theo thiết kế) — đúng thứ
# rot mà không ai phát hiện. Rào này gọi self-test đó, và kiểm ba thứ mà self-test KHÔNG tự
# kiểm được vì chúng nằm ngoài file: manifest hợp lệ, plugin có mặt trong marketplace, và
# lệnh slash tồn tại.
#
# Usage: bash harness/tests/budget-statusline-test.sh [repo-root]   (exit 0 = pass)
set -u
ROOT="$(cd "${1:-.}" && pwd)"
P="$ROOT/plugins/overstack-budget-statusline"
fail=0
ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$1"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }

# 1. Self-test của chính engine (21 assertion, tất định).
if out=$(python3 "$P/statusline.py" --self-test 2>&1); then
  ok "statusline.py --self-test: $(printf '%s' "$out" | tail -1)"
else
  bad "statusline.py --self-test ĐỎ"; printf '%s\n' "$out" | sed 's/^/      /'
fi

# 2. Manifest đọc được và khai đúng tên (tên lệch = /plugin install gọi không ra).
name=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['name'])" \
        "$P/.claude-plugin/plugin.json" 2>/dev/null)
[ "$name" = "overstack-budget-statusline" ] \
  && ok "plugin.json khai name=$name" || bad "plugin.json name sai/không đọc được: '$name'"

# 3. Có mặt trong marketplace, và source trỏ đúng thư mục tồn tại.
src=$(python3 - "$ROOT/.claude-plugin/marketplace.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
print(next((p.get("source","") for p in d.get("plugins",[])
            if p.get("name")=="overstack-budget-statusline"), ""))
PY
)
if [ -z "$src" ]; then
  bad "marketplace.json chưa publish plugin — /plugin install sẽ không thấy"
elif [ -d "$ROOT/${src#./}" ]; then
  ok "marketplace source $src tồn tại"
else
  bad "marketplace source '$src' trỏ vào thư mục không có"
fi

# 4. Lệnh slash tồn tại và có frontmatter description (thiếu thì /budget-statusline câm).
CMD="$P/commands/budget-statusline.md"
if [ -f "$CMD" ] && head -5 "$CMD" | grep -q '^description:'; then
  ok "lệnh /budget-statusline có frontmatter description"
else
  bad "thiếu $CMD hoặc thiếu frontmatter description"
fi

# 5. NEGATIVE control — engine phải fail-open THẬT: rác vào, exit 0, không stacktrace.
out=$(printf 'không phải json' | python3 "$P/statusline.py" 2>&1); rc=$?
if [ "$rc" -eq 0 ] && ! printf '%s' "$out" | grep -q 'Traceback'; then
  ok "stdin rác → exit 0, không stacktrace (fail-open thật)"
else
  bad "stdin rác làm engine gãy (rc=$rc)"
fi

# 6. Cách cộng $ phải KHỚP token-budget.py — hai nơi lệch thì thanh và --report nói khác nhau.
same=$(python3 - "$ROOT" <<'PY'
import importlib.util, sys
from pathlib import Path
root = Path(sys.argv[1])
def load(name, p):
    s = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(s)
    sys.path.insert(0, str(p.parent)); s.loader.exec_module(m); return m
tb = load("tb", root / "harness" / "scripts" / "token-budget.py")
sl = load("sl", root / "plugins" / "overstack-budget-statusline" / "statusline.py")
rates = {"default": {"input": 0.003, "output": 0.015}, "opus": {"input": 0.015, "output": 0.075}}
cases = [(326, 139477, "claude-opus-5"), (1000, 1000, "opus"), (0, 0, "x")]
print(int(all(abs(tb.cost_usd(i, o, m, rates) - sl.cost_usd(i, o, m, rates)) < 1e-12
              for i, o, m in cases)))
PY
2>/dev/null)
[ "$same" = "1" ] && ok "công thức \$ khớp token-budget.py trên 3 ca" \
                  || bad "công thức \$ LỆCH token-budget.py → thanh và --report sẽ nói khác nhau"

if [ "$fail" -eq 0 ]; then
  printf '\n\033[1m═══ budget-statusline: \033[1;32mPASS\033[0m\033[0m\n'; exit 0
fi
printf '\n\033[1m═══ budget-statusline: \033[1;31m%d VI PHẠM\033[0m\033[0m\n' "$fail"; exit 1
