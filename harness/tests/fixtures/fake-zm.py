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
