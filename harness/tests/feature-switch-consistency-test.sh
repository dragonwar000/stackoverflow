#!/usr/bin/env bash
# feature-switch-consistency-test — FR-010: hai copy evidence_terminal giống hệt; FR-009: switch hợp lệ;
# mọi id trong hooklib.GUARDRAIL_FALLBACK có trong features.yaml với class guardrail.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
fail=0
A="harness/validators/evidence_terminal.py"
B="llmwiki/.claude/hooks/validators/evidence_terminal.py"
if cmp -s "$A" "$B"; then echo "  ok   hai copy evidence_terminal giống hệt từng byte"; else echo "  FAIL hai copy evidence_terminal lệch nhau: $A vs $B"; fail=1; fi
python3 - <<'PY' || fail=1
import ast, sys
import yaml
ok = True
d = yaml.safe_load(open("harness/poc-vendor-neutral/policy.yaml", encoding="utf-8"))["rules"]
bad = [k for k, v in d.items() if v.get("switch") not in ("guardrail", "gate", "feature")]
if bad:
    print("  FAIL rule thiếu/sai switch:", bad); ok = False
else:
    g = sorted(v["id"] for v in d.values() if v.get("switch") == "guardrail")
    if g != ["R1", "R14"]:
        print("  FAIL guardrail phải là R1, R14, nhưng là", g); ok = False
    else:
        print(f"  ok   policy: {len(d)} rule đều có switch hợp lệ; guardrail = {g}")
# GUARDRAIL_FALLBACK đọc bằng ast (không import hooklib để khỏi chạy side-effect).
fb = None
for node in ast.parse(open("llmwiki/.claude/hooks/hooklib.py", encoding="utf-8").read()).body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "GUARDRAIL_FALLBACK" for t in node.targets):
        fb = ast.literal_eval(node.value)
if fb is None:
    print("  FAIL không tìm thấy GUARDRAIL_FALLBACK trong hooklib.py"); ok = False
else:
    feats = (yaml.safe_load(open("harness/features.yaml", encoding="utf-8")) or {}).get("features") or {}
    not_guard = [i for i in fb if (feats.get(i) or {}).get("class") != "guardrail"]
    if not_guard:
        print("  FAIL GUARDRAIL_FALLBACK có id không phải class guardrail trong features.yaml:", not_guard); ok = False
    else:
        print(f"  ok   GUARDRAIL_FALLBACK {list(fb)} đều class guardrail trong features.yaml")
sys.exit(0 if ok else 1)
PY
[ $fail -eq 0 ] && echo "PASS" || { echo "FAIL"; exit 1; }
