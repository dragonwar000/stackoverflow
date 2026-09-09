#!/usr/bin/env python3
"""overstack-budget-statusline — status bar cho một phiên làm việc.

Hai dòng:
  1. badge nối chuỗi (giữ statusLine đang có) · model · thanh cửa sổ ngữ cảnh SỐNG
  2. % bốn trần overstack đọc từ harness/token-budget.config.yaml + harness/metrics/tokens.jsonl

Vì sao script này tồn tại thay vì một field trong plugin.json: Claude Code KHÔNG cho plugin
khai `statusLine` (chỉ `subagentStatusLine`). Nên plugin mang script, còn `--install` ghi khoá
`statusLine` vào settings.json trỏ về đây.

Vì sao đọc CẢ hai nguồn: stdin cho cửa sổ ngữ cảnh sống (cập nhật mọi lượt, là thứ thực sự
cắt phiên), còn ledger cho các trần overstack (chỉ đổi ở hook Stop). Trộn hai nguồn vào một
dòng thì người xem không phải nhớ số nào lấy ở đâu.

Fail-open tuyệt đối: mọi lỗi → in được gì in nấy, exit 0. Status bar không bao giờ được làm
hỏng phiên; một dòng thiếu còn hơn một terminal gãy.

Usage:
  statusline.py                 đọc JSON trên stdin, in status bar (chế độ Claude Code gọi)
  statusline.py --install       ghi statusLine vào ~/.claude/settings.json (trỏ về file này)
  statusline.py --uninstall     gỡ statusLine đã cài (khôi phục giá trị cũ nếu có)
  statusline.py --status        cho biết đang wire vào đâu, có lệch đường dẫn không
  statusline.py --self-test     kiểm bất biến nội bộ, tất định, không cần Claude Code
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

# ── hằng số hiển thị ────────────────────────────────────────────────────────────────────
BAR_CELLS = 10
FILL, EMPTY = "▓", "░"
G, Y, R, DIM, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"
WARN_AT, CRIT_AT = 0.60, 0.85          # CRIT trùng auto_handover.threshold mặc định

# Bốn trần muốn thấy trên thanh: (nhãn, khoá cộng dồn trong ledger, khoá trần trong config)
CAPS = [
    ("tok",   "tokens", "per_session_tokens"),
    ("$",     "usd",    "per_task_usd"),
    ("calls", "calls",  "per_session_model_calls"),
    ("tools", "tool_calls", "per_session_tool_calls"),
]
SETTINGS_KEY = "statusLine"
BACKUP_KEY = "_overstackBudgetStatuslinePrev"   # nơi cất statusLine cũ để --uninstall trả lại


# ── đọc config (không phụ thuộc PyYAML) ─────────────────────────────────────────────────
# Cố ý KHÔNG `import yaml`: script chạy mỗi lượt, thêm một import nặng vào đường nóng để đọc
# 8 con số là đổi độ trễ lấy sự tiện. Chỉ cần 3 khối phẳng nên bộ đọc tối giản là đủ.
def _strip_comment(v: str) -> str:
    return v.split("#", 1)[0].strip()


def parse_config(text: str) -> dict:
    """Đọc budgets / auto_handover / rates / mode từ token-budget.config.yaml."""
    cfg = {"budgets": {}, "auto_handover": {}, "rates": {}, "mode": None, "verified": None}
    section = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0:
            key = line.split(":", 1)[0].strip()
            if key in ("budgets", "auto_handover", "rates"):
                section = key
                continue
            section = None
            if key in ("mode", "verified") and ":" in line:
                val = _strip_comment(line.split(":", 1)[1])
                cfg[key] = {"true": True, "false": False}.get(val.lower(), val)
            continue
        if section is None or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), _strip_comment(v)
        if section == "rates":
            nums = dict(re.findall(r"(input|output)\s*:\s*([0-9.]+)", v))
            if nums:
                cfg["rates"][k] = {a: float(b) for a, b in nums.items()}
            continue
        if v.startswith("[") and v.endswith("]"):
            cfg[section][k] = [x.strip() for x in v[1:-1].split(",") if x.strip()]
        elif v.lower() in ("true", "false"):
            cfg[section][k] = v.lower() == "true"
        else:
            try:
                cfg[section][k] = float(v) if "." in v else int(v)
            except ValueError:
                cfg[section][k] = v
    return cfg


# ── tìm gốc overstack ───────────────────────────────────────────────────────────────────
# Chấp CẢ hai layout: `harness/` (repo framework) và `.harness/` (dự án đích sau bản dot-layout).
# Bỏ một trong hai thì status bar câm ở đúng nửa số dự án mà không báo gì.
LAYOUTS = ("harness", ".harness")


def find_root(start: str):
    try:
        p = Path(start).expanduser().resolve()
    except Exception:
        return None, None
    for d in [p, *p.parents]:
        for lay in LAYOUTS:
            if (d / lay / "token-budget.config.yaml").is_file():
                return d, lay
    return None, None


# ── cộng dồn ledger ─────────────────────────────────────────────────────────────────────
# Cùng ngữ nghĩa với token-budget.py:totals() — mọi row CỘNG DỒN, và $ luôn TÍNH LẠI từ
# (in, out, model, rates) chứ không đọc field `usd` của row. Lệch cách cộng ở đây thì thanh
# nói một đằng, `token-budget.py --report` nói một nẻo, và không ai tin cái nào nữa.
def cost_usd(in_tok: int, out_tok: int, model, rates: dict) -> float:
    r = rates.get(model) or rates.get("default") or {}
    return in_tok / 1000.0 * float(r.get("input", 0)) + out_tok / 1000.0 * float(r.get("output", 0))


def session_totals(ledger: Path, session: str, rates: dict) -> dict:
    acc = {"tokens": 0, "usd": 0.0, "calls": 0, "tool_calls": 0,
           "subagents": 0, "workers": 0, "graph_writes": 0, "rows": 0}
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
    except Exception:
        return acc
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        try:
            row = json.loads(ln)
        except Exception:
            continue
        if row.get("session") != session:
            continue
        i, o = int(row.get("in", 0) or 0), int(row.get("out", 0) or 0)
        acc["tokens"] += i + o
        acc["usd"] += cost_usd(i, o, row.get("model", "default"), rates)
        for k in ("calls", "tool_calls", "subagents", "workers", "graph_writes"):
            acc[k] += int(row.get(k, 0) or 0)
        acc["rows"] += 1
    return acc


# ── vẽ ──────────────────────────────────────────────────────────────────────────────────
def colour(frac: float) -> str:
    return R if frac >= CRIT_AT else (Y if frac >= WARN_AT else G)


def bar(frac: float, cells: int = BAR_CELLS) -> str:
    n = max(0, min(cells, int(round(frac * cells))))
    return FILL * n + EMPTY * (cells - n)


def human(n: float) -> str:
    for unit, size in (("M", 1e6), ("k", 1e3)):
        if n >= size:
            s = f"{n / size:.1f}".rstrip("0").rstrip(".")
            return f"{s}{unit}"
    return str(int(n))


def pct_cell(label: str, used, cap, trigger: bool, money: bool = False) -> str:
    """Một ô '<nhãn> <số>%' — kèm ▲ nếu trần này thực sự chặn được phiên."""
    if not cap:
        return f"{DIM}{label} —{RESET}"
    frac = used / float(cap)
    mark = "▲" if trigger else ""
    shown = f"${used:.2f}" if money else human(used)
    return f"{colour(frac)}{label} {frac * 100:.0f}%{mark}{RESET}{DIM}({shown}){RESET}"


def render(payload: dict, chain: str = "") -> str:
    model = ((payload.get("model") or {}).get("display_name") or "").strip()
    cw = payload.get("context_window") or {}
    size = cw.get("context_window_size") or 0
    used_pct = cw.get("used_percentage")
    if used_pct is None and size:
        tot = (cw.get("total_input_tokens") or 0)
        used_pct = tot / float(size) * 100 if size else None

    line1 = []
    if chain:
        line1.append(chain)
    if model:
        line1.append(model)
    if used_pct is not None:
        f = max(0.0, min(1.0, used_pct / 100.0))
        cap_txt = f"{DIM}/{human(size)}{RESET}" if size else ""
        line1.append(f"ctx {colour(f)}{bar(f)} {used_pct:.0f}%{RESET}{cap_txt}")
    else:
        line1.append(f"{DIM}ctx —{RESET}")

    ws = payload.get("workspace") or {}
    start = ws.get("current_dir") or payload.get("cwd") or os.getcwd()
    root, lay = find_root(start)
    if root is None:
        return " ".join(line1)

    try:
        cfg = parse_config((root / lay / "token-budget.config.yaml").read_text(encoding="utf-8"))
    except Exception:
        return " ".join(line1)

    tot = session_totals(root / lay / "metrics" / "tokens.jsonl",
                         payload.get("session_id") or "", cfg.get("rates", {}))
    if tot["rows"] == 0:
        # Hook Stop chưa ghi lượt nào cho phiên này — nói thẳng là CHƯA CÓ SỐ, đừng vẽ 0%
        # như thể đã đo và thấy bằng không.
        return " ".join(line1) + f"\n{DIM}budget · chưa có số cho phiên này (ledger ghi ở hook Stop){RESET}"

    ah = cfg.get("auto_handover", {})
    triggers = set(ah.get("triggers") or []) if ah.get("enabled") else set()
    budgets = cfg.get("budgets", {})
    cells = [pct_cell(lbl, tot[key], budgets.get(cap_key), cap_key in triggers, money=(key == "usd"))
             for lbl, key, cap_key in CAPS]

    thr = ah.get("threshold")
    tail = []
    if triggers and thr:
        tail.append(f"{DIM}▲=chặn@{float(thr) * 100:.0f}%{RESET}")
    if cfg.get("mode") == "warn":
        tail.append(f"{DIM}mode:warn{RESET}")
    line2 = f"{DIM}budget{RESET} " + f" {DIM}·{RESET} ".join(cells)
    if tail:
        line2 += "  " + " ".join(tail)
    return " ".join(line1) + "\n" + line2


# ── nối chuỗi statusLine đang có ────────────────────────────────────────────────────────
# Không im lặng nuốt badge người ta đang dùng (ví dụ [CAVEMAN]). Đặt OVERSTACK_STATUSLINE_CHAIN
# trỏ tới script cũ; --install tự điền nếu phát hiện được.
def chained_badge(payload: dict) -> str:
    cmd = os.environ.get("OVERSTACK_STATUSLINE_CHAIN", "").strip()
    if not cmd:
        return ""
    try:
        p = subprocess.run(["bash", "-lc", cmd], input=json.dumps(payload), text=True,
                           capture_output=True, timeout=2)
        return (p.stdout or "").splitlines()[0].strip() if p.stdout.strip() else ""
    except Exception:
        return ""


# ── cài / gỡ ────────────────────────────────────────────────────────────────────────────
def _settings_path() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))) / "settings.json"


def _load_settings(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _self_path() -> str:
    return str(Path(__file__).resolve())


def _cmd_string(entry) -> str:
    """Chuỗi lệnh của một mục statusLine, bất kể nó là dict hay chuỗi trần."""
    if isinstance(entry, dict):
        return str(entry.get("command") or "")
    return str(entry or "")


def points_at_me(entry) -> bool:
    """So SỐNG trên chính chuỗi lệnh, không so trên json.dumps() của nó.

    Đo 2026-09-08: `json.dumps` mặc định `ensure_ascii=True`, nên đường dẫn có dấu
    (`pull-code-mới-từ-setup`) bị biến thành `pull-code-m\u1edbi-t\u1eeb-setup`. So chuỗi thô
    với bản đã escape thì không bao giờ khớp → `--status` báo lệch đường dẫn giả, `--uninstall`
    từ chối gỡ chính bản nó vừa cài.
    """
    return _self_path() in _cmd_string(entry)


def build_command(script: str, chain: str = "") -> str:
    """Lệnh shell cho statusLine. shlex.quote chứ KHÔNG json.dumps.

    json.dumps escape non-ASCII, nên lệnh sinh ra trỏ vào một đường dẫn KHÔNG TỒN TẠI với bất
    kỳ project nào có dấu trong tên — thanh câm mà không báo gì. shlex.quote là công cụ đúng
    cho việc trích dẫn shell.
    """
    prefix = f"OVERSTACK_STATUSLINE_CHAIN={shlex.quote(chain)} " if chain else ""
    return f"{prefix}python3 {shlex.quote(script)}"


def cmd_install() -> int:
    p = _settings_path()
    data = _load_settings(p)
    me = _self_path()
    cur = data.get(SETTINGS_KEY)
    if cur and not points_at_me(cur):
        data[BACKUP_KEY] = cur                      # cất bản cũ để --uninstall trả lại nguyên trạng
    chain = _cmd_string(data.get(BACKUP_KEY))
    data[SETTINGS_KEY] = {"type": "command", "command": build_command(me, chain)}
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        shutil.copy2(p, p.with_suffix(".json.bak"))
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✓ statusLine → {me}")
    if chain:
        print(f"  nối chuỗi badge cũ: {chain}")
    print(f"  settings: {p} (bản cũ: {p.with_suffix('.json.bak')})")
    print("  LƯU Ý: đường dẫn plugin đổi sau mỗi lần cập nhật plugin — chạy lại /budget-statusline install.")
    return 0


def cmd_uninstall() -> int:
    p = _settings_path()
    data = _load_settings(p)
    cur = data.get(SETTINGS_KEY)
    if not cur or not points_at_me(cur):
        print("• statusLine không trỏ về plugin này — không đụng gì.")
        return 0
    prev = data.pop(BACKUP_KEY, None)
    if prev:
        data[SETTINGS_KEY] = prev
        print(f"✓ trả lại statusLine cũ: {prev.get('command') if isinstance(prev, dict) else prev}")
    else:
        data.pop(SETTINGS_KEY, None)
        print("✓ gỡ statusLine (trước đó không có bản nào để trả lại)")
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


def cmd_status() -> int:
    p = _settings_path()
    cur = _load_settings(p).get(SETTINGS_KEY)
    me = _self_path()
    print(f"script     : {me}")
    print(f"settings   : {p}")
    print(f"statusLine : {json.dumps(cur, ensure_ascii=False) if cur else '(chưa đặt)'}")
    if not cur:
        print("→ chạy: /budget-statusline install")
    elif points_at_me(cur):
        print("→ đang wire đúng về plugin này.")
    elif "overstack-budget-statusline" in _cmd_string(cur):
        print("→ LỆCH ĐƯỜNG DẪN: trỏ về một bản plugin cũ. Chạy lại /budget-statusline install.")
    else:
        print("→ đang dùng statusLine khác. `install` sẽ cất nó lại và nối chuỗi badge.")
    root, lay = find_root(os.getcwd())
    print(f"overstack  : {f'{root} (layout {lay}/)' if root else '(không tìm thấy từ cwd)'}")
    return 0


# ── self-test ───────────────────────────────────────────────────────────────────────────
def _dot_layout_ok() -> bool:
    """Layout ẩn `.harness/` (dự án đích sau bản dot-layout) phải nhận ra y như `harness/`."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r = Path(td)
        (r / ".harness").mkdir()
        (r / ".harness" / "token-budget.config.yaml").write_text("mode: warn\n", encoding="utf-8")
        found, lay = find_root(str(r))
        return found == r.resolve() and lay == ".harness"


def self_test() -> int:
    import tempfile
    ok = []

    cfg = parse_config(
        "verified: false\n"
        "mode: warn\n"
        "budgets:\n"
        "  per_session_tokens: 2000000     # ASSUMPTION\n"
        "  per_task_usd: 5.0\n"
        "  per_session_model_calls: 500\n"
        "  per_session_tool_calls: 2000\n"
        "auto_handover:\n"
        "  enabled: true\n"
        "  threshold: 0.85\n"
        "  triggers: [per_session_tokens, per_session_model_calls]\n"
        "rates:\n"
        "  default:  {input: 0.003,  output: 0.015}\n"
        "  opus:     {input: 0.015,  output: 0.075}\n")
    ok.append(("config: trần đọc đúng, chú thích bị cắt",
               cfg["budgets"]["per_session_tokens"] == 2000000
               and cfg["budgets"]["per_task_usd"] == 5.0
               and cfg["mode"] == "warn" and cfg["verified"] is False))
    ok.append(("config: triggers là list, threshold là số",
               cfg["auto_handover"]["triggers"] == ["per_session_tokens", "per_session_model_calls"]
               and cfg["auto_handover"]["threshold"] == 0.85))
    ok.append(("config: rates lồng dạng flow đọc được",
               cfg["rates"]["opus"] == {"input": 0.015, "output": 0.075}))

    # $ phải khớp token-budget.py: model lạ rơi về 'default', KHÔNG phải rate opus.
    ok.append(("cost: model lạ rơi về default",
               abs(cost_usd(1000, 1000, "claude-opus-5", cfg["rates"]) - 0.018) < 1e-9))
    ok.append(("cost: model khớp dùng rate riêng",
               abs(cost_usd(1000, 1000, "opus", cfg["rates"]) - 0.09) < 1e-9))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "harness" / "metrics").mkdir(parents=True)
        (root / "harness" / "token-budget.config.yaml").write_text(
            "mode: warn\nbudgets:\n  per_session_tokens: 1000\n  per_task_usd: 5.0\n"
            "  per_session_model_calls: 10\n  per_session_tool_calls: 100\n"
            "auto_handover:\n  enabled: true\n  threshold: 0.85\n"
            "  triggers: [per_session_tokens]\n"
            "rates:\n  default: {input: 0.003, output: 0.015}\n", encoding="utf-8")
        led = root / "harness" / "metrics" / "tokens.jsonl"
        led.write_text(
            json.dumps({"session": "s1", "in": 100, "out": 100, "model": "m", "calls": 3}) + "\n" +
            json.dumps({"session": "s1", "in": 50, "out": 50, "calls": 2, "tool_calls": 7}) + "\n" +
            json.dumps({"session": "OTHER", "in": 9999, "out": 9999, "calls": 99}) + "\n", encoding="utf-8")

        t = session_totals(led, "s1", cfg["rates"])
        ok.append(("ledger: cộng dồn nhiều row, bỏ phiên khác",
                   t["tokens"] == 300 and t["calls"] == 5 and t["tool_calls"] == 7 and t["rows"] == 2))
        ok.append(("ledger: row thiếu khoá counter không nổ", t["subagents"] == 0))

        # so bằng resolve(): trên macOS thư mục tạm là /var/... còn resolve() ra /private/var/...
        rroot = root.resolve()
        found, lay = find_root(str(root))
        ok.append(("root: tìm được layout harness/", found == rroot and lay == "harness"))
        sub = root / "a" / "b"
        sub.mkdir(parents=True)
        ok.append(("root: leo ngược từ thư mục con", find_root(str(sub))[0] == rroot))
        ok.append(("root: layout dot (.harness/) cũng nhận", _dot_layout_ok()))

        payload = {"session_id": "s1", "cwd": str(root),
                   "model": {"display_name": "Opus"},
                   "context_window": {"used_percentage": 12, "context_window_size": 1000000}}
        out = render(payload)
        ok.append(("render: hai dòng, có ctx và budget",
                   out.count("\n") == 1 and "ctx" in out and "budget" in out))
        ok.append(("render: trần trigger được đánh dấu ▲", "▲" in out))
        ok.append(("render: tok 30% (300/1000)", "tok 30%" in out))

        # Phiên chưa có row → phải nói CHƯA CÓ SỐ, không vẽ 0%.
        empty = render({**payload, "session_id": "nobody"})
        ok.append(("render: phiên chưa ghi ledger → nói thẳng, không vẽ 0%",
                   "chưa có số" in empty and "tok 0%" not in empty))

    # Ngoài overstack → chỉ còn dòng 1, không nổ.
    out2 = render({"session_id": "x", "cwd": "/", "model": {"display_name": "Opus"},
                   "context_window": {"used_percentage": 5, "context_window_size": 200000}})
    ok.append(("render: ngoài overstack → một dòng, không nổ", "\n" not in out2 and "ctx" in out2))

    # Trường context null (đầu phiên / sau /compact) → không nổ, hiện gạch.
    out3 = render({"session_id": "x", "cwd": "/", "model": {},
                   "context_window": {"used_percentage": None, "context_window_size": None}})
    ok.append(("render: context null → không nổ", "ctx —" in out3))

    # Đường dẫn có dấu: lệnh sinh ra phải trỏ ĐÚNG file, và phải tự nhận ra chính nó.
    vn = "/tmp/pull-code-mới-từ-setup/statusline.py"
    cmd = build_command(vn, 'bash "/x/caveman.sh"')
    ok.append(("install: đường dẫn có dấu không bị escape thành \\u….",
               vn in cmd and "\\u1edb" not in cmd))
    ok.append(("install: chain được trích dẫn shell an toàn",
               shlex.split(cmd)[0].startswith("OVERSTACK_STATUSLINE_CHAIN=")
               and shlex.split(cmd)[-1] == vn))
    ok.append(("status: nhận ra chính nó qua chuỗi lệnh thô",
               points_at_me({"type": "command", "command": build_command(_self_path())})
               and not points_at_me({"type": "command", "command": "bash /x/other.sh"})))

    # Ngưỡng màu.
    ok.append(("colour: 0.5 xanh · 0.7 vàng · 0.9 đỏ",
               colour(0.5) == G and colour(0.7) == Y and colour(0.9) == R))
    ok.append(("bar: 10 ô, làm tròn đúng", bar(0.0) == EMPTY * 10 and bar(1.0) == FILL * 10
               and bar(0.35) == FILL * 4 + EMPTY * 6))

    bad = [n for n, good in ok if not good]
    for n, good in ok:
        print(f"  [{'OK ' if good else 'FAIL'}] {n}")
    print(f"SELFTEST: {'ALL PASS' if not bad else f'{len(bad)} FAIL'}  ({len(ok)} assertion)")
    return 0 if not bad else 1


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--self-test":
        return self_test()
    if arg == "--install":
        return cmd_install()
    if arg == "--uninstall":
        return cmd_uninstall()
    if arg == "--status":
        return cmd_status()
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}
    try:
        print(render(payload, chained_badge(payload)))
    except Exception:
        pass                       # fail-open: thà thanh trống còn hơn terminal gãy
    return 0


if __name__ == "__main__":
    sys.exit(main())
