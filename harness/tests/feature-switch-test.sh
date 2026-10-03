#!/usr/bin/env bash
# feature-switch-test — ma trận feature_on: thứ tự ưu tiên, guardrail fail-closed, env cũ, file cục bộ.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
ROOT="$(pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/llmwiki" "$TMP/harness"
cp harness/features.yaml "$TMP/harness/"
printf 'enabled: true\n' > "$TMP/harness/agent-trace.config.yaml"
HOOKLIB="$ROOT/llmwiki/.claude/hooks/hooklib.py"

python3 - "$HOOKLIB" "$TMP" <<'PY'
import importlib.util, os, sys
hl_path, tmp = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("hooklib", hl_path)
hl = importlib.util.module_from_spec(spec); spec.loader.exec_module(hl)
passed = failed = 0
def check(name, got, want):
    global passed, failed
    if got == want:
        passed += 1; print(f"  ok   {name}")
    else:
        failed += 1; print(f"  FAIL {name}: got={got!r} want={want!r}")

# 1 guardrail, không có gì → BẬT, nguồn mặc định
check("1 guardrail mặc định bật", hl.feature_on(tmp, "egress-guard"), (True, "mặc định"))
# 2 guardrail: env tắt bị BỎ QUA (không có env cũ)
check("2 guardrail env tắt bị bỏ qua", hl.feature_on(tmp, "egress-guard", env={"OVERSTACK_FEATURE_EGRESS_GUARD": "off"})[0], True)
# 3 guardrail: file cục bộ tắt được
os.makedirs(os.path.join(tmp, "llmwiki"), exist_ok=True)
open(os.path.join(tmp, "llmwiki", "features.local.yaml"), "w").write("egress-guard: off\n")
check("3 guardrail tắt qua file cục bộ", hl.feature_on(tmp, "egress-guard"), (False, "file cục bộ features.local.yaml"))
os.remove(os.path.join(tmp, "llmwiki", "features.local.yaml"))
# 4 wikigraph mặc định (caller truyền False) → TẮT
check("4 wikigraph mặc định theo caller", hl.feature_on(tmp, "wikigraph", default=False, env={})[0], False)
# 5 env cũ =1 → BẬT
check("5 env OVERSTACK_WIKIGRAPH=1", hl.feature_on(tmp, "wikigraph", default=False, env={"OVERSTACK_WIKIGRAPH": "1"})[0], True)
# 6 env cũ =0 thắng mặc định BẬT
check("6 env OVERSTACK_WIKIGRAPH=0 thắng default", hl.feature_on(tmp, "wikigraph", default=True, env={"OVERSTACK_WIKIGRAPH": "0"})[0], False)
# 7 cờ --feature thắng env
check("7 cờ --feature=on thắng env=0", hl.feature_on(tmp, "wikigraph", default=False, argv=["--feature", "wikigraph=on"], env={"OVERSTACK_WIKIGRAPH": "0"})[0], True)
# 8 goal-hook: env cũ =0 → TẮT
check("8 goal-hook env=0 tắt", hl.feature_on(tmp, "goal-hook", env={"OVERSTACK_GOAL_HOOK": "0"})[0], False)
# 9 registry thiếu → guardrail vẫn BẬT
empty = os.path.join(tmp, "empty"); os.makedirs(empty)
check("9 registry thiếu → guardrail bật", hl.feature_on(empty, "egress-guard")[0], True)
# 10 config của công tắc (agent-trace enabled: true)
check("10 config harness/agent-trace.config.yaml", hl.feature_on(tmp, "agent-trace", env={}), (True, "config harness/agent-trace.config.yaml"))
# 11 registry thiếu + env tắt guardrail → vẫn BẬT (guardrail cố định, FR-004)
check("11 registry thiếu + env off guardrail vẫn bật", hl.feature_on(empty, "egress-guard", env={"OVERSTACK_FEATURE_EGRESS_GUARD": "off"})[0], True)
# 12 lỗi đọc (root không hợp lệ) → guardrail luôn BẬT, bỏ qua default=False truyền vào
check("12 exception guardrail → bật bất kể default", hl.feature_on(None, "egress-guard", default=False, env={}), (True, "lỗi đọc công tắc"))
# 13 lỗi đọc → feature trả default truyền vào
check("13 exception feature → default", hl.feature_on(None, "wikigraph", default=False, env={}), (False, "lỗi đọc công tắc"))
# 14 evidence-terminal: env=1 KHÔNG thắng config enabled:false (giữ hành vi hôm nay)
open(os.path.join(tmp, "harness", "evidence-terminal.config.yaml"), "w").write("enabled: false\n")
check("14 env=1 không thắng config enabled:false", hl.feature_on(tmp, "evidence-terminal", env={"OVERSTACK_EVIDENCE_TERMINAL": "1"}), (False, "config harness/evidence-terminal.config.yaml"))
# 15 guardrail: caller truyền default=False vẫn BẬT (không hạ guardrail bằng tham số)
check("15 guardrail default=False vẫn bật", hl.feature_on(tmp, "egress-guard", default=False, env={}), (True, "mặc định"))
# 16 layout dự án khách (.llmwiki/ + .harness/): config của công tắc vẫn được đọc
dot = os.path.join(tmp, "dot"); os.makedirs(os.path.join(dot, ".llmwiki")); os.makedirs(os.path.join(dot, ".harness"))
open(os.path.join(dot, ".harness", "features.yaml"), "w").write(open(os.path.join(tmp, "harness", "features.yaml"), encoding="utf-8").read())
open(os.path.join(dot, ".harness", "evidence-terminal.config.yaml"), "w").write("enabled: false\n")
check("16 layout .harness đọc được config", hl.feature_on(dot, "evidence-terminal", env={}), (False, "config harness/evidence-terminal.config.yaml"))

print(f"feature-switch-test: {passed} pass, {failed} fail")
sys.exit(1 if failed else 0)
PY
rc=$?
[ $rc -eq 0 ] && echo "PASS" || { echo "FAIL"; exit 1; }
