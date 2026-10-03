#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory-map — VIEW bộ nhớ thứ cấp: gom scratch-log + ledger + events theo SESSION/FILE
→ đồ thị visualizable (proposal 030726-secondary-memory T3), TÁI DÙNG engine build-wiki-graph.

Council-024: reuse build-wiki-graph (KHÔNG renderer mới, KHÔNG RAG); cạnh 'elaborates' nối
session → file đã chạm; why (context vụn) hiện ở tooltip node session. File-first, nhìn bằng mắt.

CLI:
  memory-map.py            # ghi llmwiki/html/memory-map.html (JS đồ thị)
  memory-map.py --static   # bản HTML thuần 0-JS
  memory-map.py --source zeromem   # ghi memory-map-zeromem.html cạnh memory-map.html, chỉ ĐỌC zeromem.db
"""
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

for _c in Path(__file__).resolve().parents:
    if (_c / "harness" / "scripts" / "overstack_paths.py").is_file():
        sys.path.insert(0, str(_c / "harness" / "scripts"))
        break
try:
    from overstack_paths import harness_dir as _harness_dir
except Exception:
    _harness_dir = None



def _ovs_font(html: str) -> str:
    """Lớp nền chung của mọi HTML framework sinh ra (font Be Vietnam Pro nhúng + token sáng/tối + nút đổi giao diện) — nguồn: fdk/tools/html_base.py."""
    import importlib.util
    from pathlib import Path as _P
    here = _P(__file__).resolve()
    for c in (here.with_name("html_font.py"), here.parents[2] / "fdk" / "tools" / "html_font.py", _P.home() / ".claude/harness/fdk/tools/html_font.py"):
        if c.is_file():
            s = importlib.util.spec_from_file_location("html_font", c); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
            return m.apply(html)
    return html

def _metrics_dir(root) -> Path:
    return (_harness_dir(root) if _harness_dir else Path(root) / "harness") / "metrics"


# ENGINE = nơi chứa fdk/tools/*.py (repo-local khi framework; GLOBAL ~/.claude/harness khi downstream).
# ROOT  = project để đọc metrics + ghi html — ưu tiên cwd (Stop-hook đặt cwd=project root) nên engine
# global vẫn vẽ ĐÚNG project downstream, không cần copy engine vào từng repo (đối xứng build-wiki-graph).
ENGINE = Path(__file__).resolve().parents[2]
_cwd = Path.cwd()
ROOT = _cwd if ((_cwd / "llmwiki").is_dir() or (_cwd / ".git").is_dir()) else ENGINE
OUT = ROOT / "llmwiki" / "html" / "memory-map.html"


def _load(modpath, name):
    spec = importlib.util.spec_from_file_location(name, ENGINE / modpath)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


WG = _load("fdk/tools/build-wiki-graph.py", "wg")
WG.REL_COLORS["elaborates"] = "#5856d6"     # session → file đã chạm
WG.REL_VI["elaborates"] = "phiên chạm/làm rõ file"
WG.REL_COLORS["continues"] = "#ff9500"      # phiên → phiên trước (chuỗi, mem-rank chain)
WG.REL_VI["continues"] = "tiếp nối phiên trước"


def _read(p):
    p = ROOT / p
    if not p.is_file():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if ln:
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    return out


def build():
    scratch = _read((_metrics_dir(ROOT) / "scratch-log.jsonl").relative_to(ROOT).as_posix())
    ledger = _read("llmwiki/wiki/ledger.jsonl")
    events = _read("harness/metrics/events.jsonl")

    # gom theo session → {files:set, whys:[]}
    sess = {}

    def touch(sid, fp, why=None):
        sid = (sid or "").strip()[:8]
        if not sid:
            return
        s = sess.setdefault(sid, {"files": set(), "whys": []})
        if fp:
            s["files"].add(fp)
        if why and why.strip():
            s["whys"].append(why.strip())

    for r in scratch:
        touch(r.get("session"), r.get("file"), r.get("why"))
    for r in ledger:
        touch(r.get("session"), r.get("target"))
    for r in events:
        touch(r.get("session"), r.get("path"))

    nodes, edges, seen_files = [], [], set()
    for sid, s in sorted(sess.items()):
        why_tip = " · ".join(s["whys"][:4]) or "(chưa có why)"
        nodes.append({"id": f"s:{sid}", "path": f"session/{sid}", "group": "session", "type": "session",
                      "title": why_tip[:120], "wiki": "memory", "label": f"⏱ {sid}"})
        for fp in sorted(s["files"]):
            if fp not in seen_files:
                nodes.append({"id": fp, "path": fp, "group": "file", "type": "file",
                              "title": fp, "wiki": "memory", "label": fp.rsplit("/", 1)[-1]})
                seen_files.add(fp)
            edges.append({"from": f"s:{sid}", "rel": "elaborates", "to": fp, "kind": "to"})
    # CHUỖI phiên (mem-rank episode --parent): map không chỉ là "phiên nào chạm file nào" mà còn
    # "phiên nào tiếp phiên nào" — đọc một mạch được. Thiếu store/episode → bỏ qua, không vẽ thêm.
    for child, parent in _session_parents().items():
        if f"s:{child}" in {n["id"] for n in nodes} and f"s:{parent}" in {n["id"] for n in nodes}:
            edges.append({"from": f"s:{child}", "rel": "continues", "to": f"s:{parent}", "kind": "to"})
    return nodes, edges


def _zeromem_sessions(root):
    """Phiên và số turn từ zeromem.db, chỉ đọc. None khi chưa có store. Lỗi schema → RuntimeError."""
    zb = _load(Path("harness") / "scripts" / "zeromem-bridge.py", "zb")
    db = zb.store_home(str(root)) / "zeromem.db"
    if not db.is_file():
        return None
    con = sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)
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
    try:
        rows = _zeromem_sessions(ROOT)
    except (RuntimeError, sqlite3.Error) as e:
        print(f"memory-map --source zeromem: {e}", file=sys.stderr)
        return 1
    if rows is None:
        print("memory-map --source zeromem: chưa có zeromem.db của project này")
        return 0
    # Chỉ id, số turn, mốc thời gian. Không đọc cột text: nội dung turn không đi vào đồ thị.
    nodes = [{"id": f"s:{sid[:8]}", "path": f"session/{sid[:8]}", "group": "session", "type": "session",
              "title": f"{n} turn · {sid[:8]}", "wiki": "memory", "label": sid[:8]}
             for sid, _ts0, n, _ts1 in rows]
    out = ROOT / "llmwiki" / "html" / "memory-map-zeromem.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    fn = WG.build_static if "--static" in sys.argv else WG.build_html
    out.write_text(_ovs_font(fn("memory", str(out), nodes, [], [], {})), encoding="utf-8")
    print(f"✓ wrote {out.relative_to(ROOT)} — {len(nodes)} phiên (zeromem, chỉ đọc)")
    return 0


def _session_parents() -> dict:
    """{session con: session cha} từ store mem-rank (harness/metrics/memory.jsonl). Fail-open."""
    out = {}
    try:
        p = _metrics_dir(Path.cwd()) / "memory.jsonl"
        for ln in p.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            m = json.loads(ln)
            if m.get("kind") != "episode":
                continue
            if m.get("session") and m.get("parent"):   # add() phẳng hoá meta lên top-level
                out[m["session"]] = m["parent"]
    except Exception:
        pass
    return out


def main():
    if "--source" in sys.argv and sys.argv[sys.argv.index("--source") + 1:][:1] == ["zeromem"]:
        return _main_zeromem()
    nodes, edges = build()
    if not nodes:
        print("memory-map: chưa có dữ liệu (scratch-log/ledger/events trống)")
        return 0
    fn = WG.build_static if "--static" in sys.argv else WG.build_html
    OUT.write_text(_ovs_font(fn("memory", str(OUT), nodes, edges, [], {})), encoding="utf-8")
    n_sess = sum(1 for n in nodes if n["type"] == "session")
    print(f"✓ wrote {OUT.relative_to(ROOT)} — {n_sess} phiên, {len(nodes)-n_sess} file, {len(edges)} cạnh (reuse build-wiki-graph)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
