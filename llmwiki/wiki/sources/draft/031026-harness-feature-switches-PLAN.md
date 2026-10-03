---
type: draft
title: "Công tắc bật/tắt harness — PLAN thi hành"
status: proposed
timestamp: 2026-10-03
---

# Công tắc bật/tắt harness — PLAN thi hành

**Goal:** Đưa mọi công tắc bật/tắt của harness về một danh mục duy nhất (`harness/features.yaml`) và một cách đọc duy nhất (`hooklib.feature_on`), có lệnh `feature-switch` để bật/tắt cho một dự án. Mặc định của mọi chức năng giữ nguyên.
**Architecture:** Bộ đọc `feature_on` áp thứ tự: cờ `--feature` → env `OVERSTACK_FEATURE_<ID>` → env cũ (`legacy_env`) → `features.local.yaml` (không commit) → config của công tắc → mặc định. Lớp `guardrail` chỉ tắt được qua file cục bộ do CLI ghi kèm `--acknowledge-guardrail`. Lớp `gate` (R19 là gate duy nhất có công tắc hôm nay) giữ đường env/config cũ, mọi lần tắt in stderr và ghi nhật ký. Hook gọi `feature_on`; validator R19 giữ hai copy giống hệt nhau (test so byte).
**Tech stack:** Python 3 (thư viện chuẩn + PyYAML, đã có trên máy dev và được các hook dùng với `try`), bash cho test, GitHub Actions (`.github/workflows/harness.yml`).
**SPEC nguồn:** `wiki/sources/draft/031026-harness-feature-switches.md` (commit 5071bb3e, đã duyệt 03/10/2026)

## Origin
- **SPEC:** `wiki/sources/draft/031026-harness-feature-switches.md`
- **Companion:** `llmwiki/html/031026-harness-feature-switches-seq.html`
- **Commit:** _(verify-before-commit điền)_

## Global constraints
- Mọi chức năng mặc định giữ đúng hành vi hiện tại. Không đổi giá trị mặc định của bất kỳ công tắc nào trong phạm vi này.
- Hook là fail-open: lỗi đọc công tắc không được chặn phiên làm việc. Ngoại lệ là guardrail (xem FR-004): lỗi đọc công tắc guardrail phải giữ guardrail BẬT.
- Mọi lần tắt một chức năng phải in một dòng ra stderr nêu rõ chức năng và tầng đã tắt nó.
- Không xoá rule nào khỏi `harness/poc-vendor-neutral/policy.yaml`. Rule là bất biến. Đề xuất này chỉ thêm đường tắt có kiểm soát cho chức năng, không cho rule.
- Đường dẫn trong script mới phải dùng `overstack_paths.*` hoặc `hooklib.*`. Không ghi cứng `llmwiki/` hoặc `harness/` (lint `bare_path_lint.py`).
- Không dùng `git add -A` hoặc `git add .`. Stage theo danh sách file cụ thể (hook `P1 no-bulk-stage`).
- Trên Windows, Python chạy với `PYTHONUTF8=1`.
- File HTML mới phải tự chứa, không request ra ngoài.

## File structure
- Tạo `harness/features.yaml` — danh mục công tắc: id, lớp, mặc định, env cũ, config, nơi gác. Một trách nhiệm: khai báo.
- Sửa `llmwiki/.claude/hooks/hooklib.py` — thêm `feature_registry` và `feature_on` (chèn trước `def stamp_path(root: str):`). Một trách nhiệm: đọc công tắc cho hook.
- Tạo `harness/scripts/feature-switch.py` — CLI `list | status | on | off`. Một trách nhiệm: đổi công tắc của một dự án.
- Sửa `llmwiki/.claude/hooks/stop.py`, `session_start.py`, `user_prompt_submit.py`, `pre_tool_use.py`, `orca_guard.py` — chuyển cờ sang `feature_on`, giữ mặc định.
- Sửa `llmwiki/.claude/hooks/validators/evidence_terminal.py` và `harness/validators/evidence_terminal.py` — giống hệt nhau từng byte: đọc config đúng thư mục harness, công tắc cục bộ, nhật ký khi tắt.
- Sửa `harness/poc-vendor-neutral/policy.yaml` — thêm `switch:` vào 22 rule.
- Sửa `.gitignore` — bỏ qua file cục bộ và nhật ký.
- Sửa `harness/mechanisms.yaml` — đăng ký cơ chế `feature-switch`.
- Tạo `llmwiki/wiki/concepts/feature-switches.md` — trang concept (có `## Origin`).
- Sửa `llmwiki/wiki/index.md` — thêm một dòng cho trang concept.
- Sửa `.github/workflows/harness.yml` — thêm các step test mới.
- Tạo các test: `harness/tests/feature-switch-test.sh`, `harness/tests/feature-switch-cli-test.sh`, `harness/tests/feature-switch-consistency-test.sh`.

---

### Task 1: danh mục công tắc và bộ đọc `feature_on`

**Thoả:** FR-001, FR-002, FR-004, FR-005, FR-006

**Files:**
- Tạo: `harness/features.yaml`
- Sửa: `llmwiki/.claude/hooks/hooklib.py` (chèn trước dòng `def stamp_path(root: str):`)
- Sửa: `.gitignore` (thêm cuối file)
- Sửa: `.github/workflows/harness.yml` (thêm step sau step có tên `evidence-terminal — R19`)
- Test: `harness/tests/feature-switch-test.sh`

**Interfaces:**
- Consumes: không có (task gốc). Dùng `harness_dir(root)` và `overstack_dir(root)` đã có trong `hooklib.py`.
- Produces: `feature_registry(root: str) -> dict` trả về mục `features` của `harness/features.yaml` (rỗng nếu thiếu hoặc lỗi). `feature_on(root: str, fid: str, default=None, argv=None, env=None) -> tuple[bool, str]` trả về `(bật?, tầng nguồn)`. Nếu `default` là `None`, lấy `default` của registry, rồi mặc định `True`.

**Depends:** —

**Verify:** `bash harness/tests/feature-switch-test.sh .` cho `feature-switch-test: 10 pass, 0 fail` và `PASS`, rc 0.

- [ ] **Step 1: tạo danh mục công tắc**

Tạo `harness/features.yaml`:

```yaml
# harness/features.yaml — danh mục công tắc của harness. Nguồn duy nhất cho hooklib.feature_on.
# class: guardrail (chỉ tắt qua file cục bộ + --acknowledge-guardrail) | gate (tắt qua env/config,
#        có stderr + nhật ký) | feature (tắt tự do).
# consumer: nơi công tắc được gác. null = chưa gắn vào hook nào: tắt bị từ chối để không no-op im lặng.
# default: "on"/"off" hoặc "stamp" (caller quyết theo stamp dự án).
version: 1
features:
  wikigraph:
    class: feature
    doc: Tự vẽ wiki-graph.html ở Stop; nhắc khi vector thiếu ở SessionStart.
    default: stamp
    legacy_env: OVERSTACK_WIKIGRAPH
    legacy_on: ["1"]
    legacy_off: ["0"]
    consumer: llmwiki/.claude/hooks/stop.py
  goal-hook:
    class: feature
    doc: Chỉ thị /orca-graph khi prompt có từ khoá goal.
    default: "on"
    legacy_env: OVERSTACK_GOAL_HOOK
    legacy_off: ["0"]
    consumer: llmwiki/.claude/hooks/user_prompt_submit.py
  self-report:
    class: feature
    doc: Tự chấm hệ mỗi N lượt. OVERSTACK_SELF_REPORT_EVERY là số, không phải công tắc.
    default: "on"
    consumer: null
  agent-trace:
    class: feature
    doc: Sổ kiểm chứng agent. Mặc định TẮT có chủ ý.
    default: "off"
    config_file: harness/agent-trace.config.yaml
    config_key: enabled
    consumer: harness/scripts/agent-trace.py
  evidence-terminal:
    class: gate
    doc: R19 — chuỗi kết luận phải chạm chứng cứ.
    default: "on"
    legacy_env: OVERSTACK_EVIDENCE_TERMINAL
    legacy_on: ["1"]
    legacy_off: ["0", "false", "off"]
    config_file: harness/evidence-terminal.config.yaml
    config_key: enabled
    consumer: llmwiki/.claude/hooks/validators/evidence_terminal.py
  egress-guard:
    class: guardrail
    doc: Chặn network-egress ngoài allow-list (mode warn/block ở harness/egress-guard.config.yaml).
    consumer: llmwiki/.claude/hooks/pre_tool_use.py
  orca-guard:
    class: guardrail
    doc: Chặn lệnh Bash sai của orchestration.
    consumer: llmwiki/.claude/hooks/orca_guard.py
  inject-scan:
    class: guardrail
    doc: Quét prompt injection (harness/scripts/inject-scan.py). Chưa có điểm gác trong hook.
    consumer: null
```

- [ ] **Step 2: viết test fail**

Tạo `harness/tests/feature-switch-test.sh`:

```bash
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

print(f"feature-switch-test: {passed} pass, {failed} fail")
sys.exit(1 if failed else 0)
PY
rc=$?
[ $rc -eq 0 ] && echo "PASS" || { echo "FAIL"; exit 1; }
```

- [ ] **Step 3: chạy cho THẤY fail**

Chạy: `bash harness/tests/feature-switch-test.sh .`
Mong đợi: lỗi `AttributeError: module 'hooklib' has no attribute 'feature_on'` và rc 1. Test đỏ vì chưa có hàm.

- [ ] **Step 4: viết `feature_registry` và `feature_on` trong hooklib**

Chèn đoạn sau vào `llmwiki/.claude/hooks/hooklib.py` ngay trước dòng `def stamp_path(root: str):`:

```python
# ── Công tắc harness: danh mục harness/features.yaml + một cách đọc duy nhất ──
FEATURE_REGISTRY_FILE = "features.yaml"
LOCAL_FEATURES_FILE = "features.local.yaml"


def _read_yaml(path) -> dict:
    try:
        import yaml
        data = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _as_bool(v):
    s = str(v).strip().lower()
    if s in ("on", "1", "true", "yes"):
        return True
    if s in ("off", "0", "false", "no"):
        return False
    return None


def feature_registry(root: str) -> dict:
    """Mục `features` của harness/features.yaml (qua harness_dir). Thiếu hoặc lỗi → {}."""
    return _read_yaml(harness_dir(root) / FEATURE_REGISTRY_FILE).get("features") or {}


def _argv_flag(argv, fid):
    for i, tok in enumerate(argv):
        if tok == "--feature" and i + 1 < len(argv) and argv[i + 1].startswith(fid + "="):
            return _as_bool(argv[i + 1].split("=", 1)[1])
    return None


def feature_on(root: str, fid: str, default=None, argv=None, env=None):
    """Trả (bật?, tầng nguồn). Thứ tự: cờ --feature > env OVERSTACK_FEATURE_<ID> > env cũ (legacy_env)
    > features.local.yaml > config của công tắc > default (tham số, rồi registry, rồi BẬT).
    Guardrail: chỉ file cục bộ được tắt; mọi nguồn khác bị bỏ qua. Lỗi bất kỳ → default, không chặn hook."""
    env = os.environ if env is None else env
    argv = list(argv or [])
    try:
        spec = feature_registry(root).get(fid) or {}
        guard = spec.get("class") == "guardrail"
        fb = default if default is not None else _as_bool(spec.get("default"))
        if fb is None:
            fb = True
        if not guard:
            v = _argv_flag(argv, fid)
            if v is not None:
                return v, "cờ --feature"
            key = "OVERSTACK_FEATURE_" + fid.upper().replace("-", "_")
            if key in env:
                v = _as_bool(env[key])
                if v is not None:
                    return v, f"env {key}"
            le = spec.get("legacy_env")
            if le and le in env:
                raw = str(env[le]).strip().lower()
                if raw in [str(x).lower() for x in (spec.get("legacy_off") or [])]:
                    return False, f"env {le}"
                if raw in [str(x).lower() for x in (spec.get("legacy_on") or [])]:
                    return True, f"env {le}"
        od = overstack_dir(root)
        if od is not None:
            v = _as_bool(_read_yaml(od / LOCAL_FEATURES_FILE).get(fid))
            if v is not None:
                return v, f"file cục bộ {LOCAL_FEATURES_FILE}"
        if not guard and spec.get("config_file") and spec.get("config_key"):
            v = _as_bool(_read_yaml(harness_dir(root) / spec["config_file"]).get(spec["config_key"]))
            if v is not None:
                return v, f"config {spec['config_file']}"
        return fb, "mặc định"
    except Exception:
        return (True if default is None else default), "lỗi đọc công tắc"


```

- [ ] **Step 5: chạy lại — PASS**

Chạy: `bash harness/tests/feature-switch-test.sh .`
Mong đợi: `feature-switch-test: 10 pass, 0 fail`, rồi `PASS`, rc 0.

- [ ] **Step 6: thêm `.gitignore` và đăng ký CI, rồi commit**

Thêm cuối `.gitignore`:

```
# công tắc cục bộ của dự án (feature-switch) và nhật ký tắt/bật — không commit
llmwiki/features.local.yaml
.llmwiki/features.local.yaml
harness/metrics/feature-switch.jsonl
```

Thêm step vào `.github/workflows/harness.yml` sau step có tên `evidence-terminal — R19`:

```yaml
      - name: feature-switch — ma trận feature_on (thứ tự ưu tiên, guardrail fail-closed)
        run: bash harness/tests/feature-switch-test.sh .
```

```bash
git add harness/features.yaml llmwiki/.claude/hooks/hooklib.py harness/tests/feature-switch-test.sh .gitignore .github/workflows/harness.yml
git commit -m "feat(feature-switch): danh mục features.yaml và feature_on (thứ tự ưu tiên, guardrail fail-closed)"
```

---

### Task 2: lệnh `feature-switch`

**Thoả:** FR-001, FR-003, FR-004, FR-007

**Files:**
- Tạo: `harness/scripts/feature-switch.py`
- Test: `harness/tests/feature-switch-cli-test.sh`
- Sửa: `.github/workflows/harness.yml` (thêm step)

**Interfaces:**
- Consumes: `hooklib.feature_on(root, fid, default=None, argv=None, env=None) -> (bool, str)` và `hooklib.feature_registry(root) -> dict` (Task 1). Tìm hooklib: `<root>/llmwiki/.claude/hooks/hooklib.py` trước, rồi `~/.claude/harness/hooks/hooklib.py`.
- Produces: CLI `feature-switch.py [--root DIR] list | status <id> | on <id> | off <id> [--acknowledge-guardrail]`. Ghi file `features.local.yaml` trong thư mục overstack của dự án. Ghi nhật ký vào `harness/metrics/feature-switch.jsonl`.

**Depends:** Task 1

**Verify:** `bash harness/tests/feature-switch-cli-test.sh .` cho `feature-switch-cli-test: 6 pass, 0 fail` và `PASS`, rc 0.

- [ ] **Step 1: viết test fail**

Tạo `harness/tests/feature-switch-cli-test.sh`:

```bash
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
[ $rc -eq 0 ] && grep -q 'egress-guard: off' "$TMP/llmwiki/features.local.yaml" && grep -q 'TẮT egress-guard' "$TMP/e2" && ok "off có ack → ghi file cục bộ + stderr" || bad "off có ack" "rc=$rc"

python3 "$CLI" --root "$TMP" status egress-guard | grep -q 'TẮT.*file cục bộ' && ok "status báo TẮT và nguồn" || bad "status" "$(python3 "$CLI" --root "$TMP" status egress-guard)"

python3 "$CLI" --root "$TMP" off inject-scan > /dev/null 2> "$TMP/e3"; rc=$?
[ $rc -eq 2 ] && grep -q 'chưa gắn' "$TMP/e3" && ok "công tắc chưa gắn hook → từ chối" || bad "chưa gắn" "rc=$rc"

python3 "$CLI" --root "$TMP" on wikigraph > /dev/null && python3 "$CLI" --root "$TMP" status wikigraph | grep -q 'BẬT' && ok "on wikigraph → BẬT" || bad "on" "sai"

[ -f "$TMP/harness/metrics/feature-switch.jsonl" ] && grep -q '"action": "off"' "$TMP/harness/metrics/feature-switch.jsonl" && ok "nhật ký ghi lần tắt" || bad "nhật ký" "thiếu"

echo "feature-switch-cli-test: $pass pass, $fail fail"
[ $fail -eq 0 ] && echo "PASS" || exit 1
```

- [ ] **Step 2: chạy cho THẤY fail**

Chạy: `bash harness/tests/feature-switch-cli-test.sh .`
Mong đợi: `feature-switch-cli-test: 0 pass, 6 fail` và rc 1, vì CLI chưa tồn tại.

- [ ] **Step 3: viết CLI**

Tạo `harness/scripts/feature-switch.py`:

```python
#!/usr/bin/env python3
"""feature-switch — bật/tắt công tắc harness. Danh mục: harness/features.yaml. Logic: hooklib.feature_on.

  feature-switch list
  feature-switch status <id>
  feature-switch on <id>
  feature-switch off <id> [--acknowledge-guardrail]

Guardrail: chỉ tắt được qua file cục bộ và PHẢI có --acknowledge-guardrail.
Gate/feature: tắt ghi file cục bộ, in stderr, ghi harness/metrics/feature-switch.jsonl.
Công tắc chưa gắn vào hook nào (consumer: null) bị từ chối khi tắt, để không tạo no-op im lặng.
agent-trace: giữ đường riêng — gọi agent-trace.py on/off (nó chỉ đọc config của chính nó).
"""
import argparse, datetime, importlib.util, json, os, subprocess, sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overstack_paths import harness_dir, overstack_dir  # noqa: E402

LOCAL = "features.local.yaml"
HOOKLIB_REPO = "llmwiki/.claude/hooks/hooklib.py"  # bare-path: ok — tìm hooklib trong repo trước
HOOKLIB_GLOBAL = ".claude/harness/hooks/hooklib.py"  # bare-path: ok — bản cài toàn cục


def load_hooklib(root: Path):
    for p in (root / HOOKLIB_REPO, Path.home() / HOOKLIB_GLOBAL):
        if p.is_file():
            spec = importlib.util.spec_from_file_location("hooklib", str(p))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit("feature-switch: không tìm thấy hooklib.py (repo hoặc ~/.claude/harness)")


def cmd_list(root: Path, hl) -> int:
    for fid, spec in sorted(hl.feature_registry(str(root)).items()):
        gate = spec.get("consumer") or "(chưa gắn vào hook)"
        print(f"{fid:18} {spec.get('class', 'feature'):10} gác: {gate}")
    return 0


def cmd_status(root: Path, hl, fid: str) -> int:
    spec = hl.feature_registry(str(root)).get(fid)
    if spec is None:
        print(f"không có công tắc {fid}", file=sys.stderr)
        return 2
    on, layer = hl.feature_on(str(root), fid)
    print(f"{fid}: {'BẬT' if on else 'TẮT'} (nguồn: {layer}; lớp: {spec.get('class', 'feature')})")
    return 0


def _write_local(root: Path, fid: str, value: str) -> Path:
    od = overstack_dir(str(root)) or (root / ".llmwiki")  # bare-path: ok — thư mục overstack thật của dự án
    f = od / LOCAL
    data = {}
    if f.is_file():
        loaded = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        data = loaded if isinstance(loaded, dict) else {}
    data[fid] = value
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=True), encoding="utf-8")
    return f


def _audit(root: Path, action: str, fid: str, cls: str, layer: str) -> None:
    d = harness_dir(str(root)) / "metrics"
    d.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "action": action,
           "feature": fid, "class": cls, "layer": layer, "by": "cli"}
    with open(d / "feature-switch.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def cmd_set(root: Path, hl, action: str, fid: str, ack: bool) -> int:
    spec = hl.feature_registry(str(root)).get(fid)
    if spec is None:
        print(f"không có công tắc {fid}", file=sys.stderr)
        return 2
    cls = spec.get("class", "feature")
    if action == "off":
        if not spec.get("consumer"):
            print(f"từ chối: {fid} chưa gắn vào hook nào — tắt sẽ không có tác dụng", file=sys.stderr)
            return 2
        if cls == "guardrail" and not ack:
            print(f"từ chối: {fid} là guardrail. Thêm --acknowledge-guardrail để xác nhận.", file=sys.stderr)
            return 2
    if fid == "agent-trace":
        script = Path(__file__).resolve().parent / "agent-trace.py"
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
        return subprocess.run([sys.executable, str(script), action], env=env).returncode
    value = "on" if action == "on" else "off"
    f = _write_local(root, fid, value)
    if action == "off":
        print(f"[feature-switch] TẮT {fid} (lớp {cls}) — ghi {f}", file=sys.stderr)
        _audit(root, "off", fid, cls, f"file cục bộ {LOCAL}")
    else:
        print(f"[feature-switch] BẬT {fid} — ghi {f}")
        _audit(root, "on", fid, cls, f"file cục bộ {LOCAL}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="feature-switch")
    ap.add_argument("--root", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    st = sub.add_parser("status")
    st.add_argument("id")
    for name in ("on", "off"):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("--acknowledge-guardrail", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    hl = load_hooklib(root)
    if a.cmd == "list":
        return cmd_list(root, hl)
    if a.cmd == "status":
        return cmd_status(root, hl, a.id)
    return cmd_set(root, hl, a.cmd, a.id, a.acknowledge_guardrail)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: chạy lại — PASS**

Chạy: `bash harness/tests/feature-switch-cli-test.sh .`
Mong đợi: `feature-switch-cli-test: 6 pass, 0 fail`, rồi `PASS`, rc 0.

- [ ] **Step 5: đăng ký CI và commit**

Thêm step vào `.github/workflows/harness.yml` sau step `feature-switch — ma trận feature_on`:

```yaml
      - name: feature-switch CLI — list/status/on/off, ack guardrail, từ chối công tắc chưa gắn
        run: bash harness/tests/feature-switch-cli-test.sh .
```

```bash
git add harness/scripts/feature-switch.py harness/tests/feature-switch-cli-test.sh .github/workflows/harness.yml
git commit -m "feat(feature-switch): lệnh list/status/on/off, ack cho guardrail, nhật ký"
```

---

### Task 3: chuyển cờ hiện có sang `feature_on` và thêm `switch` vào policy

**Thoả:** FR-005, FR-006, FR-008, FR-009

**Files:**
- Sửa: `llmwiki/.claude/hooks/stop.py` — import (dòng `from hooklib import running_servers, `), dòng `wikigraph_on = ...` (dòng ~117), dòng `if not (is_framework or has_stamp or os.environ.get("OVERSTACK_WIKIGRAPH") == "1"):` (dòng ~192).
- Sửa: `llmwiki/.claude/hooks/session_start.py` — import (dòng `from hooklib import HARNESS_HOME, audit,`), trong `wikigraph_reminder(root: Path)` dòng `if os.environ.get("OVERSTACK_WIKIGRAPH") != "1":` (dòng ~289).
- Sửa: `llmwiki/.claude/hooks/user_prompt_submit.py` — import (dòng `from hooklib import (audit, find_wiki_dir,`), hàm `goal_directive`, và lời gọi `goal_directive(...)` (dòng ~142).
- Sửa: `llmwiki/.claude/hooks/pre_tool_use.py` — import (dòng `from hooklib import find_validators, project_dir,`), đầu hàm `run_egress_guard`.
- Sửa: `llmwiki/.claude/hooks/orca_guard.py` — import (dòng `from hooklib import audit, read_payload`), đầu `main()` sau `audit(payload, "PreToolUse")`.
- Sửa: `llmwiki/.claude/hooks/validators/evidence_terminal.py` VÀ `harness/validators/evidence_terminal.py` — cùng một patch, giống hệt nhau.
- Sửa: `harness/poc-vendor-neutral/policy.yaml` — thêm `switch:` cho 22 rule.
- Test: chạy lại các test có sẵn (không thêm test mới ở task này).

**Interfaces:**
- Consumes: `hooklib.feature_on` (Task 1), CLI `feature-switch.py` ghi `features.local.yaml` (Task 2).
- Produces: `switch_state(argv, env, cfg) -> (bool, str)` giữ nguyên chữ ký. `load_cfg(root: Path) -> dict` có thể chứa khoá `_layer` khi công tắc cục bộ thắng config. `_audit_off(root: Path, layer: str) -> None` ghi một dòng vào `harness/metrics/feature-switch.jsonl`.

**Depends:** Task 1, Task 2

**Verify:** `bash harness/tests/feature-switch-test.sh .` và `bash harness/tests/evidence-terminal-test.sh .` đều `PASS`. `python3 -m py_compile llmwiki/.claude/hooks/stop.py llmwiki/.claude/hooks/session_start.py llmwiki/.claude/hooks/user_prompt_submit.py llmwiki/.claude/hooks/pre_tool_use.py llmwiki/.claude/hooks/orca_guard.py` rc 0. `cmp -s harness/validators/evidence_terminal.py llmwiki/.claude/hooks/validators/evidence_terminal.py` rc 0.

- [ ] **Step 1: viết test fail cho việc chuyển cờ**

Thêm vào cuối `harness/tests/feature-switch-test.sh`, trước dòng `print(f"feature-switch-test: ...)`, một ca mới được gọi bằng cách kiểm chuỗi trong mã nguồn (đảm bảo cờ cũ không còn đọc trực tiếp):

```bash
for pair in "llmwiki/.claude/hooks/stop.py:OVERSTACK_WIKIGRAPH" \
            "llmwiki/.claude/hooks/session_start.py:OVERSTACK_WIKIGRAPH" \
            "llmwiki/.claude/hooks/user_prompt_submit.py:OVERSTACK_GOAL_HOOK"; do
  f=${pair%%:*}; k=${pair##*:}
  if grep -q "os.environ.get(\"$k\")" "$f"; then echo "  FAIL còn đọc env trực tiếp: $f $k"; exit 1; fi
done
echo "  ok   không còn đọc env cũ trực tiếp ở stop/session_start/user_prompt_submit"
```

Chạy: `bash harness/tests/feature-switch-test.sh .`
Mong đợi: `FAIL còn đọc env trực tiếp` và rc 1, vì các hook chưa được sửa.

- [ ] **Step 2: sửa các hook**

Viết một script patch, dừng nếu một đoạn không khớp đúng một lần:

```python
# patch_hooks.py — chạy từ gốc repo. Dừng nếu một đoạn không khớp đúng 1 lần.
import pathlib

def edit(path, pairs):
    p = pathlib.Path(path)
    t = p.read_text(encoding="utf-8")
    for old, new in pairs:
        n = t.count(old)
        assert n == 1, (path, n, old[:70])
        t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")
    print("patched", path)

edit("llmwiki/.claude/hooks/stop.py", [
    ("from hooklib import running_servers, ", "from hooklib import feature_on, running_servers, "),
    ('    wikigraph_on = bool(wg) and (is_framework or has_stamp or os.environ.get("OVERSTACK_WIKIGRAPH") == "1")',
     '    wikigraph_on = bool(wg) and feature_on(root, "wikigraph", default=(is_framework or has_stamp))[0]'),
    ('    if not (is_framework or has_stamp or os.environ.get("OVERSTACK_WIKIGRAPH") == "1"):',
     '    if not (is_framework or has_stamp or feature_on(root, "wikigraph", default=False)[0]):'),
])
edit("llmwiki/.claude/hooks/session_start.py", [
    ("from hooklib import HARNESS_HOME, audit,", "from hooklib import HARNESS_HOME, audit, feature_on,"),
    ('        if os.environ.get("OVERSTACK_WIKIGRAPH") != "1":',
     '        if not feature_on(str(root), "wikigraph", default=False)[0]:'),
])
edit("llmwiki/.claude/hooks/user_prompt_submit.py", [
    ("from hooklib import (audit, find_wiki_dir,", "from hooklib import (audit, feature_on, find_wiki_dir,"),
    ('def goal_directive(prompt, atlas=""):', 'def goal_directive(prompt, atlas="", root=""):'),
    ('    if os.environ.get("OVERSTACK_GOAL_HOOK") == "0":',
     '    if not feature_on(root or os.getcwd(), "goal-hook")[0]:'),
    ('goal_directive(payload.get("prompt", ""), str(atlas) if atlas.is_file() else "")',
     'goal_directive(payload.get("prompt", ""), str(atlas) if atlas.is_file() else "", root=project_dir(payload))'),
])
edit("llmwiki/.claude/hooks/pre_tool_use.py", [
    ("from hooklib import find_validators, project_dir,", "from hooklib import feature_on, find_validators, project_dir,"),
    ('    guard = resolve_tool(root, "harness/scripts/egress-guard.py")',
     '    if not feature_on(root, "egress-guard")[0]:\n        return\n    guard = resolve_tool(root, "harness/scripts/egress-guard.py")'),
])
edit("llmwiki/.claude/hooks/orca_guard.py", [
    ("from hooklib import audit, read_payload", "from hooklib import audit, feature_on, project_dir, read_payload"),
    ('    audit(payload, "PreToolUse")',
     '    audit(payload, "PreToolUse")\n    if not feature_on(project_dir(payload), "orca-guard")[0]:\n        sys.exit(0)'),
])
```

Chạy: `python3 patch_hooks.py` từ gốc repo, rồi xoá `patch_hooks.py`.
Mong đợi: năm dòng `patched ...`, không có `AssertionError`.

- [ ] **Step 3: sửa validator R19 (hai copy, cùng một patch)**

Viết `patch_validator.py`, áp cùng nội dung cho cả hai file. Dừng nếu không khớp:

```python
# patch_validator.py — áp cùng một patch cho hai copy evidence_terminal.py.
import pathlib, sys

COPIES = ["harness/validators/evidence_terminal.py",
          "llmwiki/.claude/hooks/validators/evidence_terminal.py"]

NEW_LOAD_CFG = '''def _harness_dir(root: Path) -> Path:
    """Thư mục harness của dự án: .harness (downstream) hoặc harness (repo framework)."""
    for n in (".harness", "harness"):
        if (Path(root) / n).is_dir():
            return Path(root) / n
    return Path(root) / "harness"


def _local_override(root: Path, fid: str):
    """features.local.yaml (công tắc cục bộ, không commit). Trả bool hoặc None."""
    for n in (".llmwiki", "llmwiki"):
        f = Path(root) / n / "features.local.yaml"
        if f.is_file():
            try:
                import yaml
                d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
                v = d.get(fid) if isinstance(d, dict) else None
                if isinstance(v, bool):
                    return v
                if str(v).strip().lower() in ("on", "off"):
                    return str(v).strip().lower() == "on"
            except Exception:
                return None
            return None
    return None


def load_cfg(root: Path) -> dict:
    """Đọc config R19 đúng thư mục harness của dự án, rồi áp công tắc cục bộ features.local.yaml.
    Lỗi đọc file không im lặng: ghi rõ ra stderr rồi dùng mặc định."""
    cfg = dict(_FALLBACK)
    f = _harness_dir(root) / "evidence-terminal.config.yaml"
    if f.is_file():
        try:
            import yaml
            cur = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            if isinstance(cur, dict):
                cfg.update(cur)
        except Exception as e:
            sys.stderr.write(f"[R19] không đọc được {f}: {e} — dùng mặc định\\n")
    loc = _local_override(root, "evidence-terminal")
    if loc is not None:
        cfg["enabled"] = loc
        cfg["_layer"] = "features.local.yaml (feature-switch)"
    return cfg


'''

AUDIT_OFF = '''def _audit_off(root: Path, layer: str) -> None:
    """Mỗi lần TẮT gate R19 ghi một dòng nhật ký. Fail-open."""
    try:
        import json, datetime
        d = _harness_dir(root) / "metrics"
        d.mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "feature": "evidence-terminal",
               "class": "gate", "layer": layer, "by": "validator"}
        with open(d / "feature-switch.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\\n")
    except Exception:
        pass


'''

for path in COPIES:
    p = pathlib.Path(path)
    t = p.read_text(encoding="utf-8")
    # 1. thay toàn bộ load_cfg
    start = t.index("def load_cfg(root: Path) -> dict:")
    end = t.index("\n\n\ndef ", start) + 3
    t = t[:start] + NEW_LOAD_CFG + t[end:]
    # 2. switch_state: lớp cục bộ hiện trong thông báo
    old = '        return False, "harness/evidence-terminal.config.yaml (enabled: false)"'
    assert t.count(old) == 1, (path, "switch_state")
    t = t.replace(old, '        return False, cfg.get("_layer") or "harness/evidence-terminal.config.yaml (enabled: false)"')
    # 3. ghi nhật ký khi tắt, trong main()
    old = '        sys.exit(0)\n\n    if "--self-test" in argv:'
    assert t.count(old) == 1, (path, "main gate")
    t = t.replace(old, '        _audit_off(root, layer)\n        sys.exit(0)\n\n    if "--self-test" in argv:')
    # 4. định nghĩa _audit_off trước main()
    assert t.count("def main() -> None:") == 1, (path, "def main")
    t = t.replace("def main() -> None:", AUDIT_OFF + "def main() -> None:")
    p.write_text(t, encoding="utf-8")
    print("patched", path)
```

Chạy: `python3 patch_validator.py` từ gốc repo, rồi xoá `patch_validator.py`.
Mong đợi: hai dòng `patched ...`. Kiểm tra: `cmp -s harness/validators/evidence_terminal.py llmwiki/.claude/hooks/validators/evidence_terminal.py` rc 0.

- [ ] **Step 4: thêm `switch` vào 22 rule của policy**

Viết `add_switch.py`. Chỉ R1 và R14 là `guardrail`, còn lại là `gate`. Chèn ngay sau dòng `    id: Rx` trong từng rule. Idempotent:

```python
# add_switch.py — thêm `switch:` vào 22 rule của harness/poc-vendor-neutral/policy.yaml.
import pathlib, re

p = pathlib.Path("harness/poc-vendor-neutral/policy.yaml")
t = p.read_text(encoding="utf-8")
if "\n    switch: " in t:
    print("đã có switch — không sửa lại"); raise SystemExit(0)

def cls(rid):
    return "guardrail" if rid in ("R1", "R14") else "gate"

n = 0
def repl(m):
    global n
    n += 1
    return f"{m.group(0)}    switch: {cls(m.group(2))}\n"

t2 = re.sub(r"^(  (\w+):\n)    id: (R\d+)\n", lambda m: f"{m.group(1)}    id: {m.group(3)}\n    switch: {cls(m.group(3))}\n", t, flags=re.M)
count = len(re.findall(r"^    switch: (guardrail|gate)$", t2, flags=re.M))
assert count == 22, count
p.write_text(t2, encoding="utf-8")
print("đã thêm switch cho", count, "rule")
```

Chạy: `python3 add_switch.py`, rồi xoá `add_switch.py`.
Mong đợi: `đã thêm switch cho 22 rule`.

- [ ] **Step 5: chạy kiểm — PASS**

Chạy: `bash harness/tests/feature-switch-test.sh .` → `PASS`.
Chạy: `bash harness/tests/evidence-terminal-test.sh .` → `PASS` (kiểm công tắc R19 cũ không đổi).
Chạy: `python3 llmwiki/.claude/hooks/validators/evidence_terminal.py --self-test` → không có dòng `FAIL:`, rc 0.

- [ ] **Step 6: commit**

```bash
git add llmwiki/.claude/hooks/hooklib.py llmwiki/.claude/hooks/stop.py llmwiki/.claude/hooks/session_start.py llmwiki/.claude/hooks/user_prompt_submit.py llmwiki/.claude/hooks/pre_tool_use.py llmwiki/.claude/hooks/orca_guard.py llmwiki/.claude/hooks/validators/evidence_terminal.py harness/validators/evidence_terminal.py harness/poc-vendor-neutral/policy.yaml harness/tests/feature-switch-test.sh
git commit -m "feat(feature-switch): chuyển cờ sang feature_on, R19 đọc đúng harness dir và công tắc cục bộ, switch cho 22 rule"
```

---

### Task 4: kiểm nhất quán, đăng ký và tài liệu

**Thoả:** FR-010, FR-008, FR-009, FR-001

**Files:**
- Tạo: `harness/tests/feature-switch-consistency-test.sh`
- Sửa: `harness/mechanisms.yaml` (thêm một mục vào cuối danh sách `mechanisms`)
- Tạo: `llmwiki/wiki/concepts/feature-switches.md`
- Sửa: `llmwiki/wiki/index.md` (thêm một dòng)
- Sửa: `.github/workflows/harness.yml` (thêm step)

**Interfaces:**
- Consumes: hai copy `evidence_terminal.py` (Task 3), trường `switch` trong `harness/poc-vendor-neutral/policy.yaml` (Task 3), `harness/features.yaml` (Task 1).
- Produces: test nhất quán trả `PASS` khi hai copy giống hệt nhau, mọi rule có `switch` hợp lệ, và đúng hai rule `guardrail` là R1 và R14.

**Depends:** Task 3

**Verify:** `bash harness/tests/feature-switch-consistency-test.sh .` cho `PASS`, rc 0.

- [ ] **Step 1: viết test nhất quán (fail trước khi có gì để kiểm)**

Tạo `harness/tests/feature-switch-consistency-test.sh`:

```bash
#!/usr/bin/env bash
# feature-switch-consistency-test — FR-010: hai copy evidence_terminal giống hệt; FR-009: switch hợp lệ.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
A="harness/validators/evidence_terminal.py"
B="llmwiki/.claude/hooks/validators/evidence_terminal.py"
if cmp -s "$A" "$B"; then echo "  ok   hai copy evidence_terminal giống hệt từng byte"; else echo "  FAIL hai copy evidence_terminal lệch nhau: $A vs $B"; exit 1; fi
python3 - <<'PY'
import sys, yaml
d = yaml.safe_load(open("harness/poc-vendor-neutral/policy.yaml", encoding="utf-8"))["rules"]
bad = [k for k, v in d.items() if v.get("switch") not in ("guardrail", "gate", "feature")]
if bad:
    print("  FAIL rule thiếu/sai switch:", bad); sys.exit(1)
g = sorted(v["id"] for v in d.values() if v.get("switch") == "guardrail")
if g != ["R1", "R14"]:
    print("  FAIL guardrail phải là R1, R14, nhưng là", g); sys.exit(1)
print(f"  ok   policy: {len(d)} rule đều có switch hợp lệ; guardrail = {g}")
PY
rc=$?
[ $rc -eq 0 ] && echo "PASS" || { echo "FAIL"; exit 1; }
```

Chạy: `bash harness/tests/feature-switch-consistency-test.sh .`
Mong đợi: ca 1 `ok`, ca 2 `ok` (Task 3 đã thêm `switch`). Nếu ca 1 FAIL thì quay lại Task 3 Step 3 và chạy lại patch.

- [ ] **Step 2: đăng ký cơ chế trong mechanisms**

Thêm vào cuối danh sách `mechanisms:` trong `harness/mechanisms.yaml`:

```yaml
  - id: feature-switch
    name: feature-switch
    kind: tool
    surface: [mechanism]
    desc: "Công tắc bật/tắt harness: harness/features.yaml + hooklib.feature_on. Guardrail tắt cần --acknowledge-guardrail; gate tắt qua env/config có stderr và nhật ký."
    live_probe: harness/scripts/feature-switch.py
```

Kiểm: `python3 -c "import yaml; d=yaml.safe_load(open('harness/mechanisms.yaml')); print(any(m['id']=='feature-switch' for m in d['mechanisms']))"` → `True`.

- [ ] **Step 3: viết trang concept và dòng index**

Tạo `llmwiki/wiki/concepts/feature-switches.md`:

```markdown
---
type: concept
title: "Công tắc bật/tắt harness — ba lớp guardrail, gate, feature"
tags: [feature-switch, harness, guardrail, gate, config]
timestamp: 2026-10-03
---

# Công tắc bật/tắt harness

Mọi công tắc của harness khai trong `harness/features.yaml` và được đọc bằng một hàm: `hooklib.feature_on`. Thứ tự ưu tiên: cờ `--feature` > env `OVERSTACK_FEATURE_<ID>` > env cũ > `features.local.yaml` > config của công tắc > mặc định.

Ba lớp (trường `switch` trong `harness/poc-vendor-neutral/policy.yaml` và `class` trong `features.yaml`):

- **guardrail** (R1 no-write-raw, R14 patterns-protected, egress-guard, orca-guard, inject-scan): chỉ tắt qua `feature-switch off <id> --acknowledge-guardrail`, ghi vào file cục bộ. Không có đường env hay config.
- **gate** (R2…R22, gồm R19 evidence-terminal): giữ đường env và config cũ. Mỗi lần tắt in stderr và ghi `harness/metrics/feature-switch.jsonl`.
- **feature** (wikigraph, goal-hook, agent-trace, self-report): tắt tự do, mặc định của từng công tắc giữ nguyên.

Lệnh: `python3 harness/scripts/feature-switch.py list | status <id> | on <id> | off <id> [--acknowledge-guardrail]`.

## Origin
- **SPEC:** `wiki/sources/draft/031026-harness-feature-switches.md`
- **PLAN:** `wiki/sources/draft/031026-harness-feature-switches-PLAN.md`
```

Thêm một dòng vào `llmwiki/wiki/index.md` (chỉ thêm, không sửa dòng khác):

```
| [feature-switches](concepts/feature-switches.md) | concept | Công tắc bật/tắt harness: ba lớp guardrail, gate, feature |
```

Kiểm: `python3 harness/validators/okf_frontmatter.py llmwiki/wiki/concepts/feature-switches.md` rc 0 và `python3 harness/validators/origin_required.py llmwiki/wiki/concepts/feature-switches.md` rc 0.

- [ ] **Step 4: đăng ký CI và commit**

Thêm step vào `.github/workflows/harness.yml`:

```yaml
      - name: feature-switch — hai copy evidence_terminal giống hệt, policy có switch hợp lệ
        run: bash harness/tests/feature-switch-consistency-test.sh .
```

```bash
git add harness/tests/feature-switch-consistency-test.sh harness/mechanisms.yaml llmwiki/wiki/concepts/feature-switches.md llmwiki/wiki/index.md .github/workflows/harness.yml
git commit -m "docs(feature-switch): kiểm nhất quán hai copy và policy, đăng ký mechanisms, trang concept"
```

## Global self-review
1. **Phủ SPEC.** FR-001 → T1 (registry), T2 (list). FR-002 → T1 (thứ tự ưu tiên). FR-003 → T2 (on/off một lệnh). FR-004 → T1 (guardrail chỉ qua local), T2 (ack). FR-005 → T1, T3 (mặc định giữ nguyên, test ca 4 và 8). FR-006 → T1 (env cũ), T3 (R19 env/config giữ). FR-007 → T2 (status). FR-008 → T3 (nhật ký khi tắt R19), T4 (trang concept). FR-009 → T3 (switch cho 22 rule), T4 (kiểm). FR-010 → T4 (cmp hai copy). Không yêu cầu nào bị bỏ rơi.
2. **Quét placeholder.** Đã rà các từ bị cấm. Mọi bước đổi code có code đầy đủ hoặc script patch có assert.
3. **Nhất quán tên.** Hàm `feature_on`, `feature_registry`, `load_cfg`, `_audit_off`, `_local_override`, `_harness_dir`, `switch_state`. Tên file `features.yaml` và `features.local.yaml`. Id công tắc `wikigraph`, `goal-hook`, `egress-guard`, `orca-guard`, `evidence-terminal`, `agent-trace`, `self-report`, `inject-scan`. Tên lệnh `feature-switch`.
