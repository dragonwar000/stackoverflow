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
    env = os.environ.get("ZEROMEM_ZM")
    if env:
        return env if os.path.isfile(env) else None
    return shutil.which("zm")


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
    # zm có thể bỏ qua exclude_session: lọc lại ở đây để phiên hiện tại không tự nhớ lại chính nó
    return [e for e in res.get("evidence", [])
            if e.get("text") and (not exclude_session or e.get("session_id") != exclude_session)]


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

    Thiếu binary zm → mem-rank (không mất ghi), cả khi khai zeromem lẫn both. Giá trị lạ → `invalid:<giá trị>`,
    hook sẽ báo và giữ mem-rank.
    """
    cfg = harness_dir(root) / "mem-rank.config.yaml"
    try:
        text = cfg.read_text(encoding="utf-8")
    except (OSError, ValueError):
        text = ""
    m = re.search(r"^memory:\s*\n(?:[ \t]+.*\n)*?[ \t]+backend:\s*([A-Za-z-]+)", text, re.M)
    val = m.group(1) if m else DEFAULT_BACKEND
    if val not in VALID_BACKENDS:
        return f"invalid:{val}"
    if val in ("zeromem", "both") and not zm_bin():
        print(f"zeromem-bridge: backend={val} nhưng không có zm — tạm dùng mem-rank", file=sys.stderr)
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
    try:
        if a.cmd == "backend":
            print(memory_backend(root))
            return 0
        if a.cmd == "ingest":
            ingest(root, a.transcript, a.session)
            return 0
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
    except Exception as e:  # fail-open: lỗi zm hay schema lạ không được làm rc khác 0 (trừ status)
        print(f"zeromem-bridge: {e}", file=sys.stderr)
        return 1 if a.cmd == "status" else 0


if __name__ == "__main__":
    sys.exit(main())
