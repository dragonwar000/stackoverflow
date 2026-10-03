#!/usr/bin/env python3
"""feature-switch — bật/tắt công tắc harness. Danh mục: features.yaml (registry). Logic: hooklib.feature_on.

  feature-switch list
  feature-switch status <id>
  feature-switch on <id>
  feature-switch off <id> [--acknowledge-guardrail]

Guardrail (hooklib.GUARDRAIL_FALLBACK hoặc class: guardrail): chỉ tắt được qua file cục bộ và PHẢI có
--acknowledge-guardrail. Gate/feature: tắt ghi file cục bộ, in stderr, ghi nhật ký metrics/feature-switch.jsonl (qua harness_dir).
Công tắc chưa gắn vào hook nào (consumer: null) bị từ chối khi tắt, để không tạo no-op im lặng.
default 'stamp' (wikigraph): feature_on không tự resolve — CLI tính theo stamp dự án rồi truyền default tường minh.
agent-trace: giữ đường riêng — gọi agent-trace.py on/off (nó chỉ đọc config của chính nó).
"""
import argparse, datetime, importlib.util, json, os, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overstack_paths import harness_dir, overstack_dir  # noqa: E402

LOCAL = "features.local.yaml"
HOOKLIB_REPO = "llmwiki/.claude/hooks/hooklib.py"  # bare-path: ok — tìm hooklib trong repo trước
HOOKLIB_GLOBAL = ".claude/harness/hooks/hooklib.py"  # bare-path: ok — bản cài toàn cục
STAMP_DEFAULT = "stamp"


class CliError(Exception):
    """Lỗi dừng lệnh trước khi ghi gì (rc 1)."""


def load_hooklib(root: Path):
    for p in (root / HOOKLIB_REPO, Path.home() / HOOKLIB_GLOBAL):
        if p.is_file():
            spec = importlib.util.spec_from_file_location("hooklib", str(p))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit("feature-switch: không tìm thấy hooklib.py (repo hoặc ~/.claude/harness)")


def _is_guardrail(hl, fid: str, spec: dict) -> bool:
    return fid in getattr(hl, "GUARDRAIL_FALLBACK", ()) or spec.get("class") == "guardrail"


def _state(root: Path, hl, fid: str, spec: dict):
    """(bật?, nguồn). Default 'stamp' do CLI tự tính theo stamp dự án (phía Stop), không để feature_on đoán."""
    default = None
    if str(spec.get("default", "")).strip().lower() == STAMP_DEFAULT:
        default = hl.stamp_path(str(root)) is not None
    on, layer = hl.feature_on(str(root), fid, default=default)
    if default is not None and layer == "mặc định":
        layer = "mặc định theo stamp (phía Stop)"
    return on, layer


def cmd_list(root: Path, hl) -> int:
    for fid, spec in sorted(hl.feature_registry(str(root)).items()):
        on, _ = _state(root, hl, fid, spec)
        gate = spec.get("consumer") or "(chưa gắn vào hook)"
        print(f"{fid:18} {spec.get('class', 'feature'):10} {'BẬT' if on else 'TẮT':4} gác: {gate}")
    return 0


def cmd_status(root: Path, hl, fid: str) -> int:
    spec = hl.feature_registry(str(root)).get(fid)
    if spec is None:
        print(f"không có công tắc {fid}", file=sys.stderr)
        return 2
    on, layer = _state(root, hl, fid, spec)
    print(f"{fid}: {'BẬT' if on else 'TẮT'} (nguồn: {layer}; lớp: {spec.get('class', 'feature')})")
    return 0


def _write_local(root: Path, fid: str, value: str) -> Path:
    import yaml
    od = overstack_dir(str(root)) or (root / ".llmwiki")  # bare-path: ok — thư mục overstack thật của dự án
    f = od / LOCAL
    data = {}
    if f.is_file():
        try:
            loaded = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            raise CliError(f"{f} sai cú pháp YAML — chưa ghi gì: {e}")
        data = loaded if isinstance(loaded, dict) else {}
    data[fid] = value
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=True)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, f)  # ghi nguyên tử: không để file nửa chừng
    return f


def _audit(root: Path, action: str, fid: str, cls: str, layer: str) -> None:
    d = harness_dir(str(root)) / "metrics"
    d.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "action": action,
           "feature": fid, "class": cls, "layer": layer, "by": "cli"}
    with open(d / "feature-switch.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def cmd_set(root: Path, hl, action: str, fid: str, ack: bool) -> int:
    try:
        import yaml  # noqa: F401 — registry và file cục bộ đều cần PyYAML
    except ImportError:
        print("feature-switch: cần PyYAML (pip install pyyaml) — chưa ghi gì", file=sys.stderr)
        return 1
    spec = hl.feature_registry(str(root)).get(fid)
    if spec is None:
        print(f"không có công tắc {fid}", file=sys.stderr)
        return 2
    cls = spec.get("class", "feature")
    if action == "off":
        if not spec.get("consumer"):
            print(f"từ chối: {fid} chưa gắn vào hook nào — tắt sẽ không có tác dụng", file=sys.stderr)
            return 2
        if _is_guardrail(hl, fid, spec) and not ack:
            print(f"từ chối: {fid} là guardrail. Thêm --acknowledge-guardrail để xác nhận.", file=sys.stderr)
            return 2
    if fid == "agent-trace":
        script = Path(__file__).resolve().parent / "agent-trace.py"
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
        rc = subprocess.run([sys.executable, str(script), action, "--root", str(root)], env=env).returncode
        if rc == 0:
            src = f"config {spec.get('config_file')}"
            if action == "off":
                print(f"[feature-switch] TẮT {fid} (lớp {cls}) — qua agent-trace.py, {src}", file=sys.stderr)
            _audit(root, action, fid, cls, src)
        return rc
    try:
        f = _write_local(root, fid, action)
    except CliError as e:
        print(f"feature-switch: {e}", file=sys.stderr)
        return 1
    if action == "off":
        print(f"[feature-switch] TẮT {fid} (lớp {cls}) — ghi {f}", file=sys.stderr)
    else:
        print(f"[feature-switch] BẬT {fid} — ghi {f}")
    _audit(root, action, fid, cls, f"file cục bộ {LOCAL}")
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
