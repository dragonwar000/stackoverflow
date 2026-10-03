---
type: draft
title: "zeromem chạy song song với mem-rank và memory-map — PLAN thi hành"
status: proposed
timestamp: 2026-10-03
---

# zeromem chạy song song với mem-rank và memory-map — PLAN thi hành

**Goal:** Thêm zeromem làm backend memory mặc định của project, chạy song song với mem-rank và memory-map. Người dùng chọn backend bằng khoá `memory.backend` trong config. mem-rank giữ đúng hành vi cũ.
**Architecture:** Một bridge Python `harness/scripts/zeromem-bridge.py` là lớp duy nhất giữa hook và binary `zm`. Bridge gọi `zm mcp` qua JSON-RPC stdio, và gọi `zm hook` để spool turn từ transcript. Mỗi project có một store riêng ngoài repo, tại `~/.overstack/zeromem/<khoá-project>`, và mọi store cùng link một model dùng chung. Hook Stop và SessionEnd gọi `ingest`, SessionStart gọi `recall`. memory-map thêm `--source zeromem` và đọc `zeromem.db` ở chế độ chỉ đọc.
**Tech stack:** Python 3 (thư viện chuẩn, không thêm dependency), bash, zm pin `eda212665a35cd01c188121e759de282728238d5` (Rust, build bằng cargo `--locked`), model `Xenova/bge-small-en-v1.5` revision `ea104dacec62c0de699686887e3f920caeb4f3e3`. Test: bash script, và fake zm viết bằng Python.
**SPEC nguồn:** `wiki/sources/draft/031026-zeromem-parallel-backend.md` (đã duyệt 03/10/2026)

## Origin
- **SPEC:** `wiki/sources/draft/031026-zeromem-parallel-backend.md`
- **Companion:** `llmwiki/html/031026-zeromem-parallel-backend-seq.html`
- **Commit:** _(verify-before-commit điền)_

## Global constraints
- Ngân sách Stop: `_BUDGET_S = float(os.environ.get("OVERSTACK_STOP_BUDGET_S", "20"))` trong `llmwiki/.claude/hooks/stop.py:35`. Mọi việc ghi memory của Stop phải nằm trong ngân sách này, hoặc chuyển sang SessionEnd.
- Revision zeromem đã ghim: `eda212665a35cd01c188121e759de282728238d5`, crate `zeromem` phiên bản `0.3.0`, giấy phép MIT.
- Model đã ghim: `Xenova/bge-small-en-v1.5`, revision `ea104dacec62c0de699686887e3f920caeb4f3e3`. Sha256 từng file theo `harness/zeromem/zeromem-lock.json`. Không cài model nếu sha không khớp.
- Store zeromem nằm ngoài repo, quyền thư mục `0700`, không bao giờ được commit.
- Tool output và nội dung file đọc được không được đi vào store.
- Script mới phải dùng `overstack_paths.*` hoặc `hooklib.*` để đường dẫn chạy đúng ở máy khách. Không ghi cứng `llmwiki/` hoặc `harness/` (theo lint `bare_path_lint.py`).
- Trên Windows, `bootstrap.sh` đặt `PYTHONUTF8=1` và `PYTHONIOENCODING=utf-8` trước khi chạy Python.
- Fail-open: thiếu `zm`, thiếu model, timeout, schema lạ đều không được chặn phiên làm việc.
- `zm mcp` không nhận session id từ Claude Code. Bridge phải tự truyền `exclude_session`.

## File structure
- Tạo `harness/scripts/zeromem-install.sh` — cài zm đúng revision, tải model, kiểm sha256. Một trách nhiệm: cài và xác minh.
- Tạo `harness/scripts/zeromem-bridge.py` — cầu nối duy nhất giữa hook và zm: `store_home`, `recall`, `forget_session`, `stats`, `ingest`, `status`, `memory_backend`. Mọi lệnh đi qua `zm mcp` hoặc `zm hook`, không đọc trực tiếp `zeromem.db`.
- Tạo `harness/tests/fixtures/fake-zm.py` — fake zm trả JSON cố định, dùng cho CI.
- Tạo `harness/tests/zeromem-install-test.sh`, `harness/tests/zeromem-bridge-test.sh`, `harness/tests/zeromem-hooks-test.sh`, `harness/tests/zeromem-memory-map-test.sh`, `harness/tests/zeromem-eval-test.sh`.
- Tạo `harness/evals/zeromem-cross-session.json` — golden hai phiên cho hit@k.
- Sửa `harness/zeromem/zeromem-lock.json` — đã copy, chỉ commit, không đổi nội dung.
- Sửa `harness/mem-rank.config.yaml` — thêm khoá `memory.backend`.
- Sửa `llmwiki/.claude/hooks/hooklib.py` — thêm `memory_backend(root)`.
- Sửa `llmwiki/.claude/hooks/stop.py` — thêm `zeromem_write`, gate mem-rank episode theo backend.
- Sửa `llmwiki/.claude/hooks/session_start.py` — thêm `_zeromem_recall`, gate `recall` theo backend.
- Sửa `llmwiki/.claude/hooks/session_end.py` — gọi `zeromem_write` ở SessionEnd.
- Sửa `fdk/tools/memory-map.py` — thêm `--source zeromem`.
- Sửa `.github/workflows/harness.yml` — thêm các step chạy test mới.

## Cổng ngược đã kiểm (không chặn, ghi để người duyệt biết)
1. `llmwiki/.claude/hooks/session_end.py` không đọc `transcript_path` trong code hiện tại. Nhánh SessionEnd của PLAN chỉ chạy khi payload có trường này, và thiếu thì bỏ qua. Stop vẫn là đường ghi chính.
2. `harness/scripts/bnal_config.py` đọc config bằng `Path(root) / "harness"` cứng, và hàm này không đọc được layout `.harness/` của downstream. PLAN không dùng `bnal_config`. `memory_backend` đọc file config qua `harness_dir` từ `overstack_paths`.
3. `zeromem_recall` cần một câu truy vấn, còn SessionStart không có câu hỏi sẵn. PLAN chọn subject của commit gần nhất làm câu truy vấn. Đây là quyết định (default), không phải SPEC.
4. Nếu backend là `zeromem` mà không có binary `zm`, `memory_backend` tự rơi về `mem-rank` và in cảnh báo ra stderr. Tránh mất hoàn toàn bộ nhớ trên máy chưa cài zm. Đây là bổ sung so với SPEC.

### Task 1: cài và ghim zeromem

**Thoả:** FR-007

**Files:**
- Tạo: `harness/scripts/zeromem-install.sh`
- Tạo: `harness/tests/zeromem-install-test.sh`
- Sửa: `.github/workflows/harness.yml` (thêm step `bash harness/tests/zeromem-install-test.sh .` cạnh step memory-map)

**Interfaces:**
- Consumes: không có (task gốc).
- Produces: CLI `zeromem-install.sh [--verify-only DIR]`. Không có `--verify-only`: cài zm và tải model vào `$OVERSTACK_ZEROMEM_SHARED/models`, thoát 0 khi sha khớp, thoát 1 khi lệch. Có `--verify-only DIR`: chỉ kiểm sha các file trong `DIR`, thoát 0 hoặc 1. Biến môi trường: `ZEROMEM_LOCK` (mặc định `harness/zeromem/zeromem-lock.json` cạnh script), `OVERSTACK_ZEROMEM_SHARED` (mặc định `~/.overstack/zeromem/_shared`). Sau khi chạy thành công, `zm` nằm trong PATH và thư mục `$OVERSTACK_ZEROMEM_SHARED/models/models--Xenova--bge-small-en-v1.5/snapshots/<rev>/` chứa đủ file.

**Depends:** —

**Verify:** `bash harness/tests/zeromem-install-test.sh .` cho `PASS`, rc 0.

- [ ] **Step 1: viết test fail cho chế độ kiểm sha**

Tạo `harness/tests/zeromem-install-test.sh`:

```bash
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
```

- [ ] **Step 2: chạy cho thấy fail**

Chạy: `bash harness/tests/zeromem-install-test.sh .`
Mong đợi: `zeromem-install-test: 0 pass, 3 fail` và rc 1, vì `harness/scripts/zeromem-install.sh` chưa tồn tại.

- [ ] **Step 3: viết script cài đặt**

Tạo `harness/scripts/zeromem-install.sh`:

```bash
#!/usr/bin/env bash
# zeromem-install — cài zm đúng revision đã ghim và tải model bge-small, kiểm sha256 trước khi nhận.
#   zeromem-install.sh                    cài zm + tải model vào thư mục chung, rồi kiểm sha
#   zeromem-install.sh --verify-only DIR  chỉ kiểm sha các file model trong DIR
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
LOCK="${ZEROMEM_LOCK:-$HERE/../zeromem/zeromem-lock.json}"
SHARED="${OVERSTACK_ZEROMEM_SHARED:-$HOME/.overstack/zeromem/_shared}"

verify_dir() {  # $1 = thư mục chứa các file model theo đường dẫn tương đối trong lock
  python3 - "$LOCK" "$1" <<'PY'
import hashlib, json, os, sys
lock = json.load(open(sys.argv[1], encoding="utf-8"))
base = sys.argv[2]
files = lock["model"]["files"]
bad = 0
for rel, want in files.items():
    p = os.path.join(base, rel)
    if not os.path.isfile(p):
        print(f"THIẾU {rel}")
        bad += 1
        continue
    got = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if got != want:
        print(f"LỆCH {rel}")
        bad += 1
print(f"{len(files) - bad}/{len(files)} file khớp sha256")
sys.exit(1 if bad else 0)
PY
}

if [ "${1:-}" = "--verify-only" ]; then
  verify_dir "${2:?thiếu DIR}"; exit $?
fi

REPO=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['repository'])" "$LOCK")
REV=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['rev'])" "$LOCK")
MODEL_REPO=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['model']['repository'])" "$LOCK")
MODEL_REV=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['model']['rev'])" "$LOCK")

command -v cargo >/dev/null 2>&1 || { echo "thiếu cargo — cài rustup trước"; exit 2; }
cargo install --git "$REPO" --rev "$REV" --locked zeromem || { echo "cargo install zeromem thất bại"; exit 1; }
command -v zm >/dev/null 2>&1 || { echo "zm không có trong PATH sau khi cài"; exit 1; }

mkdir -p "$SHARED" && chmod 700 "$SHARED"
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"zeromem-install","version":"1"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"zeromem_recall","arguments":{"query":"warm","top_k":1}}}' \
  | zm mcp --home "$SHARED" >/dev/null 2>&1 || echo "cảnh báo: lượt khởi động model trả lỗi, sẽ kiểm sha để xác định"
rm -f "$SHARED"/zeromem.db "$SHARED"/zeromem.db-*

SNAP="$SHARED/models/models--${MODEL_REPO//\//--}/snapshots/$MODEL_REV"
if verify_dir "$SNAP"; then
  echo "zeromem sẵn sàng: $(command -v zm), model tại $SNAP"
  exit 0
fi
mkdir -p "$SHARED/models/rejected"
mv "$SNAP" "$SHARED/models/rejected/$(date +%Y%m%d%H%M%S)" 2>/dev/null
echo "model bị từ chối: sha không khớp lock, đã chuyển vào models/rejected"
exit 1
```

Ghi chú: script không tự chạy `cargo install` trong test. Test chỉ gọi `--verify-only`.

- [ ] **Step 4: chạy lại — PASS**

Chạy: `bash harness/tests/zeromem-install-test.sh .`
Mong đợi: `zeromem-install-test: 3 pass, 0 fail` rồi `PASS`, rc 0.

- [ ] **Step 5: đăng ký test vào CI và commit**

Thêm step vào `.github/workflows/harness.yml`:

```yaml
      - name: zeromem-install — kiểm sha256 model theo lock
        run: bash harness/tests/zeromem-install-test.sh .
```

```bash
git add harness/scripts/zeromem-install.sh harness/tests/zeromem-install-test.sh harness/zeromem/zeromem-lock.json .github/workflows/harness.yml
git commit -m "feat(zeromem): cài và ghim zeromem, kiểm sha256 model theo lock"
```

### Task 2: bridge zeromem-bridge.py (recall, forget, stats, ingest)

**Thoả:** FR-003, FR-004, FR-005

**Files:**
- Tạo: `harness/scripts/zeromem-bridge.py`
- Tạo: `harness/tests/fixtures/fake-zm.py`
- Tạo: `harness/tests/zeromem-bridge-test.sh`
- Sửa: `.github/workflows/harness.yml` (thêm step chạy `zeromem-bridge-test.sh`)

**Interfaces:**
- Consumes: `harness/scripts/zeromem-install.sh` (Task 1) đặt zm trong PATH và model trong `$OVERSTACK_ZEROMEM_SHARED/models`.
- Produces (Python, module `zeromem-bridge.py`, import được qua `importlib`):
  - `store_home(root: str) -> pathlib.Path`: trả về thư mục store của project, `<base>/<khoá-16-ký-tự>`, với base là `OVERSTACK_ZEROMEM_HOME` hoặc `~/.overstack/zeromem`.
  - `recall(root: str, query: str, exclude_session: str | None = None, top_k: int = 3) -> list[dict]`: mỗi dict có `session_id`, `speaker`, `text`, `score`.
  - `forget_session(root: str, session_id: str) -> bool`.
  - `stats(root: str) -> dict`: các khoá `turns`, `sessions`, `embedder`, `embedder_is_fallback`.
  - `ingest(root: str, transcript: str, session_id: str) -> int`: trả về rc của `zm hook`, 0 khi không có việc để làm.
  - `status(root: str) -> dict`.
  - Lỗi nội bộ: `class BridgeError(RuntimeError)`.
- CLI: `zeromem-bridge.py <recall|forget-session|stats|ingest|status|backend> [--root R] [--query Q] [--exclude-session S] [--top-k N] [--session S] [--transcript T]`. `recall` in dòng văn bản `- [sid8] speaker: text`, không in JSON. Mọi lệnh trừ `status` thoát 0 khi lỗi và chỉ in cảnh báo ra stderr.

**Depends:** Task 1

**Verify:** `bash harness/tests/zeromem-bridge-test.sh .` cho `PASS`, rc 0.

- [ ] **Step 1: viết test fail**

Tạo `harness/tests/zeromem-bridge-test.sh`:

```bash
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
```

- [ ] **Step 2: chạy cho thấy fail**

Chạy: `bash harness/tests/zeromem-bridge-test.sh .`
Mong đợi: `zeromem-bridge-test: 0 pass, 5 fail` và rc 1, vì bridge và fake zm chưa tồn tại.

- [ ] **Step 3: viết fake zm**

Tạo `harness/tests/fixtures/fake-zm.py`:

```python
#!/usr/bin/env python3
# fake-zm — giả lập `zm mcp` / `zm hook` cho CI, trả JSON cố định theo đúng hình dạng của zeromem 0.3.0.
import json, sys

args = sys.argv[1:]
if args[:1] == ["hook"]:
    sys.exit(0)
if args[:1] != ["mcp"]:
    sys.exit(2)

EVIDENCE = [
    {"turn_id": 1, "session_id": "aaaaaaaa", "session_turn": 0, "speaker": "user", "text": "Carrie lo kho sach", "ts": 1, "score": 1.0},
    {"turn_id": 2, "session_id": "bbbbbbbb", "session_turn": 0, "speaker": "user", "text": "phien hien tai", "ts": 2, "score": 0.9},
]
out = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    if msg.get("method") == "initialize":
        out.append({"id": 1, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "zeromem", "version": "0.3.0"}}})
    elif msg.get("method") == "tools/call":
        p = msg["params"]
        a = p.get("arguments", {})
        if p["name"] == "zeromem_recall":
            ev = [e for e in EVIDENCE if e["session_id"] != a.get("exclude_session")]
            body = {"evidence": ev, "route": "Local"}
        elif p["name"] == "zeromem_stats":
            body = {"turns": 2, "sessions": 2, "entities": 0, "windows": 0, "episodes": 0, "embedder": "hash-v1-256", "embedder_is_fallback": True}
        elif p["name"] == "zeromem_forget_session":
            body = {"removed": 1}
        else:
            out.append({"id": 2, "error": {"message": "unknown tool"}})
            continue
        out.append({"id": 2, "result": {"content": [{"type": "text", "text": json.dumps(body)}], "isError": False}})
print("\n".join(json.dumps(o) for o in out))
```

Chạy `chmod +x harness/tests/fixtures/fake-zm.py`.

- [ ] **Step 4: viết bridge**

Tạo `harness/scripts/zeromem-bridge.py`:

```python
#!/usr/bin/env python3
"""zeromem-bridge — cầu nối duy nhất giữa hook Python và binary zm (backend memory zeromem).

Mọi thao tác đi qua `zm mcp` (JSON-RPC stdio) hoặc `zm hook`, không đọc trực tiếp zeromem.db.
Fail-open: lỗi zm, thiếu model, timeout đều in cảnh báo ra stderr và trả rỗng, thoát 0.
Ngoại lệ: `status` thoát 1 khi không gọi được zm, để người dùng thấy ngay.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overstack_paths import harness_dir  # noqa: E402

DEFAULT_BACKEND = "zeromem"
VALID_BACKENDS = ("zeromem", "mem-rank", "both")
MCP_TIMEOUT_S = 15


class BridgeError(RuntimeError):
    pass


def zm_bin():
    return os.environ.get("ZEROMEM_ZM") or shutil.which("zm")


def project_key(root: str) -> str:
    return hashlib.sha256(str(Path(root).resolve()).encode("utf-8")).hexdigest()[:16]


def shared_home() -> Path:
    return Path(os.environ.get("OVERSTACK_ZEROMEM_SHARED", str(Path.home() / ".overstack" / "zeromem" / "_shared")))


def store_home(root: str) -> Path:
    base = os.environ.get("OVERSTACK_ZEROMEM_HOME", str(Path.home() / ".overstack" / "zeromem"))
    return Path(base) / project_key(root)


def ensure_store(home: Path) -> Path:
    home.mkdir(parents=True, exist_ok=True)
    os.chmod(home, 0o700)
    link = home / "models"
    shared_models = shared_home() / "models"
    if shared_models.is_dir() and not link.exists() and not link.is_symlink():
        try:
            link.symlink_to(shared_models, target_is_directory=True)
        except OSError:
            pass  # Windows không có quyền symlink: zm tự tải model vào <home>/models, không chặn phiên
    return home


def _mcp_call(home: Path, name: str, arguments: dict, timeout: float = MCP_TIMEOUT_S) -> dict:
    zm = zm_bin()
    if not zm:
        raise BridgeError("không thấy binary zm (đặt ZEROMEM_ZM hoặc đưa zm vào PATH)")
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "zeromem-bridge", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": arguments}},
    ]
    stdin = "\n".join(json.dumps(r, ensure_ascii=False) for r in reqs) + "\n"
    try:
        p = subprocess.run([zm, "mcp", "--home", str(home)], input=stdin, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise BridgeError("zm mcp quá thời gian") from e
    except OSError as e:
        raise BridgeError(f"không chạy được zm: {e}") from e
    for line in p.stdout.splitlines():
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg.get("id") != 2:
            continue
        if "error" in msg:
            raise BridgeError(msg["error"].get("message", "zm báo lỗi"))
        res = msg.get("result", {})
        text = res["content"][0]["text"]
        if res.get("isError"):
            raise BridgeError(text)
        return json.loads(text)
    raise BridgeError(f"zm mcp không trả lời (rc={p.returncode}): {p.stderr.strip()[-200:]}")


def recall(root: str, query: str, exclude_session=None, top_k: int = 3) -> list:
    home = ensure_store(store_home(root))
    args = {"query": query, "top_k": top_k}
    if exclude_session:
        args["exclude_session"] = exclude_session
    res = _mcp_call(home, "zeromem_recall", args)
    return [e for e in res.get("evidence", []) if e.get("text")]


def forget_session(root: str, session_id: str) -> bool:
    _mcp_call(ensure_store(store_home(root)), "zeromem_forget_session", {"session_id": session_id})
    return True


def stats(root: str) -> dict:
    return _mcp_call(ensure_store(store_home(root)), "zeromem_stats", {})


def ingest(root: str, transcript: str, session_id: str) -> int:
    """Spool turn mới của transcript vào store project qua `zm hook`. Trả rc của zm hook."""
    zm = zm_bin()
    if not zm or not transcript or memory_backend(root) not in ("zeromem", "both"):
        return 0
    home = ensure_store(store_home(root))
    payload = json.dumps({"session_id": session_id, "transcript_path": transcript})
    try:
        p = subprocess.run([zm, "hook"], input=payload, capture_output=True, text=True,
                           timeout=MCP_TIMEOUT_S, env={**os.environ, "ZEROMEM_HOME": str(home)})
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"zeromem-bridge: ingest lỗi: {e}", file=sys.stderr)
        return 0
    if p.returncode != 0:
        print(f"zeromem-bridge: zm hook rc={p.returncode}: {p.stderr.strip()[-200:]}", file=sys.stderr)
    return p.returncode


def memory_backend(root: str) -> str:
    """Đọc `memory.backend` từ harness/mem-rank.config.yaml qua harness_dir. Mặc định zeromem.

    Thiếu binary zm → mem-rank (không mất ghi). Giá trị lạ → `invalid:<giá trị>`, hook sẽ báo và giữ mem-rank.
    """
    cfg = harness_dir(root) / "mem-rank.config.yaml"
    try:
        text = cfg.read_text(encoding="utf-8")
    except OSError:
        text = ""
    m = re.search(r"^memory:\s*\n(?:[ \t]+.*\n)*?[ \t]+backend:\s*([A-Za-z-]+)", text, re.M)
    val = m.group(1) if m else DEFAULT_BACKEND
    if val not in VALID_BACKENDS:
        return f"invalid:{val}"
    if val == "zeromem" and not zm_bin():
        print("zeromem-bridge: backend=zeromem nhưng không có zm — tạm dùng mem-rank", file=sys.stderr)
        return "mem-rank"
    return val


def status(root: str) -> dict:
    st = stats(root)
    return {"zm": zm_bin(), "store": str(store_home(root)), "backend": memory_backend(root),
            "embedder": st.get("embedder"), "embedder_is_fallback": st.get("embedder_is_fallback"),
            "turns": st.get("turns")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="zeromem-bridge")
    ap.add_argument("cmd", choices=["recall", "forget-session", "stats", "ingest", "status", "backend"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--query", default="")
    ap.add_argument("--exclude-session", default=None)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--session", default="")
    ap.add_argument("--transcript", default="")
    a = ap.parse_args(argv)
    root = str(Path(a.root).resolve())
    if a.cmd == "backend":
        print(memory_backend(root))
        return 0
    if a.cmd == "ingest":
        ingest(root, a.transcript, a.session)
        return 0
    try:
        if a.cmd == "recall":
            for e in recall(root, a.query, a.exclude_session, a.top_k):
                print(f"- [{str(e.get('session_id', ''))[:8]}] {e.get('speaker', '')}: {str(e.get('text', ''))[:120]}")
            return 0
        if a.cmd == "forget-session":
            forget_session(root, a.session)
            return 0
        out = status(root) if a.cmd == "status" else stats(root)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    except BridgeError as e:
        print(f"zeromem-bridge: {e}", file=sys.stderr)
        return 1 if a.cmd == "status" else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: chạy lại — PASS**

Chạy: `bash harness/tests/zeromem-bridge-test.sh .`
Mong đợi: `zeromem-bridge-test: 5 pass, 0 fail` rồi `PASS`, rc 0.

- [ ] **Step 6: đăng ký CI và commit**

Thêm step vào `.github/workflows/harness.yml`:

```yaml
      - name: zeromem-bridge — recall loại phiên hiện tại, fail-open khi thiếu zm (fake zm)
        run: bash harness/tests/zeromem-bridge-test.sh .
```

```bash
git add harness/scripts/zeromem-bridge.py harness/tests/fixtures/fake-zm.py harness/tests/zeromem-bridge-test.sh .github/workflows/harness.yml
git commit -m "feat(zeromem): bridge recall/forget/stats/ingest qua zm mcp và zm hook"
```

### Task 3: chọn backend bằng config

**Thoả:** FR-001, FR-002

**Files:**
- Sửa: `harness/mem-rank.config.yaml` (thêm block `memory:` ở cuối file)
- Sửa: `harness/tests/zeromem-bridge-test.sh` (thêm nhóm test backend)
- Sửa: `llmwiki/.claude/hooks/hooklib.py` (thêm `memory_backend`, dùng `subprocess` gọi bridge)

**Interfaces:**
- Consumes: `memory_backend(root: str) -> str` từ `zeromem-bridge.py` (Task 2) và giá trị `memory.backend` trong config.
- Produces: `hooklib.memory_backend(root: str) -> str`, trả về một trong `zeromem`, `mem-rank`, `both`. Giá trị lạ được trả về `mem-rank` sau khi in cảnh báo ra stderr, theo đúng cổng ngược.

**Depends:** Task 2

**Verify:** `bash harness/tests/zeromem-bridge-test.sh .` cho `PASS`, rc 0, và `python3 harness/scripts/mem-rank.py --self-test` in `mem-rank self-test: PASS`.

- [ ] **Step 1: viết test fail cho backend**

Thêm vào cuối `harness/tests/zeromem-bridge-test.sh`, trước dòng `echo "zeromem-bridge-test: ..."`:

```bash
mkcfg(){ mkdir -p "$TMP/cfg/harness"; printf '%s' "$1" > "$TMP/cfg/harness/mem-rank.config.yaml"; }
mkcfg 'verified: false
'
[ "$(python3 "$BRIDGE" backend --root "$TMP/cfg")" = "zeromem" ] && ok "thiếu khoá memory → zeromem" || bad "mặc định" "$(python3 "$BRIDGE" backend --root "$TMP/cfg")"
mkcfg 'verified: false
memory:
  backend: mem-rank
'
[ "$(python3 "$BRIDGE" backend --root "$TMP/cfg")" = "mem-rank" ] && ok "backend mem-rank được đọc" || bad "mem-rank" "$(python3 "$BRIDGE" backend --root "$TMP/cfg")"
mkcfg 'memory:
  backend: both
'
[ "$(python3 "$BRIDGE" backend --root "$TMP/cfg")" = "both" ] && ok "backend both được đọc" || bad "both" "$(python3 "$BRIDGE" backend --root "$TMP/cfg")"
mkcfg 'memory:
  backend: foo
'
[ "$(python3 "$BRIDGE" backend --root "$TMP/cfg")" = "invalid:foo" ] && ok "giá trị lạ → invalid:foo, không đoán" || bad "invalid" "$(python3 "$BRIDGE" backend --root "$TMP/cfg")"
mkcfg 'memory:
  backend: zeromem
'
[ "$(ZEROMEM_ZM=/does/not/exist PATH=/usr/bin:/bin python3 "$BRIDGE" backend --root "$TMP/cfg" 2>/dev/null)" = "mem-rank" ] && ok "zeromem không có zm → rơi về mem-rank" || bad "fallback zm" "không khớp"
```

- [ ] **Step 2: chạy cho thấy fail**

Chạy: `bash harness/tests/zeromem-bridge-test.sh .`
Mong đợi: 5 ca cũ vẫn pass. 5 ca mới fail, vì `harness/mem-rank.config.yaml` chưa có khoá `memory`, và trong ca cuối `ZEROMEM_ZM` trỏ tới file không tồn tại nên `zm_bin()` vẫn trả về đường dẫn đó. Ghi chú: ca cuối cần sửa `zm_bin()` để kiểm `os.path.isfile` trước khi trả. Việc này làm ở Step 3.

- [ ] **Step 3: sửa bridge và config**

Trong `harness/scripts/zeromem-bridge.py`, thay hàm `zm_bin`:

```python
def zm_bin():
    env = os.environ.get("ZEROMEM_ZM")
    if env:
        return env if os.path.isfile(env) else None
    return shutil.which("zm")
```

Thêm vào cuối `harness/mem-rank.config.yaml`:

```yaml

# Backend memory của project: zeromem (mặc định) | mem-rank | both.
# Đọc bởi harness/scripts/zeromem-bridge.py (memory_backend). Thiếu khoá → zeromem.
memory:
  backend: zeromem
```

Trong `llmwiki/.claude/hooks/hooklib.py`, thêm hàm (đặt sau `resolve_tool`):

```python
def memory_backend(root: str) -> str:
    """Backend memory của project: zeromem | mem-rank | both. Fail-open về mem-rank khi không đọc được."""
    zb = resolve_tool(root, "harness/scripts/zeromem-bridge.py")
    if not zb:
        return "mem-rank"
    try:
        out = subprocess.run([sys.executable, zb, "backend", "--root", root], cwd=root,
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return "mem-rank"
    if out.startswith("invalid:"):
        sys.stderr.write(f"memory.backend không hợp lệ ({out[8:]}) — giữ mem-rank\n")
        return "mem-rank"
    return out if out in ("zeromem", "mem-rank", "both") else "mem-rank"
```

Kiểm `hooklib.py` đã import `subprocess` và `sys`. Nếu chưa, thêm vào khối import đầu file.

- [ ] **Step 4: chạy lại — PASS, và mem-rank không đổi**

Chạy: `bash harness/tests/zeromem-bridge-test.sh .`
Mong đợi: `zeromem-bridge-test: 10 pass, 0 fail` rồi `PASS`, rc 0.

Chạy: `python3 harness/scripts/mem-rank.py --self-test`
Mong đợi: dòng cuối `mem-rank self-test: PASS`.

- [ ] **Step 5: commit**

```bash
git add harness/mem-rank.config.yaml harness/scripts/zeromem-bridge.py harness/tests/zeromem-bridge-test.sh llmwiki/.claude/hooks/hooklib.py
git commit -m "feat(zeromem): khoá memory.backend, mặc định zeromem, rơi về mem-rank khi thiếu zm"
```

### Task 4: nối ghi ở Stop và SessionEnd, đọc ở SessionStart

**Thoả:** FR-003, FR-004

**Files:**
- Sửa: `llmwiki/.claude/hooks/stop.py` — thêm `zeromem_write` trước dòng `secondary_memory(root, ...)` (hiện ở khoảng dòng 431); gate khối `mr episode` trong `secondary_memory` (hiện ở khoảng dòng 214–226) bằng `memory_backend`.
- Sửa: `llmwiki/.claude/hooks/session_start.py` — thêm `_zeromem_recall`; ở đầu hàm `recall` (dòng 223), gọi `_zeromem_recall` và `return` sớm khi backend là `zeromem`.
- Sửa: `llmwiki/.claude/hooks/session_end.py` — gọi `zeromem_write` trong `main()` sau `audit(payload, "SessionEnd")`.
- Tạo: `harness/tests/zeromem-hooks-test.sh`
- Sửa: `.github/workflows/harness.yml` (thêm step)

**Interfaces:**
- Consumes: `hooklib.memory_backend(root)` (Task 3), `zeromem-bridge.py ingest|recall` (Task 2).
- Produces: hàm `zeromem_write(root: str, session: str, tp: str) -> None` trong `stop.py`, cùng một bản trong `session_end.py` (sao chép một dòng gọi, không import chéo). `_zeromem_recall(root: Path, sid: str, backend: str) -> None` trong `session_start.py`.

**Depends:** Task 2, Task 3

**Verify:** `bash harness/tests/zeromem-hooks-test.sh .` cho `PASS`, rc 0.

- [ ] **Step 1: viết test fail**

Tạo `harness/tests/zeromem-hooks-test.sh`:

```bash
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

PROJ="$TMP/proj"; mkdir -p "$PROJ/harness" "$PROJ/llmwiki"
git -C "$PROJ" init -q && git -C "$PROJ" -c user.email=t@t -c user.name=t commit -q --allow-empty -m "feat: xuất csv"
cp harness/mem-rank.config.yaml "$PROJ/harness/" && cp -r harness/scripts "$PROJ/harness/" && mkdir -p "$PROJ/harness/tests" && cp -r harness/tests/fixtures "$PROJ/harness/tests/"

out=$(echo '{"session_id":"bbbbbbbb","cwd":"'"$PROJ"'"}' | CLAUDE_PROJECT_DIR="$PROJ" python3 llmwiki/.claude/hooks/session_start.py 2>/dev/null)
echo "$out" | grep -q 'Trí nhớ zeromem' && echo "$out" | grep -q 'aaaaaaaa' && ! echo "$out" | grep -q 'bbbbbbbb' \
  && ok "SessionStart in recall zeromem, loại phiên hiện tại" || bad "SessionStart recall" "$(echo "$out" | head -5)"

sed -i.bak 's/backend: zeromem/backend: mem-rank/' "$PROJ/harness/mem-rank.config.yaml"
out=$(echo '{"session_id":"bbbbbbbb","cwd":"'"$PROJ"'"}' | CLAUDE_PROJECT_DIR="$PROJ" python3 llmwiki/.claude/hooks/session_start.py 2>/dev/null)
echo "$out" | grep -q 'Trí nhớ zeromem' && bad "backend mem-rank" "vẫn in recall zeromem" || ok "backend mem-rank không in recall zeromem"

echo "zeromem-hooks-test: $pass pass, $fail fail"
[ $fail -eq 0 ] && echo "PASS" || exit 1
```

- [ ] **Step 2: chạy cho thấy fail**

Chạy: `bash harness/tests/zeromem-hooks-test.sh .`
Mong đợi: ca cú pháp pass. Ca SessionStart fail, vì `session_start.py` chưa có nhánh zeromem. Ca `mem-rank` có thể pass vì không có dòng nào được in.

- [ ] **Step 3: sửa session_start.py**

Thêm vào `llmwiki/.claude/hooks/session_start.py`, ngay trên `def recall`:

```python
def _zeromem_recall(root: Path, sid: str, backend: str) -> None:
    """Đầu phiên: recall zeromem theo subject commit gần nhất, tối đa 3 dòng, loại phiên hiện tại.

    Fail-open: thiếu bridge, thiếu zm, timeout đều im lặng. Chạy khi backend là zeromem hoặc both.
    """
    if backend not in ("zeromem", "both"):
        return
    zb = resolve_tool(str(root), "harness/scripts/zeromem-bridge.py")
    if not zb:
        return
    try:
        subj = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=str(root),
                              capture_output=True, text=True, timeout=5).stdout.strip()
        if not subj:
            return
        out = subprocess.run([sys.executable, zb, "recall", "--root", str(root), "--query", subj,
                              "--exclude-session", sid, "--top-k", "3"],
                             cwd=str(root), capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return
    if out:
        print("Trí nhớ zeromem (liên quan việc gần nhất):")
        print(out)
```

Sửa đầu hàm `recall`, ngay sau dòng docstring:

```python
    backend = memory_backend(str(root))
    _zeromem_recall(root, sid, backend)
    if backend == "zeromem":
        return
```

Thêm `memory_backend` vào dòng import từ `hooklib` ở đầu file. Kiểm tra `subprocess`, `sys`, `resolve_tool` đã được import.

- [ ] **Step 4: sửa stop.py và session_end.py**

Trong `llmwiki/.claude/hooks/stop.py`, thêm trước `def secondary_memory`:

```python
def zeromem_write(root: str, session: str, tp: str) -> None:
    """Ghi turn của phiên vào store zeromem của project, qua bridge → zm hook. Fail-open, theo ngân sách Stop."""
    zb = resolve_tool(root, "harness/scripts/zeromem-bridge.py")
    if not zb or not tp:
        return
    try:
        _run([sys.executable, zb, "ingest", "--root", root, "--session", session, "--transcript", tp],
             cwd=root, capture_output=True, timeout=12)
    except Exception:
        pass
```

Trong `secondary_memory`, đổi dòng `if mr:` (khối `mr episode`) thành:

```python
    if mr and memory_backend(root) in ("mem-rank", "both"):
```

Trong `main()` của `stop.py`, đặt ngay trước dòng `secondary_memory(root, (payload.get("session_id") or ""))`:

```python
    zeromem_write(root, (payload.get("session_id") or ""), tp or "")
```

Biến `tp` đã được gán ở đầu `main()` (dòng `tp = payload.get("transcript_path")`). Thêm `memory_backend` vào import từ `hooklib` ở đầu `stop.py`.

Trong `llmwiki/.claude/hooks/session_end.py`, thêm vào đầu file cùng hàm `zeromem_write` (bản sao, không import chéo giữa hooks), và trong `main()` ngay sau `audit(payload, "SessionEnd")`:

```python
    zeromem_write(str(root_of_project), (payload.get("session_id") or ""), payload.get("transcript_path") or "")
```

Dùng đúng biến chứa đường dẫn project trong `session_end.py`. Nếu hàm `main()` chưa có biến đó, lấy bằng `project_dir(payload)` từ `hooklib`.

- [ ] **Step 5: chạy lại — PASS**

Chạy: `bash harness/tests/zeromem-hooks-test.sh .`
Mong đợi: `zeromem-hooks-test: 5 pass, 0 fail` rồi `PASS`, rc 0.

- [ ] **Step 6: đăng ký CI và commit**

Thêm step vào `.github/workflows/harness.yml`:

```yaml
      - name: zeromem-hooks — SessionStart recall zeromem, mem-rank không đổi (fake zm)
        run: bash harness/tests/zeromem-hooks-test.sh .
```

```bash
git add llmwiki/.claude/hooks/stop.py llmwiki/.claude/hooks/session_start.py llmwiki/.claude/hooks/session_end.py llmwiki/.claude/hooks/hooklib.py harness/tests/zeromem-hooks-test.sh .github/workflows/harness.yml
git commit -m "feat(zeromem): ghi turn ở Stop và SessionEnd, recall ở SessionStart"
```

### Task 5: memory-map đọc zeromem và eval golden

**Thoả:** FR-006

**Files:**
- Sửa: `fdk/tools/memory-map.py` — thêm nhánh `--source zeromem` ở `main()` (dòng 144) và hàm `_zeromem_sessions`.
- Tạo: `harness/tests/zeromem-memory-map-test.sh`
- Tạo: `harness/evals/zeromem-cross-session.json`
- Tạo: `harness/tests/zeromem-eval-test.sh`
- Sửa: `.github/workflows/harness.yml` (thêm hai step)

**Interfaces:**
- Consumes: `store_home(root: str) -> Path` từ `harness/scripts/zeromem-bridge.py` (Task 2), nạp qua hàm `_load` có sẵn trong `memory-map.py`. Schema của bảng `turns` trong `zeromem.db`: `id, session_id, session_turn, speaker, text, ts` (đã kiểm trong `crates/zeromem/src/store.rs` của zeromem `eda212665`).
- Produces: `_zeromem_sessions(root) -> list[tuple[str, int, int, int]]`, mỗi tuple là `(session_id, ts_đầu, số_turn, ts_cuối)`, sắp theo `ts_đầu`. Hàm trả về `None` khi chưa có `zeromem.db`. Lệnh `python3 fdk/tools/memory-map.py --source zeromem` ghi `llmwiki/html/memory-map-zeromem.html`, không ghi đè `memory-map.html`.

**Depends:** Task 2

**Verify:** `bash harness/tests/zeromem-memory-map-test.sh .` và `bash harness/tests/zeromem-eval-test.sh .` cho `PASS`, rc 0.

- [ ] **Step 1: viết test fail cho memory-map**

Tạo `harness/tests/zeromem-memory-map-test.sh`:

```bash
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

python3 fdk/tools/memory-map.py --source zeromem > "$TMP/out.log" 2>&1
[ $? -eq 0 ] && grep -q 'memory-map-zeromem.html' "$TMP/out.log" && ok "--source zeromem chạy và báo đúng file đích" || bad "chạy --source zeromem" "$(cat "$TMP/out.log")"

python3 - "$STORE/zeromem.db" <<'PY' && ok "DB không bị ghi (đọc ở chế độ ro)" || bad "DB bị ghi" "số turn đổi"
import sqlite3, sys
con = sqlite3.connect(sys.argv[1]); n = con.execute("SELECT COUNT(*) FROM turns").fetchone()[0]; con.close()
sys.exit(0 if n == 3 else 1)
PY

python3 - "$STORE/zeromem.db" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1]); con.execute("ALTER TABLE turns RENAME COLUMN text TO body"); con.commit(); con.close()
PY
python3 fdk/tools/memory-map.py --source zeromem > "$TMP/schema.log" 2>&1
grep -q 'schema zeromem lạ' "$TMP/schema.log" && ok "schema lạ → báo lỗi, không vẽ bừa" || bad "schema lạ" "$(cat "$TMP/schema.log")"

echo "zeromem-memory-map-test: $pass pass, $fail fail"
[ $fail -eq 0 ] && echo "PASS" || exit 1
```

Ghi chú: test dùng `fdk/tools/memory-map.py` và ghi `llmwiki/html/memory-map-zeromem.html` trong repo. Test chạy trên bản sao của repo để không làm bẩn cây làm việc. Trước khi chạy, copy repo vào `$TMP` hoặc chạy trong worktree tạm.

- [ ] **Step 2: chạy cho thấy fail**

Chạy: `bash harness/tests/zeromem-memory-map-test.sh .`
Mong đợi: 0 pass, 3 fail, vì `memory-map.py` chưa có `--source zeromem`.

- [ ] **Step 3: viết nhánh zeromem trong memory-map.py**

Trong `fdk/tools/memory-map.py`, thêm `import sqlite3` vào khối import đầu file. Thêm hàm sau `_session_parents`:

```python
def _zeromem_sessions(root):
    """Phiên và số turn từ zeromem.db, chỉ đọc. None khi chưa có store. Lỗi schema → RuntimeError."""
    zb = _load("harness/scripts/zeromem-bridge.py", "zb")
    db = zb.store_home(str(root)) / "zeromem.db"
    if not db.is_file():
        return None
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(turns)")}
        need = {"session_id", "session_turn", "speaker", "text", "ts"}
        if not need <= cols:
            raise RuntimeError(f"schema zeromem lạ: thiếu {sorted(need - cols)}")
        return con.execute(
            "SELECT session_id, MIN(ts), COUNT(*), MAX(ts) FROM turns GROUP BY session_id ORDER BY MIN(ts)"
        ).fetchall()
    finally:
        con.close()


def _main_zeromem():
    rows = _zeromem_sessions(ROOT)
    if rows is None:
        print("memory-map --source zeromem: chưa có zeromem.db của project này")
        return 0
    nodes, edges, prev = [], [], None
    for sid, ts0, n, ts1 in rows:
        node_id = f"s:{sid[:8]}"
        nodes.append({"id": node_id, "type": "session", "title": f"{n} turn · {sid[:8]}",
                      "wiki": "memory", "label": sid[:8]})
        if prev:
            edges.append({"from": prev, "rel": "continues", "to": node_id, "kind": "to"})
        prev = node_id
    out = ROOT / "llmwiki" / "html" / "memory-map-zeromem.html"
    out.write_text(_ovs_font(WG.build_html("memory", str(out), nodes, edges, [], {})), encoding="utf-8")
    print(f"✓ wrote {out.relative_to(ROOT)} — {len(nodes)} phiên (zeromem, chỉ đọc)")
    return 0
```

Trong `main()`, ngay đầu hàm trước dòng `nodes, edges = build()`:

```python
    if "--source" in sys.argv and sys.argv[sys.argv.index("--source") + 1:][:1] == ["zeromem"]:
        return _main_zeromem()
```

Mã này dùng `_load`, `WG`, `_ovs_font`, `ROOT` đã có trong `memory-map.py`. Trước khi sửa, đọc lại dòng định nghĩa `_load` để xác nhận chữ ký.

- [ ] **Step 4: chạy lại — PASS**

Chạy: `bash harness/tests/zeromem-memory-map-test.sh .`
Mong đợi: `zeromem-memory-map-test: 3 pass, 0 fail` rồi `PASS`, rc 0.

Chạy: `python3 fdk/tools/memory-map.py` (không có `--source`)
Mong đợi: hành vi cũ không đổi, in dòng `✓ wrote llmwiki/html/memory-map.html`, hoặc `chưa có dữ liệu` nếu chưa có scratch-log.

- [ ] **Step 5: viết golden hai phiên và test hit@k**

Tạo `harness/evals/zeromem-cross-session.json`:

```json
{
  "schema": 1,
  "note": "Golden cross-session: câu hỏi thuộc phiên A, truy vấn từ phiên B. Hit@k đo trên zeromem thật (ZEROMEM_E2E=1); CI chỉ kiểm harness bằng fake zm.",
  "sessions": {
    "A": ["Carrie lo sach ban sci-fi tu Ingram", "Dung Books mo o Jersey City"],
    "B": ["sua hook stop cho dung budget"]
  },
  "cases": [
    {"id": "xc-1", "query": "ai lo mang sach sci-fi", "expect_session": "A", "k": 3},
    {"id": "xc-2", "query": "cua hang Dung Books mo o dau", "expect_session": "A", "k": 3}
  ]
}
```

Tạo `harness/tests/zeromem-eval-test.sh`:

```bash
#!/usr/bin/env bash
# zeromem-eval-test — hit@k cross-session. ZEROMEM_E2E=1 dùng zm thật; mặc định dùng fake zm (chỉ kiểm harness).
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
ROOT="$(pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export OVERSTACK_ZEROMEM_HOME="$TMP/stores"
if [ "${ZEROMEM_E2E:-0}" = "1" ]; then
  command -v zm >/dev/null 2>&1 || { echo "ZEROMEM_E2E=1 nhưng không có zm — không đo được"; exit 2; }
  MODE=real
else
  export ZEROMEM_ZM="$ROOT/harness/tests/fixtures/fake-zm.py"; MODE=fake
fi
pass=0; fail=0
ok(){ printf '  \033[1;32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad(){ printf '  \033[1;31m✗\033[0m %s — %s\n' "$1" "$2"; fail=$((fail+1)); }

python3 - "$ROOT" "$MODE" <<'PY' > "$TMP/hits.txt"
import json, subprocess, sys
root, mode = sys.argv[1], sys.argv[2]
g = json.load(open(f"{root}/harness/evals/zeromem-cross-session.json", encoding="utf-8"))
hit = 0
for case in g["cases"]:
    out = subprocess.run([sys.executable, f"{root}/harness/scripts/zeromem-bridge.py", "recall",
                          "--root", root, "--query", case["query"], "--exclude-session", "zzzzzzzz",
                          "--top-k", str(case["k"])], capture_output=True, text=True).stdout
    ok = bool(out.strip()) if mode == "fake" else out.strip() != ""
    hit += int(ok)
    print(f"{case['id']} {'HIT' if ok else 'MISS'}")
print(f"HITRATE {hit}/{len(g['cases'])}")
PY
cat "$TMP/hits.txt"
rate=$(grep HITRATE "$TMP/hits.txt" | awk '{print $2}')
[ "$MODE" = "fake" ] && ok "harness eval chạy với fake zm ($rate)" || ok "eval zeromem thật ($rate)"
grep -q 'MISS' "$TMP/hits.txt" && [ "$MODE" = "real" ] && bad "hit@k thật" "có ca MISS" || true
echo "zeromem-eval-test: $pass pass, $fail fail ($MODE)"
[ $fail -eq 0 ] && echo "PASS" || exit 1
```

Ghi chú về ngữ nghĩa: chế độ `fake` chỉ kiểm rằng harness chạy và in đúng định dạng. Kết quả chất lượng chỉ có ở chế độ `real`. CI chạy `fake`. Không được coi `fake` là đạt chất lượng.

- [ ] **Step 6: chạy eval và commit**

Chạy: `bash harness/tests/zeromem-eval-test.sh .`
Mong đợi: `HITRATE 2/2` ở chế độ fake, rồi `PASS`, rc 0.

Chạy thật (máy có zm và model): `ZEROMEM_E2E=1 bash harness/tests/zeromem-eval-test.sh .`
Mong đợi: ghi số hit@k thật vào log. Không tự suy ra kết quả.

Thêm hai step vào `.github/workflows/harness.yml`:

```yaml
      - name: zeromem-memory-map — --source zeromem chỉ đọc, schema lạ báo lỗi
        run: bash harness/tests/zeromem-memory-map-test.sh .
      - name: zeromem-eval — harness hit@k cross-session (fake zm)
        run: bash harness/tests/zeromem-eval-test.sh .
```

```bash
git add fdk/tools/memory-map.py harness/tests/zeromem-memory-map-test.sh harness/evals/zeromem-cross-session.json harness/tests/zeromem-eval-test.sh .github/workflows/harness.yml
git commit -m "feat(zeromem): memory-map --source zeromem chỉ đọc và eval hit@k cross-session"
```

## Global self-review

1. **Phủ SPEC.** FR-001 → Task 3. FR-002 → Task 3 (verify bằng `mem-rank --self-test`), và Task 4 (gate mem-rank episode). FR-003 → Task 2 (ingest) và Task 4 (Stop/SessionEnd). FR-004 → Task 2 (recall loại phiên) và Task 4 (SessionStart). FR-005 → Task 2 (forget-session). FR-006 → Task 5. FR-007 → Task 1. Không FR nào bị bỏ rơi.
2. **Quét placeholder.** Đã rà các từ bị cấm. Mọi bước đổi code đều có code đầy đủ. Mọi hàm được nhắc tới đều được định nghĩa trong một task.
3. **Nhất quán tên.** Tên `memory_backend` dùng ở bridge (Task 3), `hooklib` (Task 3), `stop.py` và `session_start.py` (Task 4). Tên `store_home` dùng ở bridge (Task 2), memory-map (Task 5) và test (Task 5). Tên `zeromem_write` và `_zeromem_recall` dùng nhất quán giữa định nghĩa và chỗ gọi. Khoá config là `memory.backend`, biến môi trường là `ZEROMEM_ZM`, `OVERSTACK_ZEROMEM_HOME`, `OVERSTACK_ZEROMEM_SHARED`.

## Ghi chú cho người thi hành

- Mỗi task có một commit riêng. Không gộp task.
- Chạy test của task trước trước khi làm task sau. Task 3 sửa cùng file bridge với Task 2, nên không chạy song song.
- Test dùng fake zm. Muốn kết quả chất lượng thật, chạy `ZEROMEM_E2E=1` trên máy đã có zm và model, và ghi số đo vào log.
- Không tự cài bản fork archify `macos`. Không đẩy PR của task nào mà chưa được duyệt riêng.

## Lịch sử sửa

- **PLAN v2 (03/10/2026).** Worker T2 dry-run và dừng đúng quy trình, báo hai lỗi thật của PLAN v1:
  1. Session id trong fixture và test dài 9 ký tự (`aaaaaaaa1`), còn bridge in `sid[:8]`, nên test `grep` không bao giờ khớp. Sửa thành 8 ký tự (`aaaaaaaa`, `bbbbbbbb`) ở T2, T4 và T5. Lỗi này cũng có ở T4.
  2. `ensure_store` gọi `symlink_to` ngoài `try`, Windows không có quyền symlink nên vi phạm fail-open. Bọc trong `try` ở T2.
  Các task T2–T5 của run cũ được thay bằng run v2 với spec lấy lại từ PLAN này. T1 không đổi.
